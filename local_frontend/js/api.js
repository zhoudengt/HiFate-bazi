class GrpcGatewayClient {
    constructor(config = {}) {
        this.enabled = !!config.enabled;
        this.baseURL = (config.baseURL || '').replace(/\/$/, '');
        this.timeout = config.timeout || 30000;
        const endpoints = Array.isArray(config.endpoints) ? config.endpoints : [];
        this.allowedEndpoints = new Set(endpoints);
        this.allowAll = endpoints.length === 0;
        this.textEncoder = new TextEncoder();
        this.textDecoder = new TextDecoder();
    }

    canHandle(endpoint) {
        return this.enabled && !!this.baseURL && (this.allowAll || this.allowedEndpoints.has(endpoint));
    }

    async call(endpoint, payload) {
        if (!this.canHandle(endpoint)) {
            throw new Error(`gRPC 网关未启用或未授权端点: ${endpoint}`);
        }

        const token = localStorage.getItem(TOKEN_KEY) || '';
        const requestBody = this._buildGrpcWebBody(endpoint, payload, token);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(`${this.baseURL}/frontend.gateway.FrontendGateway/Call`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/grpc-web+proto',
                    'X-Grpc-Web': '1',
                    'X-User-Agent': 'grpc-web-js/0.1',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: requestBody,
                signal: controller.signal,
                mode: 'cors',
                credentials: 'omit'
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`gRPC-Web 调用失败: HTTP ${response.status}`, errorText);
                
                // 尝试解析 JSON 错误响应
                let errorMessage = `服务器错误: HTTP ${response.status}`;
                try {
                    const errorData = JSON.parse(errorText);
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    } else if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (errorData.detail) {
                        errorMessage = errorData.detail;
                    }
                } catch (e) {
                    // 如果不是 JSON，使用原始文本（截取前200字符）
                    errorMessage = errorText.substring(0, 200);
                }
                
                throw new Error(errorMessage);
            }

            const buffer = new Uint8Array(await response.arrayBuffer());
            const { messageBytes, trailers } = this._parseGrpcWebResponse(buffer);
            const parsed = this._decodeResponse(messageBytes);
            const trailerStatus = trailers['grpc-status'] ?? response.headers.get('grpc-status') ?? '0';
        
            if (trailerStatus !== '0' || !parsed.success) {
                // ⭐ 增强错误处理：尝试从多个来源获取错误信息
                let errorMessage = '';
                
                // 1. 优先使用 parsed.error
                if (parsed.error) {
                    errorMessage = parsed.error;
                }
                // 2. 尝试从 trailers 获取
                else if (trailers['grpc-message']) {
                    errorMessage = trailers['grpc-message'];
                }
                // 3. 尝试从 data_json 解析错误信息
                else if (parsed.data_json) {
                    try {
                        const errorData = JSON.parse(parsed.data_json);
                        if (errorData.detail) {
                            errorMessage = errorData.detail;
                        } else if (errorData.message) {
                            errorMessage = errorData.message;
                        } else if (errorData.error) {
                            errorMessage = errorData.error;
                        } else {
                            errorMessage = JSON.stringify(errorData);
                        }
                    } catch (e) {
                        // 如果解析失败，使用原始字符串的前200个字符
                        errorMessage = parsed.data_json.substring(0, 200);
                    }
                }
                
                // 4. 如果还是没有错误信息，使用默认消息
                if (!errorMessage) {
                    errorMessage = `gRPC 调用失败 (status: ${trailerStatus})`;
                }
                
                console.error('gRPC 错误:', { 
                    trailerStatus, 
                    errorMessage, 
                    parsed,
                    trailers 
                });
                throw new Error(errorMessage);
            }

            if (!parsed.data_json) {
                console.warn('gRPC 响应中没有 data_json');
                return {};
            }

            try {
                return JSON.parse(parsed.data_json);
            } catch (e) {
                console.error('解析 data_json 失败:', e, '原始数据:', parsed.data_json);
                throw new Error('服务器响应格式错误');
            }
        } finally {
            clearTimeout(timeoutId);
        }
    }

    _buildGrpcWebBody(endpoint, payload, token) {
        // 安全地序列化 payload，避免 Maximum call stack exceeded
        let payloadJson;
        try {
            // 直接尝试序列化
            payloadJson = JSON.stringify(payload ?? {});
        } catch (error) {
            // 如果遇到循环引用或栈溢出，使用深度清理
            if (error.message && (error.message.includes('Maximum call stack') || error.message.includes('circular'))) {
                console.warn('检测到循环引用或栈溢出，使用安全序列化:', error.message);
                const cleaned = this._deepCleanForSerialization(payload ?? {});
                payloadJson = JSON.stringify(cleaned);
            } else {
                throw error;
            }
        }
        
        const message = this._encodeRequest(
            endpoint,
            payloadJson,
            token || ''
        );
        return this._wrapFrame(0x00, message);
    }
    
    _deepCleanForSerialization(obj, visited = new WeakSet()) {
        // 检测循环引用
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        
        // 处理基本类型
        if (typeof obj === 'string' || typeof obj === 'number' || typeof obj === 'boolean') {
            return obj;
        }
        
        // 检测循环引用
        if (visited.has(obj)) {
            return '[循环引用]';
        }
        
        visited.add(obj);
        
        try {
            if (Array.isArray(obj)) {
                return obj.map(item => this._deepCleanForSerialization(item, visited));
            } else if (obj instanceof File || obj instanceof Blob) {
                return `[File: ${obj.name || 'blob'}]`;
            } else {
                const cleaned = {};
                for (const key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        try {
                            cleaned[key] = this._deepCleanForSerialization(obj[key], visited);
                        } catch (e) {
                            cleaned[key] = '[序列化失败]';
                        }
                    }
                }
                return cleaned;
            }
        } finally {
            visited.delete(obj);
        }
    }

    _encodeRequest(endpoint, payloadJson, authToken) {
        // 使用 Uint8Array 而不是数组，避免大数组展开导致栈溢出
        const parts = [];

        if (endpoint) {
            parts.push(this._encodeStringField(1, endpoint));
        }
        if (payloadJson) {
            parts.push(this._encodeStringField(2, payloadJson));
        }
        if (authToken) {
            parts.push(this._encodeStringField(3, authToken));
        }

        // 计算总长度
        let totalLength = 0;
        for (const part of parts) {
            totalLength += part.length;
        }

        // 合并所有部分
        const result = new Uint8Array(totalLength);
        let offset = 0;
        for (const part of parts) {
            result.set(part, offset);
            offset += part.length;
        }

        return result;
    }

    _encodeStringField(fieldNumber, value) {
        const header = (fieldNumber << 3) | 2;
        const valueBytes = this.textEncoder.encode(value);
        const varintArray = this._encodeVarint(valueBytes.length);
        const varintBytes = new Uint8Array(varintArray);
        
        // 使用 Uint8Array 而不是数组，避免大数组展开导致栈溢出
        const result = new Uint8Array(1 + varintBytes.length + valueBytes.length);
        result[0] = header;
        result.set(varintBytes, 1);
        result.set(valueBytes, 1 + varintBytes.length);
        
        return result;
    }

    _encodeVarint(value) {
        const chunks = [];
        let current = value >>> 0;
        while (current >= 0x80) {
            chunks.push((current & 0x7F) | 0x80);
            current >>>= 7;
        }
        chunks.push(current);
        return chunks; // 返回数组，调用者需要转换为 Uint8Array
    }

    _wrapFrame(flag, payload) {
        const frame = new Uint8Array(5 + payload.length);
        frame[0] = flag;
        const view = new DataView(frame.buffer);
        view.setUint32(1, payload.length, false); // big-endian
        frame.set(payload, 5);
        return frame;
    }

    _parseGrpcWebResponse(buffer) {
        let offset = 0;
        let messageBytes = null;
        const trailers = {};

        while (offset + 5 <= buffer.length) {
            const flag = buffer[offset];
            const view = new DataView(buffer.buffer, buffer.byteOffset + offset + 1, 4);
            const length = view.getUint32(0, false);
            offset += 5;

            const framePayload = buffer.slice(offset, offset + length);
            offset += length;

            if (flag & 0x80) {
                const trailerText = this.textDecoder.decode(framePayload);
                trailerText.split(/\r?\n/).forEach((line) => {
                    const trimmed = line.trim();
                    if (!trimmed) return;
                    const [key, ...rest] = trimmed.split(':');
                    trailers[key.toLowerCase()] = rest.join(':').trim();
                });
            } else {
                messageBytes = framePayload;
            }
        }

        if (!messageBytes) {
            throw new Error('gRPC 响应缺少数据帧');
        }

        return { messageBytes, trailers };
    }

    _decodeResponse(bytes) {
        let offset = 0;
        const result = {
            success: false,
            data_json: '',
            error: '',
            status_code: 0
        };

        while (offset < bytes.length) {
            const key = bytes[offset++];
            const fieldNumber = key >> 3;
            const wireType = key & 0x07;

            if (wireType === 0) {
                const { value, nextOffset } = this._decodeVarint(bytes, offset);
                offset = nextOffset;
                if (fieldNumber === 1) {
                    result.success = value === 1;
                } else if (fieldNumber === 4) {
                    result.status_code = value;
                }
            } else if (wireType === 2) {
                const { value: length, nextOffset } = this._decodeVarint(bytes, offset);
                offset = nextOffset;
                const valueBytes = bytes.slice(offset, offset + length);
                offset += length;
                const text = this.textDecoder.decode(valueBytes);
                if (fieldNumber === 2) {
                    result.data_json = text;
                } else if (fieldNumber === 3) {
                    result.error = text;
                }
            } else {
                throw new Error(`不支持的 wireType: ${wireType}`);
            }
        }

        return result;
    }

    _decodeVarint(bytes, offset) {
        let shift = 0;
        let value = 0;
        let currentOffset = offset;

        while (currentOffset < bytes.length) {
            const byte = bytes[currentOffset++];
            value |= (byte & 0x7F) << shift;
            if (!(byte & 0x80)) {
                return { value, nextOffset: currentOffset };
            }
            shift += 7;
        }

        throw new Error('varint 解析失败');
            }
}

const grpcGatewayClient = new GrpcGatewayClient(GRPC_CONFIG);

// API 调用封装（强制使用 gRPC-Web 网关）
class ApiClient {
    constructor(baseURL) {
        // baseURL 保留，便于兼容legacy配置（例如其它fetch引用）
        this.baseURL = baseURL;
    }

    async request(endpoint, data = {}) {
        return this._invokeGrpc(endpoint, data);
    }

    async post(endpoint, data = {}) {
        return this._invokeGrpc(endpoint, data);
    }

    async get() {
        throw new Error('APIClient.get 尚未迁移至 gRPC，请实现专用客户端或使用 POST 请求');
    }

    async _invokeGrpc(endpoint, data = {}) {
        const result = await grpcGatewayClient.call(endpoint, data);
        if (result === null || result === undefined) {
            throw new Error('gRPC 网关返回空响应');
        }
        return result;
    }
}

const api = new ApiClient(API_CONFIG.baseURL);

