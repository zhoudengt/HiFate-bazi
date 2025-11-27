// API 配置
const API_CONFIG = {
    baseURL: 'http://127.0.0.1:8001/api/v1',
    timeout: 60000,  // 60秒超时（fortune接口计算量大）
    fortuneApiKey: 'fortune_analysis_default_key_2024'  // 面相手相分析 API Key
};

// gRPC-Web 配置（前端调用通用网关）
const GRPC_CONFIG = {
    enabled: true,
    baseURL: 'http://127.0.0.1:8001/api/grpc-web',
    timeout: 60000,
    // 为空表示允许调用所有已注册的 REST 端点
    endpoints: []
};

// 存储 Token 的 key
const TOKEN_KEY = 'bazi_token';

