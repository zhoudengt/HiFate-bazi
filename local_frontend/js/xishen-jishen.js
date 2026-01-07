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
        // 使用相对路径
        const response = await fetch('/api/v1/bazi/xishen-jishen', {
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

// 流式生成大模型分析 - 带打字机效果的真正流式显示
let llmBuffer = '';
let displayQueue = '';  // 待显示的字符队列
let isTyping = false;   // 是否正在打字
let typingTimer = null;
let streamFinished = false;

async function generateLLMAnalysis(userInfo) {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 重置状态
    llmBuffer = '';
    displayQueue = '';
    isTyping = false;
    streamFinished = false;
    if (typingTimer) clearInterval(typingTimer);
    
    // 使用相对路径，适应任何环境
    const url = '/api/v1/bazi/xishen-jishen/stream';
    
    // 显示等待状态提示
    llmContent.innerHTML = '<div class="waiting-status">⏳ 正在等待AI分析，请稍候...</div>';
    llmContent.classList.add('streaming');
    
    // 启动打字机效果
    startTypingEffect();
    
    try {
        console.log('🚀 [DEBUG] 开始流式请求:', url);
        
        // 发送POST请求获取流式响应
        // ⚠️ 关键：添加 Accept-Encoding: identity 禁止服务器压缩 SSE 响应
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept-Encoding': 'identity'  // 禁止 gzip 压缩，确保 SSE 流正常读取
            },
            body: JSON.stringify({
                solar_date: userInfo.solar_date,
                solar_time: userInfo.solar_time,
                gender: userInfo.gender
            })
        });
        
        console.log('📡 [DEBUG] 响应状态:', response.status, response.statusText);
        console.log('📡 [DEBUG] 响应头:', Object.fromEntries(response.headers.entries()));
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // 读取流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let chunkCount = 0;
        
        console.log('📖 [DEBUG] 开始读取流...');
        
        while (true) {
            let result;
            try {
                result = await reader.read();
            } catch (readError) {
                console.error('❌ [DEBUG] reader.read() 错误:', readError);
                throw readError;
            }
            
            const { done, value } = result;
            chunkCount++;
            
            if (done) {
                console.log('✅ [DEBUG] 流结束，共收到', chunkCount, '个数据块');
                break;
            }
            
            const chunk = decoder.decode(value, { stream: true });
            console.log('📥 [DEBUG] 收到数据块 #' + chunkCount + ':', chunk.length, '字节');
            
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后一个不完整的行
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6);
                    if (dataStr.trim() === '[DONE]') {
                        console.log('🏁 [DEBUG] 收到 [DONE] 标记');
                        streamFinished = true;
                        return;
                    }
                    
                    try {
                        const data = JSON.parse(dataStr);
                        console.log('📨 [DEBUG] SSE数据:', data.type, data.content ? data.content.substring(0, 50) : '');
                        handleStreamData(data);
                    } catch (e) {
                        console.warn('解析SSE数据失败:', e, dataStr.substring(0, 100));
                    }
                }
            }
        }
        
        streamFinished = true;
    } catch (error) {
        console.error('❌ [DEBUG] 流式分析失败:', error);
        console.error('❌ [DEBUG] 错误堆栈:', error.stack);
        streamFinished = true;
        stopTypingEffect();
        displayLLMError('流式分析失败: ' + (error.message || '未知错误'));
    }
}

// 打字机效果：每20ms显示一个字符
function startTypingEffect() {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    typingTimer = setInterval(() => {
        if (displayQueue.length > 0) {
            // 从队列中取出一个字符
            const char = displayQueue[0];
            displayQueue = displayQueue.slice(1);
            llmBuffer += char;
            
            // 更新显示（清除等待提示，开始显示内容）
            const html = llmBuffer.replace(/\n/g, '<br>');
            llmContent.innerHTML = html + '<span class="streaming-cursor"></span>';
            
            // 自动滚动到底部
            if (llmContent.scrollHeight > llmContent.clientHeight) {
                llmContent.scrollTop = llmContent.scrollHeight;
            }
        } else if (streamFinished && displayQueue.length === 0) {
            // 流已结束且队列为空，完成显示
            finishLLMAnalysis();
        }
    }, 20);  // 每20ms显示一个字符
}

// 停止打字机效果
function stopTypingEffect() {
    if (typingTimer) {
        clearInterval(typingTimer);
        typingTimer = null;
    }
}

// 处理流式数据
function handleStreamData(data) {
    const type = data.type;
    
    if (type === 'heartbeat') {
        // 心跳包：更新等待提示，让用户知道连接正常
        updateWaitingStatus();
    } else if (type === 'start') {
        displayLLMStart();
    } else if (type === 'progress') {
        if (data.content) {
            // 将内容加入显示队列
            displayQueue += data.content;
        }
    } else if (type === 'complete') {
        if (data.content) {
            // 将内容加入显示队列
            displayQueue += data.content;
        }
        streamFinished = true;
    } else if (type === 'error') {
        streamFinished = true;
        stopTypingEffect();
        displayLLMError(data.error || '分析失败');
    }
}

// 更新等待状态提示
let heartbeatCount = 0;
function updateWaitingStatus() {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 如果还没有开始显示内容，更新等待提示
    if (llmBuffer.length === 0 && displayQueue.length === 0) {
        heartbeatCount++;
        const statuses = [
            '⏳ 正在等待AI分析，请稍候...',
            '🤔 AI正在思考中，请稍候...',
            '💭 AI正在深度分析，请稍候...',
            '🔮 AI正在生成内容，请稍候...'
        ];
        const statusIndex = Math.floor(heartbeatCount / 3) % statuses.length;
        llmContent.innerHTML = `<div class="waiting-status">${statuses[statusIndex]}</div>`;
    }
}

// 显示LLM分析开始
function displayLLMStart() {
    const llmContent = document.getElementById('llmContent');
    llmBuffer = '';
    displayQueue = '';
    heartbeatCount = 0;  // 重置心跳计数
    llmContent.innerHTML = '';
    llmContent.classList.add('streaming');
}

// 完成LLM分析
function finishLLMAnalysis() {
    stopTypingEffect();
    const llmContent = document.getElementById('llmContent');
    
    // 移除光标
    const cursor = llmContent.querySelector('.streaming-cursor');
    if (cursor) {
        cursor.remove();
    }
    
    // 最终渲染
    const html = llmBuffer.replace(/\n/g, '<br>');
    llmContent.innerHTML = html;
    llmContent.classList.remove('streaming');
}

// 显示LLM错误
function displayLLMError(message) {
    const llmContent = document.getElementById('llmContent');
    llmContent.innerHTML = `
        <div class="error-message">
            ⚠️ AI分析失败：${message}
        </div>
    `;
    llmContent.classList.remove('streaming');
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

