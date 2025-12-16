/**
 * 统一前端错误处理工具
 * 符合开发规范：所有错误处理必须同时更新内容和显示状态
 * 
 * @module ErrorHandler
 */

class ErrorHandler {
    /**
     * 显示错误信息
     * @param {string} message - 错误消息
     * @param {Object} options - 配置选项
     * @param {string} options.containerId - 错误容器ID（如果不存在会自动查找）
     * @param {string} options.sectionId - 需要显示的UI区域ID（可选）
     * @param {boolean} options.autoHide - 是否自动隐藏（默认false）
     * @param {number} options.hideDelay - 自动隐藏延迟（毫秒，默认5000）
     * @param {boolean} options.scrollTo - 是否滚动到错误区域（默认true）
     * @returns {HTMLElement|null} 错误容器元素
     */
    static showError(message, options = {}) {
        const {
            containerId,
            sectionId,
            autoHide = false,
            hideDelay = 5000,
            scrollTo = true
        } = options;

        // 1. 查找或创建错误容器
        let errorContainer = containerId 
            ? document.getElementById(containerId)
            : this._findErrorContainer();

        if (!errorContainer) {
            // 如果找不到错误容器，创建一个
            errorContainer = this._createErrorContainer();
        }

        // 2. 更新错误内容
        errorContainer.textContent = '❌ ' + message;
        errorContainer.className = 'error-message error-visible';
        
        // 3. 显示错误容器（关键：确保可见）
        errorContainer.style.display = 'block';
        errorContainer.style.visibility = 'visible';
        errorContainer.style.opacity = '1';

        // 4. 显示相关UI区域（如果指定）
        if (sectionId) {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
                section.style.visibility = 'visible';
            }
        }

        // 5. 滚动到错误区域（提升用户体验）
        if (scrollTo) {
            setTimeout(() => {
                errorContainer.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }, 100);
        }

        // 6. 自动隐藏（如果启用）
        if (autoHide) {
            setTimeout(() => {
                this.hideError(containerId);
            }, hideDelay);
        }

        // 7. 控制台记录（便于调试）
        console.error('前端错误:', message);

        return errorContainer;
    }

    /**
     * 隐藏错误信息
     * @param {string|null} containerId - 错误容器ID，如果为null则自动查找
     */
    static hideError(containerId = null) {
        const errorContainer = containerId
            ? document.getElementById(containerId)
            : this._findErrorContainer();
        
        if (errorContainer) {
            errorContainer.style.display = 'none';
            errorContainer.textContent = '';
            errorContainer.className = 'error-message';
        }
    }

    /**
     * 显示成功消息
     * @param {string} message - 成功消息
     * @param {Object} options - 配置选项
     */
    static showSuccess(message, options = {}) {
        const {
            containerId,
            autoHide = true,
            hideDelay = 3000,
            scrollTo = false
        } = options;

        let successContainer = containerId
            ? document.getElementById(containerId)
            : this._findSuccessContainer();

        if (!successContainer) {
            successContainer = this._createSuccessContainer();
        }

        successContainer.textContent = '✅ ' + message;
        successContainer.className = 'success-message success-visible';
        successContainer.style.display = 'block';
        successContainer.style.visibility = 'visible';
        successContainer.style.opacity = '1';

        if (scrollTo) {
            setTimeout(() => {
                successContainer.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }, 100);
        }

        if (autoHide) {
            setTimeout(() => {
                this.hideSuccess(containerId);
            }, hideDelay);
        }
    }

    /**
     * 隐藏成功消息
     * @param {string|null} containerId - 成功容器ID
     */
    static hideSuccess(containerId = null) {
        const successContainer = containerId
            ? document.getElementById(containerId)
            : this._findSuccessContainer();
        
        if (successContainer) {
            successContainer.style.display = 'none';
            successContainer.textContent = '';
            successContainer.className = 'success-message';
        }
    }

    /**
     * 提前显示UI区域（关键阶段使用）
     * @param {string|string[]} sectionId - UI区域ID或ID数组
     */
    static showSection(sectionId) {
        const ids = Array.isArray(sectionId) ? sectionId : [sectionId];
        
        ids.forEach(id => {
            const section = document.getElementById(id);
            if (section) {
                section.style.display = 'block';
                section.style.visibility = 'visible';
                section.style.opacity = '1';
            }
        });
    }

    /**
     * 隐藏UI区域
     * @param {string|string[]} sectionId - UI区域ID或ID数组
     */
    static hideSection(sectionId) {
        const ids = Array.isArray(sectionId) ? sectionId : [sectionId];
        
        ids.forEach(id => {
            const section = document.getElementById(id);
            if (section) {
                section.style.display = 'none';
            }
        });
    }

    /**
     * 处理API错误
     * @param {Error|string} error - 错误对象或错误消息
     * @param {Object} options - 配置选项
     * @returns {HTMLElement|null} 错误容器元素
     */
    static handleApiError(error, options = {}) {
        let errorMessage = '操作失败';

        // 解析错误信息
        if (error instanceof Error) {
            errorMessage = error.message || '操作失败';
        } else if (typeof error === 'string') {
            errorMessage = error;
        } else if (error && typeof error === 'object' && error.message) {
            errorMessage = error.message;
        }

        // 友好化错误信息
        if (errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Failed to fetch')) {
            errorMessage = '网络连接失败，请检查网络连接';
        } else if (errorMessage.includes('401') || errorMessage.includes('未授权') || errorMessage.includes('unauthorized')) {
            errorMessage = '登录已过期，请重新登录';
            // 自动跳转到登录页
            setTimeout(() => {
                if (window.location.pathname !== '/login.html' && window.location.pathname !== '/local_frontend/login.html') {
                    window.location.href = 'login.html';
                }
            }, 2000);
        } else if (errorMessage.includes('403') || errorMessage.includes('禁止') || errorMessage.includes('forbidden')) {
            errorMessage = '权限不足，无法执行此操作';
        } else if (errorMessage.includes('404') || errorMessage.includes('不存在') || errorMessage.includes('not found')) {
            errorMessage = '请求的资源不存在';
        } else if (errorMessage.includes('500') || errorMessage.includes('服务器') || errorMessage.includes('server error')) {
            errorMessage = '服务器错误，请稍后重试';
        } else if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
            errorMessage = '请求超时，请稍后重试';
        }

        // 显示错误
        return this.showError(errorMessage, options);
    }

    /**
     * 查找错误容器（自动检测常见的错误容器ID）
     * @private
     * @returns {HTMLElement|null}
     */
    static _findErrorContainer() {
        const commonIds = [
            'errorMessage',
            'errorMsg',
            'error-message',
            'errorContainer',
            'error-container'
        ];

        for (const id of commonIds) {
            const element = document.getElementById(id);
            if (element) {
                return element;
            }
        }

        return null;
    }

    /**
     * 查找成功容器
     * @private
     * @returns {HTMLElement|null}
     */
    static _findSuccessContainer() {
        const commonIds = [
            'successMessage',
            'successMsg',
            'success-message',
            'successContainer'
        ];

        for (const id of commonIds) {
            const element = document.getElementById(id);
            if (element) {
                return element;
            }
        }

        return null;
    }

    /**
     * 创建错误容器（如果页面没有）
     * @private
     * @returns {HTMLElement}
     */
    static _createErrorContainer() {
        const container = document.createElement('div');
        container.id = 'errorMessage';
        container.className = 'error-message error-visible';
        container.style.cssText = `
            display: block;
            padding: 15px;
            margin: 20px 0;
            background-color: #fee;
            border: 1px solid #fcc;
            border-left: 4px solid #f44;
            border-radius: 5px;
            color: #c33;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(244, 68, 68, 0.1);
        `;
        
        // 插入到页面顶部
        const body = document.body;
        const firstChild = body.firstChild;
        if (firstChild) {
            body.insertBefore(container, firstChild);
        } else {
            body.appendChild(container);
        }

        return container;
    }

    /**
     * 创建成功容器
     * @private
     * @returns {HTMLElement}
     */
    static _createSuccessContainer() {
        const container = document.createElement('div');
        container.id = 'successMessage';
        container.className = 'success-message success-visible';
        container.style.cssText = `
            display: block;
            padding: 15px;
            margin: 20px 0;
            background-color: #efe;
            border: 1px solid #cfc;
            border-left: 4px solid #4c4;
            border-radius: 5px;
            color: #3c3;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(68, 204, 68, 0.1);
        `;
        
        const body = document.body;
        const firstChild = body.firstChild;
        if (firstChild) {
            body.insertBefore(container, firstChild);
        } else {
            body.appendChild(container);
        }

        return container;
    }

    /**
     * 重试机制包装器
     * @param {Function} fn - 要执行的异步函数
     * @param {number} maxRetries - 最大重试次数
     * @param {number} delay - 重试延迟（毫秒）
     * @returns {Promise<any>}
     */
    static async withRetry(fn, maxRetries = 3, delay = 1000) {
        let lastError;
        
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await fn();
            } catch (error) {
                lastError = error;
                if (i < maxRetries - 1) {
                    console.warn(`重试 ${i + 1}/${maxRetries - 1}:`, error.message);
                    await new Promise(resolve => setTimeout(resolve, delay * (i + 1)));
                }
            }
        }
        
        throw lastError;
    }
}

// 全局错误捕获
if (typeof window !== 'undefined') {
    // 捕获未处理的错误
    window.addEventListener('error', (event) => {
        console.error('全局错误捕获:', event.error);
        ErrorHandler.handleApiError(event.error, {
            scrollTo: true
        });
    });

    // 捕获未处理的Promise rejection
    window.addEventListener('unhandledrejection', (event) => {
        console.error('未处理的Promise rejection:', event.reason);
        ErrorHandler.handleApiError(event.reason, {
            scrollTo: true
        });
    });
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.ErrorHandler = ErrorHandler;
}

// 支持ES模块导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
}

