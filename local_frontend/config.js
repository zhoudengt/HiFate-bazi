// ============================================
// HiFate-bazi API 配置
// 自动识别开发/生产环境，无需手动切换
// 支持通过 URL 参数 ?env=production 切换到生产环境
// ============================================

// 解析 URL 参数
function getUrlParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// 检查是否通过 URL 参数强制切换到生产环境（在配置计算时实时读取）
function getForceProduction() {
    return getUrlParam('env') === 'production';
}

const productionNode = '8.210.52.217'; // Node1 生产服务器

// API 配置 - 自动识别环境
const API_CONFIG = (function() {
    const hostname = window.location.hostname;
    const port = window.location.port || '8001';
    
    // 生产环境域名/IP 列表
    const PRODUCTION_HOSTS = [
        '123.57.216.15',        // 测试环境
        '8.210.52.217',         // Node1（生产环境）
        '47.243.160.43',        // Node2（生产环境）
        // 'your-domain.com',   // 未来的域名
    ];
    
    // 判断当前环境（URL 参数优先，实时读取）
    const forceProduction = getForceProduction();
    const isProduction = forceProduction || PRODUCTION_HOSTS.includes(hostname);
    
    // 根据环境返回配置
    if (isProduction) {
        // === 生产环境 ===
        // 如果通过 URL 参数强制切换，使用指定的生产节点
        const targetHost = forceProduction ? productionNode : hostname;
        return {
            baseURL: `http://${targetHost}:8001/api/v1`,
            timeout: 60000,
            fortuneApiKey: 'fortune_analysis_default_key_2024',
            env: 'production'
        };
    } else {
        // === 开发环境 ===
        // 前端页面可能在 8080 端口，但后端 API 在 8001 端口
        const apiPort = (hostname === 'localhost' || hostname === '127.0.0.1') ? '8001' : port;
        return {
            baseURL: `http://${hostname}:${apiPort}/api/v1`,
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
        '123.57.216.15',        // 测试环境
        '8.210.52.217',         // Node1（生产环境）
        '47.243.160.43',        // Node2（生产环境）
    ];
    
    // 判断当前环境（URL 参数优先，实时读取）
    const forceProduction = getForceProduction();
    const isProduction = forceProduction || PRODUCTION_HOSTS.includes(hostname);
    
    // 如果通过 URL 参数强制切换，使用指定的生产节点
    const targetHost = forceProduction ? productionNode : hostname;
    
    // 开发环境：前端可能在 8080 端口，但后端 gRPC 在 8001 端口
    const grpcPort = isProduction ? '8001' : ((hostname === 'localhost' || hostname === '127.0.0.1') ? '8001' : port);
    const baseHost = `http://${targetHost}:${grpcPort}`;
    
    return {
        enabled: true,
        baseURL: baseHost + '/api/grpc-web',
        timeout: 60000,
        endpoints: [],
        env: isProduction ? 'production' : 'development'
    };
})();

// Token 功能已移除

// 调试信息（显示当前环境配置）
(function() {
    const forceProduction = getForceProduction();
if (forceProduction) {
    console.log('🌐 生产环境（URL 参数强制切换）');
    console.log('📍 目标服务器:', productionNode);
    console.log('📍 API 地址:', API_CONFIG.baseURL);
    console.log('📍 gRPC 地址:', GRPC_CONFIG.baseURL);
} else if (API_CONFIG.env === 'development') {
    console.log('🔧 开发环境');
    console.log('📍 API 地址:', API_CONFIG.baseURL);
    console.log('📍 gRPC 地址:', GRPC_CONFIG.baseURL);
}
})();
