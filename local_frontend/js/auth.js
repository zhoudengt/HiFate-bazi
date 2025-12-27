// 认证相关功能
class Auth {
    static async login(username, password) {
        console.log('🔐 开始登录，用户名:', username);
        console.log('📡 调用 gRPC 网关: /auth/login');
        
        try {
            const response = await api.post('/auth/login', {
                username: username,
                password: password
            });
            
            console.log('✅ 登录成功，响应:', response);
            
            // 保存 token
            if (response && response.access_token) {
                localStorage.setItem('token', response.access_token);
                console.log('✅ Token 已保存到 localStorage');
            } else if (response && response.token) {
                localStorage.setItem('token', response.token);
                console.log('✅ Token 已保存到 localStorage');
            }
            
            return response;
        } catch (error) {
            console.error('❌ Login error:', error);
            console.error('错误详情:', error.message);
            console.error('错误堆栈:', error.stack);
            throw error;
        }
    }
    
    static logout() {
        localStorage.removeItem('token');
        console.log('✅ 已登出，Token 已清除');
    }
    
    static getToken() {
        return localStorage.getItem('token');
    }
    
    static isLoggedIn() {
        return !!localStorage.getItem('token');
    }
}

