// 认证相关
class Auth {
    static async login(username, password) {
        try {
            const response = await api.post('/auth/login', {
                username,
                password
            });
            
            if (response.access_token) {
                localStorage.setItem(TOKEN_KEY, response.access_token);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
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


