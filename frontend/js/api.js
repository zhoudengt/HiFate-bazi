// API 调用封装
class ApiClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = localStorage.getItem(TOKEN_KEY);
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers,
            // 添加超时控制
            signal: AbortSignal.timeout(API_CONFIG.timeout || 30000)
        };

        try {
            const response = await fetch(url, config);
            
            // 检查响应状态
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
                throw new Error(errorData.detail || `请求失败: ${response.status}`);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API Error:', error);
            if (error.name === 'AbortError' || error.name === 'TimeoutError') {
                throw new Error('请求超时，请稍后重试');
            }
            throw error;
        }
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async get(endpoint) {
        return this.request(endpoint, {
            method: 'GET'
        });
    }
}

const api = new ApiClient(API_CONFIG.baseURL);

