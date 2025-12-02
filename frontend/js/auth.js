// 认证相关
class Auth {
    static async login(username, password) {
        try {
            console.log('🔐 开始登录，用户名:', username);
            console.log('📡 调用 gRPC 网关: /auth/login');
            
            const response = await api.post('/auth/login', {
                username,
                password
            });
            
            console.log('✅ 登录响应:', response);
            
            if (response && response.access_token) {
                localStorage.setItem(TOKEN_KEY, response.access_token);
                console.log('✅ 登录成功，token 已保存到 localStorage');
                return true;
            }
            
            console.warn('⚠️ 登录响应中没有 access_token');
            console.warn('响应内容:', JSON.stringify(response, null, 2));
            throw new Error('登录响应格式错误：缺少 access_token');
            
        } catch (error) {
            console.error('❌ Login error:', error);
            console.error('错误详情:', error.message);
            if (error.stack) {
                console.error('错误堆栈:', error.stack);
            }
            
            // 提供更友好的错误信息
            let errorMessage = '登录失败';
            if (error.message) {
                errorMessage = error.message;
                // 如果是用户名密码错误，直接显示
                if (error.message.includes('用户名或密码错误') || error.message.includes('401')) {
                    errorMessage = '用户名或密码错误';
                }
            } else if (error.name === 'TypeError' && error.message && error.message.includes('fetch')) {
                errorMessage = '无法连接到服务器，请检查网络连接和服务是否启动';
            } else if (error.message && error.message.includes('gRPC')) {
                errorMessage = '服务器通信错误，请稍后重试';
            }
            
            throw new Error(errorMessage);
        }
    }

    static logout() {
        localStorage.removeItem(TOKEN_KEY);
        window.location.href = 'login.html';
    }

    static isAuthenticated() {
        return !!localStorage.getItem(TOKEN_KEY);
    }

    static checkAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = 'login.html';
        }
    }
}

// 用户信息存储（用于跨页面共享）
class UserInfo {
    static KEY = 'bazi_user_info';
    
    static save(solar_date, solar_time, gender) {
        const info = {
            solar_date,
            solar_time,
            gender,
            timestamp: Date.now()
        };
        localStorage.setItem(this.KEY, JSON.stringify(info));
    }
    
    static load() {
        const infoStr = localStorage.getItem(this.KEY);
        if (infoStr) {
            try {
                return JSON.parse(infoStr);
            } catch (e) {
                return null;
            }
        }
        return null;
    }
    
    static clear() {
        localStorage.removeItem(this.KEY);
    }
    
    static fillForm() {
        const info = this.load();
        if (info) {
            const dateInput = document.getElementById('solar_date');
            const timeInput = document.getElementById('solar_time');
            const genderSelect = document.getElementById('gender');
            
            if (dateInput) dateInput.value = info.solar_date || '';
            if (timeInput) timeInput.value = info.solar_time || '';
            if (genderSelect) genderSelect.value = info.gender || 'male';
        }
    }
}


