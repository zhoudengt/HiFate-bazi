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
        // 硬编码生产接口地址
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

// 流式生成大模型分析
async function generateLLMAnalysis(userInfo) {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 硬编码生产接口地址
    const PRODUCTION_API = 'http://8.210.52.217:8001';
    let fullContent = '';
    let hasReceivedContent = false;
    
    try {
        llmContent.innerHTML = '<div class="loading">🔄 正在连接AI服务...</div>';
        console.log('📡 开始连接生产接口:', `${PRODUCTION_API}/api/v1/bazi/xishen-jishen/stream`);
        
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
        
        console.log('📡 收到响应:', response.status, response.headers.get('content-type'));
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        llmContent.innerHTML = '<div class="loading">⏳ 等待AI分析中（大模型生成需要约1-2分钟）...</div>';
        
        // 处理SSE流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let lastUpdateTime = Date.now();
        
        // 处理单行SSE数据
        const processLine = async (line) => {
            if (!line.startsWith('data: ')) return;
            
            try {
                const data = JSON.parse(line.substring(6));
                console.log('📨 收到数据:', data.type, data.content ? `(${data.content.length}字符)` : '');
                
                if (data.type === 'progress') {
                    const newContent = data.content || '';
                    if (newContent) {
                        hasReceivedContent = true;
                        // 逐个字符显示
                        for (let i = 0; i < newContent.length; i++) {
                            fullContent += newContent[i];
                            llmContent.textContent = fullContent;
                            // 每5个字符等待一次，平衡效果和性能
                            if (i % 5 === 0) {
                                await new Promise(resolve => setTimeout(resolve, 10));
                            }
                        }
                        lastUpdateTime = Date.now();
                    }
                } else if (data.type === 'complete') {
                    if (data.content) {
                        fullContent += data.content;
                        llmContent.textContent = fullContent;
                    }
                    console.log('✅ 流式传输完成');
                } else if (data.type === 'data') {
                    // 收到基础数据，显示等待状态
                    console.log('📊 收到基础数据，等待AI分析...');
                    if (!hasReceivedContent) {
                        llmContent.innerHTML = '<div class="loading">⏳ 正在生成AI分析（大模型生成需要约1-2分钟）...</div>';
                    }
                } else if (data.type === 'error') {
                    throw new Error(data.content || '生成失败');
                }
            } catch (e) {
                console.warn('解析SSE数据失败:', e, line);
            }
        };
        
        // 循环读取流
        while (true) {
            let result;
            try {
                result = await reader.read();
            } catch (readError) {
                console.warn('读取流出错:', readError);
                // 如果已有内容，不显示错误
                if (fullContent) {
                    break;
                }
                throw readError;
            }
            
            const { done, value } = result;
            
            if (done) {
                console.log('📭 流结束');
                break;
            }
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                await processLine(line);
            }
        }
        
        // 处理缓冲区中剩余的数据
        if (buffer.trim()) {
            await processLine(buffer);
        }
        
        // 流结束，确保显示内容
        if (fullContent) {
            llmContent.textContent = fullContent;
            console.log('✅ 最终内容长度:', fullContent.length);
        } else {
            llmContent.innerHTML = '<div class="error">⚠️ 未收到AI分析内容，请稍后重试</div>';
        }
        
    } catch (error) {
        console.error('生成分析失败:', error);
        llmContent.innerHTML = `<div class="error">生成分析失败: ${error.message}</div>`;
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

