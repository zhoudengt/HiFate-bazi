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
    const solarDate = document.getElementById('solarDate').value.trim();
    const solarTime = document.getElementById('solarTime').value.trim();
    const gender = document.getElementById('gender').value;
    
    // 验证三个参数都必须填写
    if (!solarDate || !solarTime || !gender) {
        alert('请填写完整的生辰信息：出生日期、出生时间和性别都必须填写');
        return;
    }
    
    // 验证日期格式
    if (!/^\d{4}-\d{2}-\d{2}$/.test(solarDate)) {
        alert('出生日期格式错误，请使用 YYYY-MM-DD 格式');
        return;
    }
    
    // 验证时间格式
    if (!/^\d{2}:\d{2}$/.test(solarTime)) {
        alert('出生时间格式错误，请使用 HH:MM 格式');
        return;
    }
    
    // 验证性别
    if (gender !== 'male' && gender !== 'female') {
        alert('性别选择错误，请选择男或女');
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
                            
                            // 前端也过滤错误消息（双重保障）
                            if (isErrorResponse(content)) {
                                console.warn('前端检测到错误消息，已过滤:', content.substring(0, 50));
                                // 不显示错误消息，继续等待有效内容
                                continue;
                            }
                            
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
                            
                            // 前端也过滤错误消息（双重保障）
                            if (isErrorResponse(content)) {
                                console.warn('前端检测到完整错误响应，已过滤:', content.substring(0, 100));
                                showError('Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。');
                                return;
                            }
                            
                            fullContent += content;
                            
                            // 在complete时，总是解析完整内容并分配到各个部分
                            // 清除之前的部分内容和DOM元素，重新分发
                            Object.keys(sections).forEach(key => {
                                sectionContent[key] = '';
                            });
                            
                            // 清除所有section的DOM内容（重要：避免显示旧内容）
                            Object.values(sections).forEach(sectionId => {
                                const sectionEl = document.getElementById(sectionId);
                                if (sectionEl) {
                                    sectionEl.innerHTML = '';
                                    sectionEl.classList.remove('streaming');
                                }
                            });
                            
                            parseAndDistributeContent(fullContent, sectionContent, sections);
                            
                            return; // 完成
                        } else if (data.type === 'error') {
                            console.error('收到错误消息:', data.content);
                            // 显示具体错误信息（已优化，会自动区分错误类型）
                            showError(data.content || '生成失败');
                            return; // 结束流处理，但不抛出异常
                        }
                    } catch (e) {
                        console.warn('解析SSE数据失败:', e, line);
                    }
                }
            }
        }
        
        // 如果流结束但没有complete消息，显示已收集的内容
        if (fullContent) {
            // 检查完整内容是否包含错误消息
            if (isErrorResponse(fullContent)) {
                console.warn('前端检测到完整内容包含错误消息，已过滤');
                showError('Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。');
            } else {
                parseAndDistributeContent(fullContent, sectionContent, sections);
            }
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
    console.log('🔄 parseAndDistributeContent 被调用，内容长度:', fullContent.length);
    
    // 再次检查完整内容是否包含错误消息（最终保障）
    if (isErrorResponse(fullContent)) {
        console.warn('解析前检测到完整内容包含错误消息');
        showError('Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。');
        return;
    }
    
    // 如果内容被重复，只取第一部分（去除重复内容）
    // 检测重复：如果内容包含两次"命盘总论"标题，说明内容重复了
    // 支持多种格式：### 1. 命盘总论 或 ### 命盘总论
    const duplicatePatterns = [
        /###\s*1\.\s*命盘总论/i,
        /###\s*命盘总论/i
    ];
    
    let firstMingpanIndex = -1;
    for (const pattern of duplicatePatterns) {
        const match = fullContent.match(pattern);
        if (match) {
            firstMingpanIndex = match.index;
            break;
        }
    }
    
    if (firstMingpanIndex >= 0) {
        // 从第一个标题之后100字符开始查找第二个匹配
        const searchStart = firstMingpanIndex + 100;
        let secondMingpanIndex = -1;
        for (const pattern of duplicatePatterns) {
            const searchContent = fullContent.substring(searchStart);
            const match = searchContent.match(pattern);
            if (match) {
                secondMingpanIndex = searchStart + match.index;
                break;
            }
        }
        
        if (secondMingpanIndex > 0) {
            // 只保留第一部分内容
            fullContent = fullContent.substring(0, secondMingpanIndex).trim();
            console.log('检测到内容重复，已去除重复部分');
        }
    }
    
    // 使用更简单直接的方法：根据标题分割内容
    // 先找到各个标题的位置（支持多种格式）
    const titlePatterns = [
        { key: 'mingpan', title: '命盘总论', patterns: [/###\s*1\.\s*命盘总论/i, /###\s*命盘总论/i, /命盘总论/i] },
        { key: 'peiou', title: '配偶特征', patterns: [/###\s*2\.\s*配偶特征/i, /###\s*配偶特征/i, /配偶特征/i] },
        { key: 'ganqing', title: '感情走势', patterns: [/###\s*3\.\s*感情走势/i, /###\s*感情走势/i, /感情走势/i] },
        { key: 'shensha', title: '神煞点睛', patterns: [/###\s*4\.\s*神煞点睛/i, /###\s*神煞点睛/i, /神煞点睛/i] },
        { key: 'jianyi', title: '建议方向', patterns: [/###\s*5\.\s*建议方向/i, /###\s*建议方向/i, /建议方向/i] }
    ];
    
    // 找到所有标题的位置（按顺序匹配，使用第一个匹配到的）
    const titlePositions = [];
    titlePatterns.forEach(({ key, title, patterns }) => {
        for (const pattern of patterns) {
            const match = fullContent.match(pattern);
            if (match) {
                // 检查是否已经添加了这个标题（避免重复）
                const existing = titlePositions.find(p => p.key === key);
                if (!existing) {
                    titlePositions.push({
                        key: key,
                        index: match.index,
                        title: title
                    });
                    break; // 找到第一个匹配就停止
                }
            }
        }
    });
    
    // 按位置排序
    titlePositions.sort((a, b) => a.index - b.index);
    
    console.log('📍 找到的标题位置:', titlePositions.map(p => ({ key: p.key, index: p.index, title: p.title })));
    
    // 如果没有找到任何标题，使用fallback
    if (titlePositions.length === 0) {
        console.warn('⚠️ 未找到任何标题，使用fallback');
        if (!isErrorResponse(fullContent)) {
            const sectionEl = document.getElementById(sections.mingpan);
            if (sectionEl) {
                sectionEl.innerHTML = fullContent;
                sectionEl.classList.remove('streaming');
            }
        }
        return;
    }
    
    // 根据标题位置分割内容
    let hasMatch = false;
    for (let i = 0; i < titlePositions.length; i++) {
        const currentPos = titlePositions[i];
        const nextPos = i < titlePositions.length - 1 ? titlePositions[i + 1] : null;
        
        // 提取当前部分的内容（从当前标题开始，到下一个标题之前）
        // 需要找到下一个标题的实际开始位置（包括 ### 和编号），然后往前一点，避免包含下一个标题
        const startIndex = currentPos.index;
        let endIndex = nextPos ? nextPos.index : fullContent.length;
        
        // 如果下一个标题存在，需要往回查找，确保不包含下一个标题的 ### X. 部分
        if (nextPos) {
            // 从nextPos.index往前查找，找到 ### 的位置
            const beforeNext = fullContent.substring(Math.max(0, nextPos.index - 20), nextPos.index);
            const hashMatch = beforeNext.match(/###\s*\d+\.\s*/);
            if (hashMatch) {
                // 找到 ### X. 的开始位置
                endIndex = nextPos.index - (beforeNext.length - hashMatch.index);
            }
        }
        
        let sectionContent_text = fullContent.substring(startIndex, endIndex).trim();
        
        // 清理内容：移除标题前的 ### 和编号（如果存在）
        // 支持多种格式：### 1. 标题 或 ### 标题 或 1. 标题 或 标题
        sectionContent_text = sectionContent_text.replace(/^###\s*\d+\.\s*/, '').trim();
        sectionContent_text = sectionContent_text.replace(/^###\s*/, '').trim();
        sectionContent_text = sectionContent_text.replace(/^\d+\.\s*/, '').trim();
        
        // 移除标题文本本身（如果内容以标题开头）
        const titleRegex = new RegExp(`^${currentPos.title}\\s*`, 'i');
        sectionContent_text = sectionContent_text.replace(titleRegex, '').trim();
        
        // 移除末尾可能残留的下一个标题标记（如 ### 3.）
        sectionContent_text = sectionContent_text.replace(/\s*###\s*\d+\.\s*$/, '').trim();
        
        // 检查内容是否有效
        if (sectionContent_text.length > 10 && !isErrorResponse(sectionContent_text)) {
            sectionContent[currentPos.key] = sectionContent_text;
            const sectionEl = document.getElementById(sections[currentPos.key]);
            if (sectionEl) {
                console.log(`✅ 设置 ${currentPos.key} 内容，长度: ${sectionContent_text.length}`);
                sectionEl.innerHTML = sectionContent[currentPos.key];
                sectionEl.classList.remove('streaming');
                hasMatch = true;
            } else {
                console.warn(`⚠️ 未找到section元素: ${sections[currentPos.key]}`);
            }
        } else {
            console.warn(`⚠️ ${currentPos.key} 内容无效，长度: ${sectionContent_text.length}`);
        }
    }
    
    // 如果解析失败，将所有内容显示在第一个部分
    if (!hasMatch) {
        if (!isErrorResponse(fullContent)) {
            const sectionEl = document.getElementById(sections.mingpan);
            if (sectionEl) {
                sectionEl.innerHTML = fullContent;
                sectionEl.classList.remove('streaming');
            }
        } else {
            showError('Coze Bot 无法处理当前请求。可能原因：1) Bot 配置问题，2) 输入数据格式不符合 Bot 期望，3) Bot Prompt 需要调整。请检查 Bot ID 和 Bot 配置。');
        }
    }
}

// 检测是否为错误响应
function isErrorResponse(text) {
    if (!text || text.trim().length < 5) {
        return false;
    }
    
    // 错误消息的关键词（与后端保持一致）
    const errorKeywords = [
        '对不起，我无法回答这个问题',
        '对不起,我无法回答这个问题',
        '对不起我无法回答这个问题',
        '无法回答这个问题',
        '我无法回答这个问题',
        '抱歉，我无法',
        '抱歉,我无法',
        '我无法处理',
        '无法处理',
    ];
    
    const normalizedText = text.trim();
    for (const keyword of errorKeywords) {
        if (normalizedText.includes(keyword)) {
            return true;
        }
    }
    
    return false;
}

// 显示错误
function showError(message) {
    // 分析错误类型，提供更友好的提示
    let friendlyMessage = message;
    let errorType = 'unknown';
    
    if (message.includes('数据计算不完整') || message.includes('数据完整性验证失败')) {
        errorType = 'data';
        friendlyMessage = '数据计算失败：生辰数据可能不正确，请检查输入的日期和时间。';
    } else if (message.includes('Coze API 返回空内容') || 
               message.includes('Coze Bot') || 
               message.includes('Bot配置') ||
               message.includes('Bot ID')) {
        errorType = 'bot';
        friendlyMessage = 'Coze Bot 配置问题：\n' +
            '1. 请检查 Coze Bot ID 是否正确配置\n' +
            '2. 请检查 Coze Bot 中的 prompt 是否已正确配置\n' +
            '3. 请确认 Coze API Token 是否有效\n\n' +
            '技术提示：可通过 /api/v1/bazi/marriage-analysis/debug 端点验证数据是否正确。';
    } else if (message.includes('未收到分析内容')) {
        errorType = 'empty';
        friendlyMessage = '未收到分析内容：\n' +
            '1. 可能是 Coze Bot 返回了空内容（请检查 Bot 配置）\n' +
            '2. 可能是网络问题导致数据丢失\n' +
            '3. 请尝试重新生成或检查后端日志';
    }
    
    const sections = ['mingpanContent', 'peiouContent', 'ganqingContent', 'shenshaContent', 'jianyiContent'];
    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            // 使用换行符和样式美化错误提示
            const formattedMessage = friendlyMessage.replace(/\n/g, '<br>');
            el.innerHTML = `<div class="error" data-error-type="${errorType}">
                <strong>错误：</strong><br>
                ${formattedMessage}
                ${errorType === 'bot' ? '<br><br><small>提示：后端数据计算正常，问题在于 Coze Bot 配置或 prompt 设置。</small>' : ''}
                ${errorType === 'data' ? '<br><br><small>提示：请检查生辰日期和时间是否正确。</small>' : ''}
            </div>`;
            el.classList.remove('streaming');
        }
    });
    
    console.error(`[错误类型: ${errorType}]`, message);
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

