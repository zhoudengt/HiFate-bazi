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

            const buffer = new Uint8Array(await response.arrayBuffer());
            const { messageBytes, trailers } = this._parseGrpcWebResponse(buffer);
            const parsed = this._decodeResponse(messageBytes);
            const trailerStatus = trailers['grpc-status'] ?? response.headers.get('grpc-status') ?? '0';
        
            if (trailerStatus !== '0' || !parsed.success) {
                const grpcMessage = parsed.error || trailers['grpc-message'] || 'gRPC 调用失败';
                throw new Error(grpcMessage);
            }

            if (!parsed.data_json) {
                return {};
            }

            return JSON.parse(parsed.data_json);
        } finally {
            clearTimeout(timeoutId);
        }
    }

    _buildGrpcWebBody(endpoint, payload, token) {
        const message = this._encodeRequest(
            endpoint,
            JSON.stringify(payload ?? {}),
            token || ''
        );
        return this._wrapFrame(0x00, message);
        }

    _encodeRequest(endpoint, payloadJson, authToken) {
        const bytes = [];

        if (endpoint) {
            bytes.push(...this._encodeStringField(1, endpoint));
        }
        if (payloadJson) {
            bytes.push(...this._encodeStringField(2, payloadJson));
        }
        if (authToken) {
            bytes.push(...this._encodeStringField(3, authToken));
        }

        return new Uint8Array(bytes);
    }

    _encodeStringField(fieldNumber, value) {
        const header = (fieldNumber << 3) | 2;
        const valueBytes = this.textEncoder.encode(value);
        return [
            header,
            ...this._encodeVarint(valueBytes.length),
            ...valueBytes
        ];
    }

    _encodeVarint(value) {
        const chunks = [];
        let current = value >>> 0;
        while (current >= 0x80) {
            chunks.push((current & 0x7F) | 0x80);
            current >>>= 7;
        }
        chunks.push(current);
        return chunks;
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

