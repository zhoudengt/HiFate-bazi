// 喜神忌神页面逻辑

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', async () => {
    // 从localStorage获取基础八字排盘的生辰信息
    const userInfo = getUserInfo();
    
    if (!userInfo || !userInfo.solar_date || !userInfo.solar_time || !userInfo.gender) {
        // 没有生辰信息，提示用户
        showError('请先在"基础八字排盘"页面输入生辰信息');
        return;
    }
    
    // 显示用户信息
    displayUserInfo(userInfo);
    
    // 加载数据
    await loadXishenJishen(userInfo);
});

// 获取用户信息（从localStorage）
function getUserInfo() {
    try {
        // 使用UserInfo.load()获取
        if (typeof UserInfo !== 'undefined' && UserInfo.load) {
            return UserInfo.load();
        }
        
        return null;
    } catch (e) {
        console.error('获取用户信息失败:', e);
        return null;
    }
}

// 显示用户信息
function displayUserInfo(userInfo) {
    const userInfoCard = document.getElementById('userInfoCard');
    if (userInfoCard) {
        document.getElementById('displayDate').textContent = userInfo.solar_date;
        document.getElementById('displayTime').textContent = userInfo.solar_time;
        document.getElementById('displayGender').textContent = userInfo.gender === 'male' ? '男' : '女';
        userInfoCard.style.display = 'flex';
    }
}

// 加载喜神忌神数据
async function loadXishenJishen(userInfo) {
    try {
        // 临时硬编码生产API用于测试流式效果
        const PRODUCTION_API = 'http://8.210.52.217:8001';
        const response = await fetch(`${PRODUCTION_API}/api/v1/bazi/xishen-jishen`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
            solar_date: userInfo.solar_date,
            solar_time: userInfo.solar_time,
            gender: userInfo.gender
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            showError(result.error || '获取数据失败');
            return;
        }
        
        const data = result.data;
        
        // 显示喜神五行
        displayElements('xiShenElements', data.xi_shen_elements || [], 'xi');
        
        // 显示忌神五行
        displayElements('jiShenElements', data.ji_shen_elements || [], 'ji');
        
        // 显示十神命格
        displayMingge('shishenMingge', data.shishen_mingge || []);
        
        // 开始流式生成大模型分析
        await generateLLMAnalysis(userInfo);
        
    } catch (error) {
        console.error('加载数据失败:', error);
        showError(error.message || '加载数据失败');
    }
}

// 显示五行元素
function displayElements(containerId, elements, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (elements.length === 0) {
        container.innerHTML = '<div style="color: #999;">暂无数据</div>';
        return;
    }
    
    container.innerHTML = elements.map(element => {
        return `
            <div class="element-item ${type}">
                ${element.name}
                <span class="element-id">(ID: ${element.id})</span>
            </div>
        `;
    }).join('');
}

// 显示十神命格
function displayMingge(containerId, minggeList) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (minggeList.length === 0) {
        container.innerHTML = '<div style="color: #999;">暂无数据</div>';
        return;
    }
    
    container.innerHTML = minggeList.map(mingge => {
        return `
            <div class="mingge-item">
                ${mingge.name}
                <span class="mingge-id">(ID: ${mingge.id})</span>
            </div>
        `;
    }).join('');
}

// 流式生成大模型分析 - 使用 EventSource API，实现真正的实时流式显示
async function generateLLMAnalysis(userInfo) {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 同域访问，使用相对路径
    const API_BASE = '/api/v1/bazi/xishen-jishen/stream';
    let fullContent = '';
    let pendingContent = ''; // 待显示的字符队列
    let hasReceivedContent = false;
    let isDisplaying = false; // 是否正在逐字显示
    let displayTimer = null;
    let eventSource = null;
    
    // 逐字显示函数
    const displayCharByChar = () => {
        if (pendingContent.length === 0) {
            isDisplaying = false;
            return;
        }
        
        isDisplaying = true;
        const char = pendingContent[0];
        pendingContent = pendingContent.slice(1);
        fullContent += char;
        llmContent.textContent = fullContent;
        
        // 自动滚动到底部
        if (llmContent.scrollHeight > llmContent.clientHeight) {
            llmContent.scrollTop = llmContent.scrollHeight;
        }
        
        // 继续显示下一个字符（20ms延迟，实现打字机效果）
        displayTimer = setTimeout(displayCharByChar, 20);
    };
    
    // 添加内容到待显示队列
    const addToDisplayQueue = (newContent) => {
        if (newContent) {
            pendingContent += newContent;
            if (!isDisplaying) {
                displayCharByChar();
            }
        }
    };
    
    // 清理函数
    const cleanup = () => {
        if (displayTimer) {
            clearTimeout(displayTimer);
            displayTimer = null;
        }
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    };
    
    try {
        llmContent.innerHTML = '<div class="loading">🔄 正在连接AI服务...</div>';
        
        // EventSource 只支持 GET 请求，通过 URL 参数传递数据
        const params = new URLSearchParams({
            solar_date: userInfo.solar_date,
            solar_time: userInfo.solar_time,
            gender: userInfo.gender
        });
        
        // 如果有其他可选参数，也添加进去
        if (userInfo.calendar_type) {
            params.append('calendar_type', userInfo.calendar_type);
        }
        if (userInfo.location) {
            params.append('location', userInfo.location);
        }
        if (userInfo.latitude !== undefined) {
            params.append('latitude', userInfo.latitude);
        }
        if (userInfo.longitude !== undefined) {
            params.append('longitude', userInfo.longitude);
        }
        
        const apiUrl = `${API_BASE}?${params.toString()}`;
        console.log('📡 开始连接:', apiUrl);
        
        // 使用 EventSource API（浏览器原生 SSE 支持）
        eventSource = new EventSource(apiUrl);
        
        // 连接打开
        eventSource.onopen = () => {
            console.log('📡 EventSource 连接成功，开始接收流式数据...');
        };
        
        // 接收消息（实时触发，无缓冲）
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // 忽略填充数据
                if (data._padding) {
                    return;
                }
                
                if (data.type === 'progress') {
                    const newContent = data.content || '';
                    if (newContent) {
                        hasReceivedContent = true;
                        addToDisplayQueue(newContent);
                        console.log('📨 收到进度数据:', newContent.length, '字符');
                    }
                } else if (data.type === 'complete') {
                    // 完成时，显示剩余内容
                    if (data.content) {
                        addToDisplayQueue(data.content);
                    }
                    console.log('✅ 收到完成消息');
                    // 等待显示队列清空后关闭连接
                    const waitForDisplay = setInterval(() => {
                        if (pendingContent.length === 0 && !isDisplaying) {
                            clearInterval(waitForDisplay);
                            if (fullContent) {
                                llmContent.textContent = fullContent;
                                console.log('✅ 流式传输完成，总长度:', fullContent.length);
                            } else if (!hasReceivedContent) {
                                llmContent.innerHTML = '<div class="error">⚠️ 未收到AI分析内容，请稍后重试</div>';
                            }
                            cleanup();
                        }
                    }, 100);
                } else if (data.type === 'data') {
                    console.log('📊 收到基础数据，等待AI分析...');
                    if (!hasReceivedContent) {
                        llmContent.innerHTML = '<div class="loading">⏳ 正在生成AI分析（大模型生成需要约1-2分钟）...</div>';
                    }
                } else if (data.type === 'heartbeat') {
                    console.log('💓 收到心跳:', data.content);
                    if (!hasReceivedContent) {
                        llmContent.innerHTML = `<div class="loading">⏳ ${data.content || '正在生成AI分析...'}</div>`;
                    }
                } else if (data.type === 'error') {
                    throw new Error(data.content || '生成失败');
                }
            } catch (e) {
                console.warn('解析SSE数据失败:', e.message, '原始数据:', event.data.substring(0, 100));
            }
        };
        
        // 错误处理
        eventSource.onerror = (error) => {
            console.error('EventSource 错误:', error);
            // EventSource 会自动重连，但如果是致命错误，需要手动关闭
            if (eventSource.readyState === EventSource.CLOSED) {
                cleanup();
                if (fullContent) {
                    llmContent.textContent = fullContent;
                } else {
                    llmContent.innerHTML = '<div class="error">⚠️ 连接已关闭，请刷新页面重试</div>';
                }
            }
        };
        
        // 等待完成（EventSource 会保持连接直到服务器关闭）
        // 注意：这里不需要 await，因为 EventSource 是事件驱动的
        
    } catch (error) {
        cleanup();
        console.error('流式生成失败:', error);
        if (fullContent) {
            llmContent.textContent = fullContent;
        } else {
            llmContent.innerHTML = `<div class="error">⚠️ 生成分析失败: ${error.message}</div>`;
        }
    }
}

// 显示错误
function showError(message) {
    const containers = ['xiShenElements', 'jiShenElements', 'shishenMingge', 'llmContent'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = `<div class="error">${message}</div>`;
        }
    });
}

