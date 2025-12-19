// 五行占比分析页面逻辑

// 从基础八字排盘获取生辰信息（如果存在）
function loadBaziInfo() {
    try {
        const baziInfo = localStorage.getItem('bazi_info');
        if (baziInfo) {
            const info = JSON.parse(baziInfo);
            if (info.solar_date) {
                document.getElementById('solar_date').value = info.solar_date;
            }
            if (info.solar_time) {
                document.getElementById('solar_time').value = info.solar_time;
            }
            if (info.gender) {
                document.getElementById('gender').value = info.gender;
            }
        }
    } catch (e) {
        console.warn('无法从localStorage加载八字信息:', e);
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    loadBaziInfo();
    
    const form = document.getElementById('wuxingForm');
    const userInfoDisplay = document.getElementById('userInfoDisplay');
    const editBtn = document.getElementById('editBtn');
    
    // 检查是否有已保存的用户信息
    const savedDate = localStorage.getItem('bazi_solar_date');
    const savedTime = localStorage.getItem('bazi_solar_time');
    const savedGender = localStorage.getItem('bazi_gender');
    
    if (savedDate && savedTime && savedGender) {
        // 显示用户信息卡片
        document.getElementById('display_date').textContent = savedDate;
        document.getElementById('display_time').textContent = savedTime;
        document.getElementById('display_gender').textContent = savedGender === 'male' ? '男' : '女';
        userInfoDisplay.style.display = 'block';
        form.style.display = 'none';
    } else {
        // 显示表单
        userInfoDisplay.style.display = 'none';
        form.style.display = 'block';
    }
    
    // 编辑按钮
    editBtn.addEventListener('click', function() {
        userInfoDisplay.style.display = 'none';
        form.style.display = 'block';
    });
    
    // 表单提交
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const solarDate = document.getElementById('solar_date').value;
        const solarTime = document.getElementById('solar_time').value;
        const gender = document.getElementById('gender').value;
        
        // 保存到localStorage
        localStorage.setItem('bazi_solar_date', solarDate);
        localStorage.setItem('bazi_solar_time', solarTime);
        localStorage.setItem('bazi_gender', gender);
        
        // 更新显示
        document.getElementById('display_date').textContent = solarDate;
        document.getElementById('display_time').textContent = solarTime;
        document.getElementById('display_gender').textContent = gender === 'male' ? '男' : '女';
        userInfoDisplay.style.display = 'block';
        form.style.display = 'none';
        
        // 开始分析
        await analyzeWuxingProportion(solarDate, solarTime, gender);
    });
});

// 分析五行占比
async function analyzeWuxingProportion(solarDate, solarTime, gender) {
    try {
        // 隐藏错误区域
        const errorSection = document.getElementById('errorSection');
        errorSection.style.display = 'none';
        
        // 显示状态
        const statusText = document.getElementById('statusText');
        statusText.style.display = 'block';
        statusText.textContent = '正在计算五行占比...';
        
        // 1. 获取五行占比数据
        const response = await api.post('/bazi/wuxing-proportion', {
            solar_date: solarDate,
            solar_time: solarTime,
            gender: gender
        });
        
        if (!response.success || !response.data) {
            displayError('获取五行占比数据失败: ' + (response.error || '未知错误'));
            return;
        }
        
        const proportionData = response.data;
        
        // 2. 显示五行占比表格
        displayProportionTable(proportionData);
        
        // 3. 开始流式分析
        statusText.textContent = '正在调用AI分析...';
        await streamLLMAnalysis(solarDate, solarTime, gender);
        
        statusText.style.display = 'none';
    } catch (error) {
        console.error('分析失败:', error);
        displayError('分析失败: ' + (error.message || '未知错误'));
    }
}

// 显示五行占比表格
function displayProportionTable(data) {
    const proportionSection = document.getElementById('proportionSection');
    const tableBody = document.getElementById('wuxingTableBody');
    
    // 显示区域
    proportionSection.style.display = 'block';
    proportionSection.classList.add('active');
    
    // 清空表格
    tableBody.innerHTML = '';
    
    const proportions = data.proportions || {};
    const elements = ['金', '木', '水', '火', '土'];
    
    elements.forEach(element => {
        const elementData = proportions[element] || { count: 0, percentage: 0, details: [] };
        const count = elementData.count || 0;
        const percentage = elementData.percentage || 0;
        const details = elementData.details || [];
        const detailsStr = details.length > 0 ? details.join('、') : '无';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="element-name">${element}</td>
            <td class="element-count">${count}/8</td>
            <td class="element-percentage">${percentage}%</td>
            <td class="element-details">${detailsStr}</td>
        `;
        tableBody.appendChild(row);
    });
    
    // 滚动到表格
    proportionSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 流式分析
let llmBuffer = '';
let eventSource = null;

async function streamLLMAnalysis(solarDate, solarTime, gender) {
    // 显示分析区域
    const llmSection = document.getElementById('llmAnalysisSection');
    const llmContent = document.getElementById('llmAnalysisContent');
    
    llmSection.style.display = 'block';
    llmSection.classList.add('active');
    llmContent.innerHTML = '';
    llmContent.classList.add('streaming');
    llmBuffer = '';
    
    // 滚动到分析区域
    llmSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    try {
        // 构建流式请求URL
        const baseUrl = window.API_BASE_URL || '';
        const url = `${baseUrl}/api/v1/bazi/wuxing-proportion/stream`;
        
        // 发送POST请求获取流式响应
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: JSON.stringify({
                solar_date: solarDate,
                solar_time: solarTime,
                gender: gender
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
    const statusText = document.getElementById('statusText');
    
    if (type === 'start') {
        statusText.style.display = 'block';
        statusText.textContent = data.statusText || '开始分析...';
        displayLLMStart();
    } else if (type === 'progress') {
        if (data.statusText) {
            statusText.textContent = data.statusText;
        }
        if (data.content) {
            appendLLMChunk(data.content);
        }
    } else if (type === 'complete') {
        if (data.content) {
            appendLLMChunk(data.content);
        }
        finishLLMAnalysis();
        statusText.style.display = 'none';
    } else if (type === 'error') {
        displayLLMError(data.error || '分析失败');
        statusText.style.display = 'none';
    }
}

// 显示LLM分析开始
function displayLLMStart() {
    const llmContent = document.getElementById('llmAnalysisContent');
    llmBuffer = '';
    llmContent.innerHTML = '';
    llmContent.classList.add('streaming');
}

// 追加LLM内容块
function appendLLMChunk(text) {
    const llmContent = document.getElementById('llmAnalysisContent');
    llmBuffer += text;
    
    // 简单处理：将换行转换为<br>
    const html = llmBuffer.replace(/\n/g, '<br>');
    llmContent.innerHTML = html + '<span class="streaming-cursor"></span>';
    
    // 自动滚动到底部
    llmContent.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// 完成LLM分析
function finishLLMAnalysis() {
    const llmContent = document.getElementById('llmAnalysisContent');
    
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
    const llmSection = document.getElementById('llmAnalysisSection');
    const llmContent = document.getElementById('llmAnalysisContent');
    
    // 显示区域
    llmSection.style.display = 'block';
    llmSection.classList.add('active');
    
    llmContent.innerHTML = `
        <div class="error-message">
            ⚠️ AI分析失败：${message}
        </div>
    `;
    llmContent.classList.remove('streaming');
    
    // 滚动到错误区域
    llmSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 显示错误
function displayError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    
    // 显示区域
    errorSection.style.display = 'block';
    errorSection.classList.add('active');
    
    errorMessage.textContent = message;
    
    // 滚动到错误区域
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

