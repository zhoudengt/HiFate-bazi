// UserInfo 工具类 - 用于管理用户信息（生辰信息）
// 替代原来的 auth.js 中的 UserInfo，但只保留生辰信息相关功能

const UserInfo = {
    /**
     * 从 localStorage 加载用户信息
     * @returns {Object|null} 用户信息对象 {solar_date, solar_time, gender} 或 null
     */
    load() {
        try {
            const solar_date = localStorage.getItem('solar_date');
            const solar_time = localStorage.getItem('solar_time');
            const gender = localStorage.getItem('gender');
            
            if (solar_date && solar_time && gender) {
                return {
                    solar_date,
                    solar_time,
                    gender
                };
            }
            return null;
        } catch (e) {
            console.error('加载用户信息失败:', e);
            return null;
        }
    },
    
    /**
     * 保存用户信息到 localStorage
     * @param {string} solar_date - 出生日期
     * @param {string} solar_time - 出生时间
     * @param {string} gender - 性别 (male/female)
     */
    save(solar_date, solar_time, gender) {
        try {
            localStorage.setItem('solar_date', solar_date);
            localStorage.setItem('solar_time', solar_time);
            localStorage.setItem('gender', gender);
        } catch (e) {
            console.error('保存用户信息失败:', e);
        }
    },
    
    /**
     * 填充表单字段
     * 从 localStorage 读取信息并填充到表单中
     */
    fillForm() {
        try {
            const userInfo = this.load();
            if (!userInfo) {
                return;
            }
            
            // 填充日期字段
            const dateInput = document.getElementById('solar_date') || document.getElementById('date') || document.querySelector('input[type="date"]');
            if (dateInput) {
                dateInput.value = userInfo.solar_date;
            }
            
            // 填充时间字段
            const timeInput = document.getElementById('solar_time') || document.getElementById('time') || document.querySelector('input[type="time"]');
            if (timeInput) {
                timeInput.value = userInfo.solar_time;
            }
            
            // 填充性别字段
            const genderSelect = document.getElementById('gender') || document.querySelector('select[name="gender"]');
            if (genderSelect) {
                genderSelect.value = userInfo.gender;
            }
        } catch (e) {
            console.error('填充表单失败:', e);
        }
    }
};

// 暴露到全局
window.UserInfo = UserInfo;

