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

// 流式生成大模型分析 - 直接照搬 wuxing-proportion.js 的简单实现
let llmBuffer = '';
async function generateLLMAnalysis(userInfo) {
    const llmContent = document.getElementById('llmContent');
    if (!llmContent) return;
    
    // 同域访问，使用相对路径
    const url = '/api/v1/bazi/xishen-jishen/stream';
    llmBuffer = '';
    llmContent.innerHTML = '';
    llmContent.classList.add('streaming');
    
    try {
        // 发送POST请求获取流式响应
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
        
        // 读取流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                break;
            }
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后一个不完整的行
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6);
                    if (dataStr.trim() === '[DONE]') {
                        finishLLMAnalysis();
                        return;
                    }
                    
                    try {
                        const data = JSON.parse(dataStr);
                        handleStreamData(data);
                    } catch (e) {
                        console.warn('解析SSE数据失败:', e, dataStr);
                    }
                }
            }
        }
        
        finishLLMAnalysis();
    } catch (error) {
        console.error('流式分析失败:', error);
        displayLLMError('流式分析失败: ' + (error.message || '未知错误'));
    }
}

// 处理流式数据
function handleStreamData(data) {
    const type = data.type;
    
    if (type === 'start') {
        displayLLMStart();
    } else if (type === 'progress') {
        if (data.content) {
            appendLLMChunk(data.content);
        }
    } else if (type === 'complete') {
        if (data.content) {
            appendLLMChunk(data.content);
        }
        finishLLMAnalysis();
    } else if (type === 'error') {
        displayLLMError(data.error || '分析失败');
    }
}

// 显示LLM分析开始
function displayLLMStart() {
    const llmContent = document.getElementById('llmContent');
    llmBuffer = '';
    llmContent.innerHTML = '';
    llmContent.classList.add('streaming');
}

// 追加LLM内容块
function appendLLMChunk(text) {
    const llmContent = document.getElementById('llmContent');
    llmBuffer += text;
    
    // 简单处理：将换行转换为<br>
    const html = llmBuffer.replace(/\n/g, '<br>');
    llmContent.innerHTML = html + '<span class="streaming-cursor"></span>';
    
    // 自动滚动到底部
    llmContent.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// 完成LLM分析
function finishLLMAnalysis() {
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

