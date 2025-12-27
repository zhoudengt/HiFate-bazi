/**
 * 身体健康分析 JavaScript
 * 处理前端页面逻辑和流式分析
 */

// 获取 API 基础路径
const getApiBase = () => {
    if (typeof API_BASE !== 'undefined') {
        return API_BASE;
    }
    // 默认使用当前域名
    return window.location.origin;
};

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('healthAnalysisForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            startAnalysis();
        });
    }
});

/**
 * 开始分析身体健康
 */
async function startAnalysis() {
    const solarDate = document.getElementById('solarDate').value;
    const solarTime = document.getElementById('solarTime').value;
    const gender = document.getElementById('gender').value;
    
    // 验证输入
    if (!solarDate || !solarTime || !gender) {
        alert('请填写完整的生辰信息！');
        return;
    }
    
    // 更新用户信息显示
    updateUserInfo(solarDate, solarTime, gender);
    
    // 显示结果区域
    const resultCard = document.getElementById('resultCard');
    resultCard.classList.add('active');
    resultCard.scrollIntoView({ behavior: 'smooth' });
    
    // 重置所有内容区域
    resetContentAreas();
    
    // 显示加载状态
    document.getElementById('loadingSection').style.display = 'block';
    document.getElementById('errorSection').style.display = 'none';
    
    // 禁用提交按钮
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = '分析中...';
    
    try {
        // 调用流式API
        await streamHealthAnalysis(solarDate, solarTime, gender);
    } catch (error) {
        console.error('分析失败:', error);
        showError('分析失败: ' + error.message);
    } finally {
        // 恢复提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '开始分析';
        document.getElementById('loadingSection').style.display = 'none';
    }
}

/**
 * 更新用户信息显示
 */
function updateUserInfo(solarDate, solarTime, gender) {
    const userInfoDiv = document.getElementById('userInfo');
    const genderText = gender === 'male' ? '男' : '女';
    userInfoDiv.innerHTML = `
        <h3>生辰信息</h3>
        <p><strong>公历日期：</strong>${solarDate}</p>
        <p><strong>出生时间：</strong>${solarTime}</p>
        <p><strong>性别：</strong>${genderText}</p>
    `;
}

/**
 * 重置所有内容区域
 */
function resetContentAreas() {
    // 隐藏所有section
    document.getElementById('mingpanSection').style.display = 'none';
    document.getElementById('wuxingSection').style.display = 'none';
    document.getElementById('dayunSection').style.display = 'none';
    document.getElementById('tiaoliSection').style.display = 'none';
    document.getElementById('fullAnalysisSection').style.display = 'none';
    
    // 清空内容
    document.getElementById('mingpanContent').textContent = '';
    document.getElementById('wuxingContent').textContent = '';
    document.getElementById('dayunContent').textContent = '';
    document.getElementById('tiaoliContent').textContent = '';
    document.getElementById('fullAnalysisContent').textContent = '';
}

/**
 * 显示错误信息
 */
function showError(message) {
    const errorSection = document.getElementById('errorSection');
    errorSection.textContent = message;
    errorSection.style.display = 'block';
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * 流式分析身体健康
 */
async function streamHealthAnalysis(solarDate, solarTime, gender) {
    const apiBase = getApiBase();
    const url = `${apiBase}/api/v1/health/stream`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    
    // 显示完整分析区域
    const fullAnalysisSection = document.getElementById('fullAnalysisSection');
    fullAnalysisSection.style.display = 'block';
    
    while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
            break;
        }
        
        // 解码数据
        buffer += decoder.decode(value, { stream: true });
        
        // 处理完整的行
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.substring(6));
                    
                    if (data.type === 'progress') {
                        // 增量内容
                        fullContent += data.content;
                        updateDisplay(fullContent);
                    } else if (data.type === 'complete') {
                        // 完成
                        fullContent += data.content;
                        updateDisplay(fullContent);
                        console.log('健康分析完成');
                        return;
                    } else if (data.type === 'error') {
                        // 错误（不中断流，显示错误信息）
                        console.error('收到错误消息:', data.content);
                        showError(data.content || '生成失败');
                        return; // 结束流处理，但不抛出异常
                    }
                } catch (e) {
                    console.error('解析SSE数据失败:', e, line);
                }
            }
        }
    }
}

/**
 * 更新显示内容
 */
function updateDisplay(content) {
    // 更新完整分析内容
    const fullAnalysisContent = document.getElementById('fullAnalysisContent');
    fullAnalysisContent.textContent = content;
    
    // 自动滚动到底部
    fullAnalysisContent.scrollTop = fullAnalysisContent.scrollHeight;
}

