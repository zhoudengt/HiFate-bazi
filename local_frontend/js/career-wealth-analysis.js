/**
 * 事业财富分析 JavaScript
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
 * 开始分析事业财富
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
    const submitBtn = document.querySelector('.analyze-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ 分析中...';
    
    try {
        // 调用流式 API
        await streamCareerWealthAnalysis(solarDate, solarTime, gender);
    } catch (error) {
        console.error('分析失败:', error);
        showError(error.message || '分析失败，请稍后重试');
    } finally {
        // 恢复提交按钮
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 开始分析事业财富';
    }
}

/**
 * 更新用户信息显示
 */
function updateUserInfo(solarDate, solarTime, gender) {
    document.getElementById('displayDate').textContent = solarDate;
    document.getElementById('displayTime').textContent = solarTime;
    document.getElementById('displayGender').textContent = gender === 'male' ? '男' : '女';
    document.getElementById('userInfoCard').style.display = 'flex';
}

/**
 * 重置所有内容区域
 */
function resetContentAreas() {
    const contentIds = ['mingpanContent', 'careerContent', 'wealthContent', 'fortuneContent', 'tipsContent'];
    contentIds.forEach(id => {
        const elem = document.getElementById(id);
        elem.innerHTML = '<div class="loading">正在分析中...</div>';
        elem.classList.remove('streaming');
    });
}

/**
 * 显示错误信息
 */
function showError(message) {
    const contentIds = ['mingpanContent', 'careerContent', 'wealthContent', 'fortuneContent', 'tipsContent'];
    contentIds.forEach(id => {
        const elem = document.getElementById(id);
        if (elem.innerHTML.includes('正在分析中')) {
            elem.innerHTML = `<div class="error">❌ ${message}</div>`;
        }
    });
}

/**
 * 流式分析事业财富
 */
async function streamCareerWealthAnalysis(solarDate, solarTime, gender) {
    const apiBase = getApiBase();
    const url = `${apiBase}/api/v1/career-wealth/stream`;
    
    const requestBody = {
        solar_date: solarDate,
        solar_time: solarTime,
        gender: gender
    };
    
    console.log('请求事业财富分析:', url, requestBody);
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        },
        body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // 处理 SSE 格式
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.substring(6));
                    handleStreamData(data, fullContent);
                    
                    if (data.type === 'progress' && data.content) {
                        fullContent += data.content;
                    } else if (data.type === 'complete' && data.content) {
                        fullContent = data.content;
                    }
                } catch (e) {
                    console.error('解析 SSE 数据失败:', e, line);
                }
            }
        }
    }
    
    // 最终解析内容到各个区域
    parseAndDisplayContent(fullContent);
}

/**
 * 处理流式数据
 */
function handleStreamData(data, currentContent) {
    if (data.type === 'error') {
        showError(data.content || '分析失败');
        return;
    }
    
    if (data.type === 'progress' || data.type === 'complete') {
        const content = currentContent + (data.content || '');
        updateStreamingDisplay(content);
    }
}

/**
 * 更新流式显示
 */
function updateStreamingDisplay(content) {
    // 实时更新到第一个内容区域，显示流式效果
    const mingpanElem = document.getElementById('mingpanContent');
    mingpanElem.innerHTML = content + '<span class="streaming-cursor"></span>';
    mingpanElem.classList.add('streaming');
}

/**
 * 解析并显示内容到各个区域
 */
function parseAndDisplayContent(content) {
    if (!content) {
        showError('未收到分析内容');
        return;
    }
    
    // 分割5个部分
    const sections = parseContentSections(content);
    
    // 显示各部分内容
    displaySection('mingpanContent', sections.mingpan || '暂无命盘分析数据');
    displaySection('careerContent', sections.career || '暂无事业特质分析数据');
    displaySection('wealthContent', sections.wealth || '暂无财富轨迹分析数据');
    displaySection('fortuneContent', sections.fortune || '暂无大运流年分析数据');
    displaySection('tipsContent', sections.tips || '暂无提运建议数据');
}

/**
 * 解析内容中的各个部分
 */
function parseContentSections(content) {
    const sections = {
        mingpan: '',
        career: '',
        wealth: '',
        fortune: '',
        tips: ''
    };
    
    // 定义各部分的标题关键词
    const sectionPatterns = [
        { key: 'mingpan', patterns: ['命盘事业财富总论', '1.', '### 1.', '**1.'] },
        { key: 'career', patterns: ['事业特质与行业发展', '2.', '### 2.', '**2.'] },
        { key: 'wealth', patterns: ['财富轨迹与创富模式', '3.', '### 3.', '**3.'] },
        { key: 'fortune', patterns: ['关键大运与流年节点', '4.', '### 4.', '**4.'] },
        { key: 'tips', patterns: ['事业财富提运锦囊', '5.', '### 5.', '**5.'] }
    ];
    
    // 尝试按标题分割
    let currentSection = 'mingpan';
    const lines = content.split('\n');
    
    for (const line of lines) {
        // 检查是否匹配某个部分的标题
        let matched = false;
        for (const { key, patterns } of sectionPatterns) {
            for (const pattern of patterns) {
                if (line.includes(pattern) && line.indexOf(pattern) < 50) {
                    currentSection = key;
                    matched = true;
                    break;
                }
            }
            if (matched) break;
        }
        
        // 添加到当前部分
        sections[currentSection] += line + '\n';
    }
    
    // 清理每个部分的内容
    for (const key of Object.keys(sections)) {
        sections[key] = sections[key].trim();
    }
    
    // 如果无法分割，则将全部内容放到第一个部分
    if (!sections.career && !sections.wealth && !sections.fortune && !sections.tips) {
        sections.mingpan = content;
    }
    
    return sections;
}

/**
 * 显示单个区域的内容
 */
function displaySection(elementId, content) {
    const elem = document.getElementById(elementId);
    if (elem) {
        // 格式化 Markdown
        elem.innerHTML = formatMarkdown(content);
        elem.classList.remove('streaming');
    }
}

/**
 * 简单的 Markdown 格式化
 */
function formatMarkdown(text) {
    if (!text) return '';
    
    return text
        // 标题
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        // 粗体
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // 斜体
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // 列表
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.+<\/li>)+/g, '<ul>$&</ul>')
        // 分隔线
        .replace(/^---+$/gm, '<hr>')
        // 换行
        .replace(/\n/g, '<br>');
}

/**
 * 页面加载时初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    // 设置默认日期
    const today = new Date();
    const defaultDate = '1990-01-15';
    const defaultTime = '12:00';
    
    document.getElementById('solarDate').value = defaultDate;
    document.getElementById('solarTime').value = defaultTime;
    
    console.log('事业财富分析页面已加载');
});

