/**
 * 数据验证工具类
 * 统一数据验证，确保数据格式正确
 * 
 * @module Validator
 */

class Validator {
    /**
     * 验证非空
     * @param {any} value - 要验证的值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static required(value, fieldName = '字段') {
        if (value === null || value === undefined || value === '') {
            throw new Error(`${fieldName}不能为空`);
        }
        return true;
    }

    /**
     * 验证字符串长度
     * @param {string} value - 字符串值
     * @param {number} min - 最小长度
     * @param {number} max - 最大长度
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static length(value, min, max, fieldName = '字段') {
        if (typeof value !== 'string') {
            throw new Error(`${fieldName}必须是字符串`);
        }
        
        if (min !== undefined && value.length < min) {
            throw new Error(`${fieldName}长度不能少于${min}个字符`);
        }
        
        if (max !== undefined && value.length > max) {
            throw new Error(`${fieldName}长度不能超过${max}个字符`);
        }
        
        return true;
    }

    /**
     * 验证日期格式（YYYY-MM-DD）
     * @param {string} value - 日期字符串
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static date(value, fieldName = '日期') {
        if (!value || typeof value !== 'string') {
            throw new Error(`${fieldName}格式错误`);
        }
        
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(value)) {
            throw new Error(`${fieldName}格式错误，应为 YYYY-MM-DD`);
        }
        
        const date = new Date(value);
        if (isNaN(date.getTime())) {
            throw new Error(`${fieldName}无效`);
        }
        
        return true;
    }

    /**
     * 验证时间格式（HH:MM）
     * @param {string} value - 时间字符串
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static time(value, fieldName = '时间') {
        if (!value || typeof value !== 'string') {
            throw new Error(`${fieldName}格式错误`);
        }
        
        const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
        if (!timeRegex.test(value)) {
            throw new Error(`${fieldName}格式错误，应为 HH:MM`);
        }
        
        return true;
    }

    /**
     * 验证日期时间格式
     * @param {string} value - 日期时间字符串
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static datetime(value, fieldName = '日期时间') {
        if (!value || typeof value !== 'string') {
            throw new Error(`${fieldName}格式错误`);
        }
        
        const datetimeRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/;
        if (!datetimeRegex.test(value)) {
            throw new Error(`${fieldName}格式错误，应为 YYYY-MM-DD HH:MM:SS`);
        }
        
        const date = new Date(value);
        if (isNaN(date.getTime())) {
            throw new Error(`${fieldName}无效`);
        }
        
        return true;
    }

    /**
     * 验证邮箱格式
     * @param {string} value - 邮箱字符串
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static email(value, fieldName = '邮箱') {
        if (!value || typeof value !== 'string') {
            throw new Error(`${fieldName}格式错误`);
        }
        
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            throw new Error(`${fieldName}格式错误`);
        }
        
        return true;
    }

    /**
     * 验证数字范围
     * @param {number} value - 数字值
     * @param {number} min - 最小值
     * @param {number} max - 最大值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static range(value, min, max, fieldName = '数值') {
        if (typeof value !== 'number' || isNaN(value)) {
            throw new Error(`${fieldName}必须是数字`);
        }
        
        if (min !== undefined && value < min) {
            throw new Error(`${fieldName}不能小于${min}`);
        }
        
        if (max !== undefined && value > max) {
            throw new Error(`${fieldName}不能大于${max}`);
        }
        
        return true;
    }

    /**
     * 验证整数
     * @param {any} value - 值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static integer(value, fieldName = '字段') {
        if (!Number.isInteger(Number(value))) {
            throw new Error(`${fieldName}必须是整数`);
        }
        return true;
    }

    /**
     * 验证性别
     * @param {string} value - 性别值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static gender(value, fieldName = '性别') {
        const validGenders = ['male', 'female', '男', '女'];
        if (!validGenders.includes(value)) {
            throw new Error(`${fieldName}必须是 male/female 或 男/女`);
        }
        return true;
    }

    /**
     * 验证年份
     * @param {number|string} value - 年份值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static year(value, fieldName = '年份') {
        const year = Number(value);
        if (isNaN(year) || !Number.isInteger(year)) {
            throw new Error(`${fieldName}必须是整数`);
        }
        
        if (year < 1900 || year > 2100) {
            throw new Error(`${fieldName}必须在 1900-2100 之间`);
        }
        
        return true;
    }

    /**
     * 验证月份
     * @param {number|string} value - 月份值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static month(value, fieldName = '月份') {
        const month = Number(value);
        if (isNaN(month) || !Number.isInteger(month)) {
            throw new Error(`${fieldName}必须是整数`);
        }
        
        if (month < 1 || month > 12) {
            throw new Error(`${fieldName}必须在 1-12 之间`);
        }
        
        return true;
    }

    /**
     * 验证日期（月份内的日期）
     * @param {number|string} value - 日期值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static day(value, fieldName = '日期') {
        const day = Number(value);
        if (isNaN(day) || !Number.isInteger(day)) {
            throw new Error(`${fieldName}必须是整数`);
        }
        
        if (day < 1 || day > 31) {
            throw new Error(`${fieldName}必须在 1-31 之间`);
        }
        
        return true;
    }

    /**
     * 验证小时
     * @param {number|string} value - 小时值
     * @param {string} fieldName - 字段名
     * @throws {Error} 如果验证失败
     */
    static hour(value, fieldName = '小时') {
        const hour = Number(value);
        if (isNaN(hour) || !Number.isInteger(hour)) {
            throw new Error(`${fieldName}必须是整数`);
        }
        
        if (hour < 0 || hour > 23) {
            throw new Error(`${fieldName}必须在 0-23 之间`);
        }
        
        return true;
    }

    /**
     * 验证八字输入数据
     * @param {Object} data - 八字数据
     * @param {string} data.solar_date - 阳历日期
     * @param {string} data.solar_time - 出生时间
     * @param {string} data.gender - 性别
     * @throws {Error} 如果验证失败
     */
    static baziInput(data) {
        if (!data || typeof data !== 'object') {
            throw new Error('八字输入数据无效');
        }
        
        this.required(data.solar_date, '出生日期');
        this.date(data.solar_date, '出生日期');
        
        this.required(data.solar_time, '出生时间');
        this.time(data.solar_time, '出生时间');
        
        this.required(data.gender, '性别');
        this.gender(data.gender, '性别');
        
        return true;
    }

    /**
     * 验证对象
     * @param {Object} data - 要验证的对象
     * @param {Object} rules - 验证规则 {field: [validators]}
     * @returns {Object} 验证结果 {valid: boolean, errors: Object}
     */
    static validate(data, rules) {
        const errors = {};
        
        for (const [field, validators] of Object.entries(rules)) {
            const value = data[field];
            
            for (const validator of validators) {
                try {
                    if (typeof validator === 'function') {
                        validator(value, field);
                    } else if (Array.isArray(validator)) {
                        const [validatorFn, ...args] = validator;
                        validatorFn(value, ...args, field);
                    }
                } catch (error) {
                    if (!errors[field]) {
                        errors[field] = [];
                    }
                    errors[field].push(error.message);
                    break; // 一个字段只显示第一个错误
                }
            }
        }
        
        return {
            valid: Object.keys(errors).length === 0,
            errors
        };
    }
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.Validator = Validator;
}

// 支持ES模块导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Validator;
}

