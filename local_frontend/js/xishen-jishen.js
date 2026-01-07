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
        // 访问生产 FastAPI 接口（已部署心跳包代码）
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

// 流式生成大模型分析 - 使用 Fetch API + ReadableStream
async function generateLLMAnalysis(userInfo) {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 访问生产 FastAPI 接口（已部署心跳包 + 2KB填充数据）
    const PRODUCTION_API = 'http://8.210.52.217:8001';
    let fullContent = '';
    let hasReceivedContent = false;
    
    try {
        llmContent.innerHTML = '<div class="loading">🔄 正在连接AI服务...</div>';
        console.log('📡 开始连接生产接口:', `${PRODUCTION_API}/api/v1/bazi/xishen-jishen/stream`);
        
        // 使用 Fetch API + ReadableStream 处理流式响应
        const response = await fetch(`${PRODUCTION_API}/api/v1/bazi/xishen-jishen/stream`, {
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
        
        console.log('📡 连接成功，开始读取流...');
        
        // 获取 ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        // 处理单行 SSE 数据
        const processLine = (line) => {
            if (!line.startsWith('data: ')) return;
            
            try {
                const data = JSON.parse(line.substring(6));
                // 只记录类型，不记录大量填充数据
                const logContent = data._padding ? '(含填充数据)' : 
                    (data.content ? `(${typeof data.content === 'string' ? data.content.length : 'object'}字符)` : '');
                console.log('📨 收到数据:', data.type, logContent);
                
                if (data.type === 'progress') {
                    const newContent = data.content || '';
                    if (newContent) {
                        hasReceivedContent = true;
                        fullContent += newContent;
                        llmContent.textContent = fullContent;
                        if (llmContent.scrollHeight > llmContent.clientHeight) {
                            llmContent.scrollTop = llmContent.scrollHeight;
                        }
                    }
                } else if (data.type === 'complete') {
                    if (data.content) {
                        fullContent += data.content;
                        llmContent.textContent = fullContent;
                    }
                    console.log('✅ 流式传输完成');
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
                if (line.trim() && !line.includes('_padding')) {
                    console.warn('解析SSE数据失败:', e.message);
                }
            }
        };
        
        // 循环读取流数据
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                console.log('📭 流读取完成');
                break;
            }
            
            // 解码并处理数据
            const chunk = decoder.decode(value, { stream: true });
            console.log('📦 收到数据块:', chunk.length, '字节');
            buffer += chunk;
            
            // 按行分割处理
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后不完整的行
            
            for (const line of lines) {
                processLine(line);
            }
        }
        
        // 处理最后的缓冲区
        if (buffer.trim()) {
            processLine(buffer);
        }
        
        // 确保显示内容
        if (fullContent) {
            llmContent.textContent = fullContent;
            console.log('✅ 最终内容长度:', fullContent.length);
        } else if (!hasReceivedContent) {
            llmContent.innerHTML = '<div class="error">⚠️ 未收到AI分析内容，请稍后重试</div>';
        }
        
    } catch (error) {
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

