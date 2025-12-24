// 八字命理-感情婚姻分析JS

let currentAnalysis = null;
let fullContent = '';
let sectionContent = {};  // 移到全局，确保每次重置时清空

// 显示用户信息
function displayUserInfo(userInfo) {
    const userInfoCard = document.getElementById('userInfoCard');
    if (userInfoCard && userInfo) {
        document.getElementById('displayDate').textContent = userInfo.solar_date || '';
        document.getElementById('displayTime').textContent = userInfo.solar_time || '';
        document.getElementById('displayGender').textContent = userInfo.gender === 'male' ? '男' : '女';
        userInfoCard.style.display = 'flex';
    }
}

// 开始分析
async function startAnalysis() {
    const solarDate = document.getElementById('solarDate').value;
    const solarTime = document.getElementById('solarTime').value;
    const gender = document.getElementById('gender').value;
    
    if (!solarDate || !solarTime) {
        alert('请填写完整的生辰信息');
        return;
    }
    
    // 显示用户信息
    displayUserInfo({
        solar_date: solarDate,
        solar_time: solarTime,
        gender: gender
    });
    
    // 禁用按钮
    const btn = document.querySelector('.analyze-btn');
    btn.disabled = true;
    btn.textContent = '⏳ 分析中...';
    
    // 显示结果卡片
    const resultCard = document.getElementById('resultCard');
    resultCard.classList.add('active');
    
    // 重置内容（清除所有状态）
    fullContent = '';
    sectionContent = {};  // 清空section内容
    currentAnalysis = null;  // 清除之前的请求
    resetAllSections();
    
    // 开始流式分析
    await generateMarriageAnalysis(solarDate, solarTime, gender);
    
    // 恢复按钮
    btn.disabled = false;
    btn.textContent = '🚀 开始分析';
}

// 重置所有部分
function resetAllSections() {
    const sections = ['mingpanContent', 'peiouContent', 'ganqingContent', 'shenshaContent', 'jianyiContent'];
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<div class="loading">正在生成...</div>';
            el.classList.remove('streaming');
        }
    });
}

// 流式生成感情婚姻分析
async function generateMarriageAnalysis(solarDate, solarTime, gender) {
    // 取消之前的请求（如果有）
    if (currentAnalysis && currentAnalysis.abort) {
        currentAnalysis.abort();
    }
    
    try {
        // 构建API URL
        const apiBaseUrl = API_CONFIG.baseURL.replace('/api/v1', '');
        const controller = new AbortController();
        currentAnalysis = { abort: () => controller.abort() };
        
        const response = await fetch(`${apiBaseUrl}/api/v1/bazi/marriage-analysis/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                solar_date: solarDate,
                solar_time: solarTime,
                gender: gender
            }),
            signal: controller.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        // 处理SSE流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentSection = null;
        
        // 初始化sectionContent（如果未初始化）
        if (!sectionContent || Object.keys(sectionContent).length === 0) {
            sectionContent = {};
        }
        
        // 初始化所有部分
        const sections = {
            'mingpan': 'mingpanContent',
            'peiou': 'peiouContent',
            'ganqing': 'ganqingContent',
            'shensha': 'shenshaContent',
            'jianyi': 'jianyiContent'
        };
        
        Object.keys(sections).forEach(key => {
            sectionContent[key] = '';
        });
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后一个不完整的行
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        
                        if (data.type === 'progress') {
                            const content = data.content || '';
                            fullContent += content;
                            
                            // 根据完整内容判断当前部分（使用完整内容，而不是单个chunk）
                            if (!currentSection || fullContent.length < 50) {
                                // 检测部分标题（在完整内容中查找）
                                if (fullContent.includes('命盘总论') || fullContent.includes('1.') || fullContent.includes('一、')) {
                                    currentSection = 'mingpan';
                                } else if (fullContent.includes('配偶特征') || fullContent.includes('2.') || fullContent.includes('二、')) {
                                    currentSection = 'peiou';
                                } else if (fullContent.includes('感情走势') || fullContent.includes('3.') || fullContent.includes('三、')) {
                                    currentSection = 'ganqing';
                                } else if (fullContent.includes('神煞点睛') || fullContent.includes('4.') || fullContent.includes('四、')) {
                                    currentSection = 'shensha';
                                } else if (fullContent.includes('建议方向') || fullContent.includes('5.') || fullContent.includes('五、')) {
                                    currentSection = 'jianyi';
                                } else {
                                    // 如果没有检测到标题，默认使用第一个部分
                                    currentSection = currentSection || 'mingpan';
                                }
                            }
                            
                            // 更新当前部分内容
                            if (currentSection && sections[currentSection]) {
                                sectionContent[currentSection] += content;
                                const sectionEl = document.getElementById(sections[currentSection]);
                                if (sectionEl) {
                                    sectionEl.innerHTML = sectionContent[currentSection];
                                    sectionEl.classList.add('streaming');
                                }
                            }
                            
                        } else if (data.type === 'complete') {
                            const content = data.content || '';
                            fullContent += content;
                            
                            // 更新当前部分
                            if (currentSection && sections[currentSection]) {
                                sectionContent[currentSection] += content;
                                const sectionEl = document.getElementById(sections[currentSection]);
                                if (sectionEl) {
                                    sectionEl.innerHTML = sectionContent[currentSection];
                                    sectionEl.classList.remove('streaming');
                                }
                            }
                            
                            // 如果没有明确的部分，尝试解析完整内容并分配到各个部分
                            if (!currentSection || fullContent.length < 100) {
                                parseAndDistributeContent(fullContent, sectionContent, sections);
                            }
                            
                            return; // 完成
                        } else if (data.type === 'error') {
                            throw new Error(data.content || '生成失败');
                        }
                    } catch (e) {
                        console.warn('解析SSE数据失败:', e, line);
                    }
                }
            }
        }
        
        // 如果流结束但没有complete消息，显示已收集的内容
        if (fullContent) {
            parseAndDistributeContent(fullContent, sectionContent, sections);
        } else {
            showError('未收到分析内容');
        }
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('请求已取消');
            return;
        }
        console.error('生成分析失败:', error);
        showError(`生成分析失败: ${error.message}`);
    } finally {
        currentAnalysis = null;
    }
}

// 解析并分配内容到各个部分
function parseAndDistributeContent(fullContent, sectionContent, sections) {
    // 简单的解析规则：根据标题分割内容
    const patterns = [
        { key: 'mingpan', regex: /(命盘总论|1\.\s*命盘总论)[\s\S]*?(?=(配偶特征|2\.|感情走势|3\.|神煞点睛|4\.|建议方向|5\.|$))/i },
        { key: 'peiou', regex: /(配偶特征|2\.\s*配偶特征)[\s\S]*?(?=(感情走势|3\.|神煞点睛|4\.|建议方向|5\.|$))/i },
        { key: 'ganqing', regex: /(感情走势|3\.\s*感情走势)[\s\S]*?(?=(神煞点睛|4\.|建议方向|5\.|$))/i },
        { key: 'shensha', regex: /(神煞点睛|4\.\s*神煞点睛)[\s\S]*?(?=(建议方向|5\.|$))/i },
        { key: 'jianyi', regex: /(建议方向|5\.\s*建议方向)[\s\S]*$/i }
    ];
    
    patterns.forEach(pattern => {
        const match = fullContent.match(pattern.regex);
        if (match) {
            sectionContent[pattern.key] = match[0];
            const sectionEl = document.getElementById(sections[pattern.key]);
            if (sectionEl) {
                sectionEl.innerHTML = sectionContent[pattern.key];
                sectionEl.classList.remove('streaming');
            }
        }
    });
    
    // 如果解析失败，将所有内容显示在第一个部分
    if (!sectionContent.mingpan && !sectionContent.peiou && !sectionContent.ganqing) {
        const sectionEl = document.getElementById(sections.mingpan);
        if (sectionEl) {
            sectionEl.innerHTML = fullContent;
            sectionEl.classList.remove('streaming');
        }
    }
}

// 显示错误
function showError(message) {
    const sections = ['mingpanContent', 'peiouContent', 'ganqingContent', 'shenshaContent', 'jianyiContent'];
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = `<div class="error">${message}</div>`;
            el.classList.remove('streaming');
        }
    });
}

// 页面加载时设置默认日期（今天）
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    const dateInput = document.getElementById('solarDate');
    if (dateInput) {
        dateInput.value = dateStr;
    }
});

