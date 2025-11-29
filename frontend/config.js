// ============================================
// HiFate-bazi API 配置
// 自动识别开发/生产环境，无需手动切换
// ============================================

// API 配置 - 自动识别环境
const API_CONFIG = (function() {
    const hostname = window.location.hostname;
    const port = window.location.port || '8001';
    
    // 生产环境域名/IP 列表
    const PRODUCTION_HOSTS = [
        '123.57.216.15',        // 阿里云 ECS
        // 'your-domain.com',   // 未来的域名
    ];
    
    // 判断当前环境
    const isProduction = PRODUCTION_HOSTS.includes(hostname);
    
    // 根据环境返回配置
    if (isProduction) {
        // === 生产环境 ===
        return {
            baseURL: `http://${hostname}:8001/api/v1`,
            timeout: 60000,
            fortuneApiKey: 'fortune_analysis_default_key_2024',
            env: 'production'
        };
    } else {
        // === 开发环境 ===
        // 使用当前主机名，支持 localhost 和 127.0.0.1
        return {
            baseURL: `http://${hostname}:${port}/api/v1`,
            timeout: 60000,
            fortuneApiKey: 'fortune_analysis_default_key_2024',
            env: 'development'
        };
    }
})();

// gRPC-Web 配置 - 自动识别环境
const GRPC_CONFIG = (function() {
    const hostname = window.location.hostname;
    const port = window.location.port || '8001';
    
    // 生产环境域名/IP 列表
    const PRODUCTION_HOSTS = [
        '123.57.216.15',
    ];
    
    const isProduction = PRODUCTION_HOSTS.includes(hostname);
    // 开发环境使用当前主机名（支持 localhost 和 127.0.0.1）
    const baseHost = isProduction ? `http://${hostname}:8001` : `http://${hostname}:${port}`;
    
    return {
        enabled: true,
        baseURL: baseHost + '/api/grpc-web',
        timeout: 60000,
        endpoints: [],
        env: isProduction ? 'production' : 'development'
    };
})();

// 存储 Token 的 key
const TOKEN_KEY = 'bazi_token';

// 调试信息（生产环境自动隐藏）
if (API_CONFIG.env === 'development') {
    console.log('🔧 开发环境');
    console.log('📍 API 地址:', API_CONFIG.baseURL);
    console.log('📍 gRPC 地址:', GRPC_CONFIG.baseURL);
}
