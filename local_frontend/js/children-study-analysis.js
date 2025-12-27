/**
 * 子女学习分析 JavaScript
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
 * 开始分析子女学习
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
    document.getElementById('resultCard').classList.add('active');
    
    // 重置所有内容区域
    resetContentAreas();
    
    // 禁用提交按钮
    const submitBtn = document.querySelector('.submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = '分析中...';
    
    try {
        // 调用流式API
        await streamChildrenStudyAnalysis(solarDate, solarTime, gender);
    } catch (error) {
        console.error('分析失败:', error);
        showError('分析失败: ' + error.message);
    } finally {
        // 恢复提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '开始分析';
    }
}

/**
 * 更新用户信息显示
 */
function updateUserInfo(solarDate, solarTime, gender) {
    document.getElementById('displayDate').textContent = solarDate;
    document.getElementById('displayTime').textContent = solarTime;
    document.getElementById('displayGender').textContent = gender === 'male' ? '男' : '女';
}

/**
 * 重置所有内容区域
 */
function resetContentAreas() {
    // 重置所有section的内容
    for (let i = 1; i <= 4; i++) {
        const content = document.getElementById(`section${i}Content`);
        if (i === 1) {
            content.innerHTML = '<div class="loading"><div class="spinner"></div><p>正在分析命盘格局...</p></div>';
        } else {
            content.innerHTML = '<div class="loading">等待前序分析完成...</div>';
        }
    }
}

/**
 * 显示错误信息
 */
function showError(message) {
    const section1 = document.getElementById('section1Content');
    section1.innerHTML = `<div class="error">${message}</div>`;
}

/**
 * 流式分析子女学习
 */
async function streamChildrenStudyAnalysis(solarDate, solarTime, gender) {
    const apiBase = getApiBase();
    const url = `${apiBase}/api/v1/children-study/stream`;
    
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
    let currentSection = 1;
    
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
                        console.log('分析完成');
                        return;
                    } else if (data.type === 'error') {
                        // 错误
                        console.error('收到错误消息:', data.content);
                        showError(data.content || '生成失败');
                        return; // 不抛出异常，让前端继续处理
                    }
                } catch (e) {
                    console.error('解析SSE数据失败:', e, line);
                }
            }
        }
    }
    
    // 最后更新一次
    if (fullContent) {
        updateDisplay(fullContent);
    } else {
        showError('未收到分析内容');
    }
}

/**
 * 更新显示内容
 * 根据分节标题自动分配到不同区域
 */
function updateDisplay(content) {
    // 定义分节标题映射
    const sectionHeaders = {
        '一、命盘子女总论': 1,
        '二、子女星与子女宫': 2,
        '三、生育时机': 3,
        '四、养育建议': 4
    };
    
    // 分割内容
    let sections = { 1: '', 2: '', 3: '', 4: '' };
    let currentSection = 1;
    let lines = content.split('\n');
    
    for (const line of lines) {
        // 检查是否是分节标题
        let foundHeader = false;
        for (const [header, sectionNum] of Object.entries(sectionHeaders)) {
            if (line.trim().startsWith(header)) {
                currentSection = sectionNum;
                foundHeader = true;
                break;
            }
        }
        
        // 如果不是标题，添加到当前section
        if (!foundHeader && line.trim()) {
            sections[currentSection] += line + '\n';
        }
    }
    
    // 更新各个section的显示
    for (let i = 1; i <= 4; i++) {
        const contentElement = document.getElementById(`section${i}Content`);
        const sectionContent = sections[i].trim();
        
        if (sectionContent) {
            // 将文本转换为HTML段落
            const paragraphs = sectionContent.split('\n\n')
                .filter(p => p.trim())
                .map(p => `<p>${p.trim().replace(/\n/g, '<br>')}</p>`)
                .join('');
            contentElement.innerHTML = paragraphs || '<p>暂无内容</p>';
        } else if (i === 1 && content.length > 10) {
            // 第一节有内容但还没分节，显示全部
            const paragraphs = content.split('\n\n')
                .filter(p => p.trim())
                .map(p => `<p>${p.trim().replace(/\n/g, '<br>')}</p>`)
                .join('');
            contentElement.innerHTML = paragraphs;
        }
    }
}

/**
 * 页面加载完成后的初始化
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('子女学习分析页面已加载');
    
    // 设置默认日期为今天
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    document.getElementById('solarDate').value = dateStr;
    
    // 设置默认时间为中午12:00
    document.getElementById('solarTime').value = '12:00';
});

