/**
 * DOM操作工具类
 * 统一DOM操作，避免直接操作DOM，确保健壮性
 * 
 * @module DomUtils
 */

class DomUtils {
    /**
     * 安全获取元素
     * @param {string} id - 元素ID
     * @param {boolean} throwIfMissing - 如果元素不存在是否抛出错误
     * @returns {HTMLElement|null}
     */
    static getElement(id, throwIfMissing = false) {
        const element = document.getElementById(id);
        
        if (!element && throwIfMissing) {
            throw new Error(`元素不存在: #${id}`);
        }
        
        return element;
    }

    /**
     * 安全获取多个元素
     * @param {string[]} ids - 元素ID数组
     * @returns {Object} 元素对象，key为ID，value为元素
     */
    static getElements(ids) {
        const elements = {};
        
        ids.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                elements[id] = element;
            }
        });
        
        return elements;
    }

    /**
     * 设置元素文本内容
     * @param {string} id - 元素ID
     * @param {string} text - 文本内容
     * @param {boolean} throwIfMissing - 如果元素不存在是否抛出错误
     */
    static setText(id, text, throwIfMissing = false) {
        const element = this.getElement(id, throwIfMissing);
        if (element) {
            element.textContent = text || '';
        }
    }

    /**
     * 设置元素HTML内容（谨慎使用）
     * @param {string} id - 元素ID
     * @param {string} html - HTML内容
     * @param {boolean} throwIfMissing - 如果元素不存在是否抛出错误
     */
    static setHTML(id, html, throwIfMissing = false) {
        const element = this.getElement(id, throwIfMissing);
        if (element) {
            element.innerHTML = html || '';
        }
    }

    /**
     * 设置元素显示/隐藏
     * @param {string} id - 元素ID
     * @param {boolean} show - 是否显示
     * @param {string} display - display样式值（默认'block'）
     */
    static setVisibility(id, show, display = 'block') {
        const element = this.getElement(id);
        if (element) {
            if (show) {
                element.style.display = display;
                element.style.visibility = 'visible';
                element.style.opacity = '1';
            } else {
                element.style.display = 'none';
            }
        }
    }

    /**
     * 显示元素
     * @param {string|string[]} id - 元素ID或ID数组
     * @param {string} display - display样式值
     */
    static show(id, display = 'block') {
        const ids = Array.isArray(id) ? id : [id];
        ids.forEach(elementId => {
            this.setVisibility(elementId, true, display);
        });
    }

    /**
     * 隐藏元素
     * @param {string|string[]} id - 元素ID或ID数组
     */
    static hide(id) {
        const ids = Array.isArray(id) ? id : [id];
        ids.forEach(elementId => {
            this.setVisibility(elementId, false);
        });
    }

    /**
     * 切换元素显示/隐藏
     * @param {string} id - 元素ID
     * @param {string} display - display样式值
     */
    static toggle(id, display = 'block') {
        const element = this.getElement(id);
        if (element) {
            const isVisible = element.style.display !== 'none' && 
                             window.getComputedStyle(element).display !== 'none';
            this.setVisibility(id, !isVisible, display);
        }
    }

    /**
     * 设置元素属性
     * @param {string} id - 元素ID
     * @param {string} name - 属性名
     * @param {string} value - 属性值
     */
    static setAttribute(id, name, value) {
        const element = this.getElement(id);
        if (element) {
            element.setAttribute(name, value);
        }
    }

    /**
     * 获取元素属性
     * @param {string} id - 元素ID
     * @param {string} name - 属性名
     * @returns {string|null}
     */
    static getAttribute(id, name) {
        const element = this.getElement(id);
        return element ? element.getAttribute(name) : null;
    }

    /**
     * 移除元素属性
     * @param {string} id - 元素ID
     * @param {string} name - 属性名
     */
    static removeAttribute(id, name) {
        const element = this.getElement(id);
        if (element) {
            element.removeAttribute(name);
        }
    }

    /**
     * 设置元素CSS类
     * @param {string} id - 元素ID
     * @param {string|string[]} className - CSS类名或类名数组
     */
    static addClass(id, className) {
        const element = this.getElement(id);
        if (element) {
            const classes = Array.isArray(className) ? className : [className];
            classes.forEach(cls => {
                element.classList.add(cls);
            });
        }
    }

    /**
     * 移除元素CSS类
     * @param {string} id - 元素ID
     * @param {string|string[]} className - CSS类名或类名数组
     */
    static removeClass(id, className) {
        const element = this.getElement(id);
        if (element) {
            const classes = Array.isArray(className) ? className : [className];
            classes.forEach(cls => {
                element.classList.remove(cls);
            });
        }
    }

    /**
     * 切换元素CSS类
     * @param {string} id - 元素ID
     * @param {string} className - CSS类名
     */
    static toggleClass(id, className) {
        const element = this.getElement(id);
        if (element) {
            element.classList.toggle(className);
        }
    }

    /**
     * 检查元素是否有CSS类
     * @param {string} id - 元素ID
     * @param {string} className - CSS类名
     * @returns {boolean}
     */
    static hasClass(id, className) {
        const element = this.getElement(id);
        return element ? element.classList.contains(className) : false;
    }

    /**
     * 设置元素样式
     * @param {string} id - 元素ID
     * @param {string|Object} style - CSS样式字符串或样式对象
     */
    static setStyle(id, style) {
        const element = this.getElement(id);
        if (element) {
            if (typeof style === 'string') {
                element.style.cssText = style;
            } else if (typeof style === 'object') {
                Object.assign(element.style, style);
            }
        }
    }

    /**
     * 滚动到元素
     * @param {string} id - 元素ID
     * @param {Object} options - 滚动选项
     */
    static scrollTo(id, options = {}) {
        const element = this.getElement(id);
        if (element) {
            const defaultOptions = {
                behavior: 'smooth',
                block: 'center'
            };
            
            element.scrollIntoView({
                ...defaultOptions,
                ...options
            });
        }
    }

    /**
     * 绑定事件监听器
     * @param {string} id - 元素ID
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     * @param {boolean|Object} options - 事件选项
     * @returns {Function} 解绑函数
     */
    static on(id, event, handler, options = false) {
        const element = this.getElement(id);
        if (element) {
            element.addEventListener(event, handler, options);
            
            // 返回解绑函数
            return () => {
                element.removeEventListener(event, handler, options);
            };
        }
        return () => {};
    }

    /**
     * 解绑事件监听器
     * @param {string} id - 元素ID
     * @param {string} event - 事件类型
     * @param {Function} handler - 事件处理函数
     * @param {boolean|Object} options - 事件选项
     */
    static off(id, event, handler, options = false) {
        const element = this.getElement(id);
        if (element) {
            element.removeEventListener(event, handler, options);
        }
    }

    /**
     * 设置表单字段值
     * @param {string} id - 字段ID
     * @param {any} value - 字段值
     */
    static setFormValue(id, value) {
        const element = this.getElement(id);
        if (element) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.value = value || '';
            } else if (element.tagName === 'SELECT') {
                element.value = value || '';
            } else if (element.hasAttribute('contenteditable')) {
                element.textContent = value || '';
            }
        }
    }

    /**
     * 获取表单字段值
     * @param {string} id - 字段ID
     * @returns {any}
     */
    static getFormValue(id) {
        const element = this.getElement(id);
        if (!element) {
            return null;
        }

        if (element.tagName === 'INPUT') {
            if (element.type === 'checkbox') {
                return element.checked;
            } else if (element.type === 'radio') {
                return element.checked ? element.value : null;
            }
            return element.value;
        } else if (element.tagName === 'TEXTAREA' || element.tagName === 'SELECT') {
            return element.value;
        } else if (element.hasAttribute('contenteditable')) {
            return element.textContent;
        }

        return null;
    }

    /**
     * 禁用/启用元素
     * @param {string} id - 元素ID
     * @param {boolean} disabled - 是否禁用
     */
    static setDisabled(id, disabled) {
        const element = this.getElement(id);
        if (element) {
            element.disabled = disabled;
        }
    }

    /**
     * 检查元素是否存在
     * @param {string} id - 元素ID
     * @returns {boolean}
     */
    static exists(id) {
        return document.getElementById(id) !== null;
    }

    /**
     * 等待元素出现
     * @param {string} id - 元素ID
     * @param {number} timeout - 超时时间（毫秒）
     * @returns {Promise<HTMLElement>}
     */
    static async waitForElement(id, timeout = 5000) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
            const element = document.getElementById(id);
            if (element) {
                return element;
            }
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        throw new Error(`元素未在 ${timeout}ms 内出现: #${id}`);
    }

    /**
     * 批量操作元素
     * @param {string[]} ids - 元素ID数组
     * @param {Function} callback - 回调函数 (element, id) => void
     */
    static forEach(ids, callback) {
        ids.forEach(id => {
            const element = this.getElement(id);
            if (element && callback) {
                callback(element, id);
            }
        });
    }
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.DomUtils = DomUtils;
}

// 支持ES模块导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DomUtils;
}

