// QA 多轮对话 JavaScript - 八字命理-AI问答

let currentSessionId = null;
let currentCategory = null;
let userInfo = null;
let allPresetQuestions = {}; // 存储所有分类的预设问题
let currentStreamingAnswer = null; // 当前正在流式输出的答案

// 开始对话
async function startConversation() {
    const solarDate = document.getElementById('solarDate').value;
    const solarTime = document.getElementById('solarTime').value;
    const gender = document.getElementById('gender').value;
    
    if (!solarDate || !solarTime || !gender) {
        alert('请填写完整的生辰信息');
        return;
    }
    
    userInfo = { solarDate, solarTime, gender };
    
    try {
        const response = await fetch(`${API_CONFIG.baseURL}/qa/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                solar_date: solarDate,
                solar_time: solarTime,
                gender: gender
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            
            // 隐藏输入卡片，显示对话区域
            document.getElementById('userInputCard').style.display = 'none';
            document.getElementById('conversationArea').style.display = 'block';
            
            // 显示初始问题
            document.getElementById('initialQuestionText').textContent = data.initial_question;
            document.getElementById('initialQuestionCard').style.display = 'block';
            
            // 显示分类按钮
            displayCategories(data.categories);
            
            // 加载所有分类的预设问题
            await loadAllPresetQuestions(data.categories);
        } else {
            alert('开始对话失败：' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('开始对话失败:', error);
        alert('开始对话失败：' + error.message);
    }
}

// 显示分类按钮
function displayCategories(categories) {
    const container = document.getElementById('categoryButtons');
    container.innerHTML = '';
    
    categories.forEach(category => {
        const button = document.createElement('button');
        button.className = 'category-btn';
        button.textContent = category.name;
        button.onclick = () => selectCategory(category.key);
        container.appendChild(button);
    });
}

// 选择分类
async function selectCategory(category) {
    currentCategory = category;
    
    // 隐藏初始问题卡片
    document.getElementById('initialQuestionCard').style.display = 'none';
    
    // 加载并显示该分类的预设问题
    await loadCategoryPresetQuestions(category);
}

// 加载所有分类的预设问题
async function loadAllPresetQuestions(categories) {
    for (const category of categories) {
        await loadCategoryPresetQuestions(category.key, false);
    }
}

// 加载分类的预设问题
async function loadCategoryPresetQuestions(category, showInPanel = true) {
    try {
        const response = await fetch(`${API_CONFIG.baseURL}/qa/categories/${category}/questions`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success && data.questions) {
            // 存储到全局对象
            allPresetQuestions[category] = data.questions;
            
            // 如果指定显示在面板中，更新预设问题列表
            if (showInPanel) {
                displayPresetQuestions(category, data.questions);
            }
        }
    } catch (error) {
        console.error(`加载分类 ${category} 的预设问题失败:`, error);
    }
}

// 显示预设问题列表
function displayPresetQuestions(category, questions) {
    const container = document.getElementById('presetQuestionsList');
    container.innerHTML = '';
    
    // 添加分类标题
    const categoryTitle = document.createElement('div');
    categoryTitle.className = 'preset-category-title';
    categoryTitle.textContent = getCategoryName(category);
    categoryTitle.style.cssText = 'font-weight: 600; color: #667eea; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #e5e5e5;';
    container.appendChild(categoryTitle);
    
    // 添加问题项
    questions.forEach((question, index) => {
        const questionItem = document.createElement('div');
        questionItem.className = 'preset-question-item';
        questionItem.textContent = question.text || question;
        questionItem.onclick = () => {
            // 移除其他项的active状态
            container.querySelectorAll('.preset-question-item').forEach(item => {
                item.classList.remove('active');
            });
            // 添加当前项的active状态
            questionItem.classList.add('active');
            // 提问
            askQuestion(question.text || question);
        };
        container.appendChild(questionItem);
    });
}

// 验证会话是否存在
async function validateSession(sessionId) {
    if (!sessionId) {
        return { valid: false, exists: false, error: 'session_id 为空' };
    }
    
    try {
        const response = await fetch(`${API_CONFIG.baseURL}/qa/validate-session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('验证会话失败:', error);
        return { valid: false, exists: false, error: '验证会话时发生错误: ' + error.message };
    }
}

// 自动重新创建会话
async function recreateSession() {
    if (!userInfo) {
        console.error('无法重新创建会话：用户信息不存在');
        return false;
    }
    
    try {
        console.log('🔄 正在重新创建会话...');
        const response = await fetch(`${API_CONFIG.baseURL}/qa/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                solar_date: userInfo.solarDate,
                solar_time: userInfo.solarTime,
                gender: userInfo.gender
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            console.log('✅ 会话重新创建成功:', currentSessionId);
            addMessageToHistory('assistant', '会话已重新创建，您可以继续提问。');
            return true;
        } else {
            console.error('❌ 会话重新创建失败:', data.error);
            return false;
        }
    } catch (error) {
        console.error('❌ 重新创建会话异常:', error);
        return false;
    }
}

// 提问（支持预设问题选择和直接输入）
async function askQuestion(questionText = null) {
    if (!currentSessionId) {
        alert('请先开始对话');
        return;
    }
    
    const question = questionText || document.getElementById('questionInput').value.trim();
    if (!question) {
        alert('请输入问题');
        return;
    }
    
    // 清空输入框
    if (!questionText) {
        document.getElementById('questionInput').value = '';
    }
    
    // 禁用发送按钮
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span>生成中...</span>';
    
    // 添加用户问题到对话历史
    addMessageToHistory('user', question);
    
    // 创建答案消息容器（用于流式输出）
    const answerMessageId = 'answer-' + Date.now();
    const answerMessage = document.createElement('div');
    answerMessage.id = answerMessageId;
    answerMessage.className = 'message assistant';
    answerMessage.innerHTML = `
        <div class="message-role">AI</div>
        <div class="message-content streaming" id="${answerMessageId}-content">正在生成答案...</div>
    `;
    document.getElementById('conversationHistory').appendChild(answerMessage);
    
    // 滚动到底部
    scrollToBottom();
    
    currentStreamingAnswer = '';
    
    try {
        // 1. 先验证会话是否存在
        const validationResult = await validateSession(currentSessionId);
        if (!validationResult.valid || !validationResult.exists) {
            console.warn('⚠️ 会话验证失败:', validationResult.error);
            
            // 尝试自动重新创建会话
            const recreated = await recreateSession();
            if (!recreated) {
                showError(answerMessageId, '会话不存在或已过期，且无法自动恢复。请重新开始对话。');
                return;
            }
            
            // 会话重新创建成功，继续提问
            console.log('✅ 会话已恢复，继续提问...');
        }
        
        // 2. 调用流式API
        const response = await fetch(`${API_CONFIG.baseURL}/qa/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                question: question
            })
        });
        
        if (!response.ok) {
            // 如果是 500 错误，可能是会话问题，尝试重新创建
            if (response.status === 500) {
                console.warn('⚠️ 服务器错误，尝试重新创建会话...');
                const recreated = await recreateSession();
                if (recreated) {
                    // 重新发送请求
                    const retryResponse = await fetch(`${API_CONFIG.baseURL}/qa/ask`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: currentSessionId,
                            question: question
                        })
                    });
                    
                    if (!retryResponse.ok) {
                        throw new Error(`HTTP error! status: ${retryResponse.status}`);
                    }
                    
                    // 使用重试的响应继续处理
                    return await processStreamResponse(retryResponse, answerMessageId);
                }
            }
            
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // 3. 处理 SSE 流
        await processStreamResponse(response, answerMessageId);
        
    } catch (error) {
        console.error('提问失败:', error);
        
        // 检查是否是会话相关错误
        if (error.message.includes('会话不存在') || error.message.includes('已过期')) {
            // 尝试自动恢复
            const recreated = await recreateSession();
            if (recreated) {
                showError(answerMessageId, '会话已恢复，请重新提问。');
            } else {
                showError(answerMessageId, '会话不存在或已过期，且无法自动恢复。请重新开始对话。');
            }
        } else {
            showError(answerMessageId, '提问失败：' + error.message);
        }
    } finally {
        // 恢复发送按钮
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<span>发送</span>';
    }
}

// 处理流式响应（提取为独立函数以便重用）
async function processStreamResponse(response, answerMessageId) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullAnswer = '';
    let generatedQuestions = [];
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.substring(6));
                    
                    if (data.type === 'progress') {
                        fullAnswer += data.content || '';
                        currentStreamingAnswer = fullAnswer;
                        updateStreamingAnswer(answerMessageId, fullAnswer);
                    } else if (data.type === 'complete') {
                        fullAnswer += data.content || '';
                        currentStreamingAnswer = fullAnswer;
                        updateStreamingAnswer(answerMessageId, fullAnswer, false);
                    } else if (data.type === 'questions_before') {
                        // 用户提问后，大模型生成的问题提示（在答案生成前）
                        generatedQuestions = data.content || data.questions || [];
                        if (generatedQuestions.length > 0) {
                            displayGeneratedQuestions(generatedQuestions);
                        }
                    } else if (data.type === 'questions_after' || data.type === 'generated_questions') {
                        // 答案生成后，大模型生成的问题提示
                        generatedQuestions = data.content || data.questions || [];
                        if (generatedQuestions.length > 0) {
                            displayGeneratedQuestions(generatedQuestions);
                        }
                    } else if (data.type === 'error') {
                        // 检查是否是会话相关错误
                        const errorContent = data.content || '生成失败';
                        if (errorContent.includes('会话不存在') || errorContent.includes('已过期')) {
                            showError(answerMessageId, errorContent + '。正在尝试自动恢复...');
                            const recreated = await recreateSession();
                            if (recreated) {
                                showError(answerMessageId, '会话已恢复，请重新提问。');
                            } else {
                                showError(answerMessageId, errorContent + '，且无法自动恢复。请重新开始对话。');
                            }
                        } else {
                            showError(answerMessageId, errorContent);
                        }
                        return;
                    }
                } catch (e) {
                    console.error('解析 SSE 数据失败:', e, line);
                }
            }
        }
    }
    
    // 流式输出完成
    if (fullAnswer) {
        currentStreamingAnswer = fullAnswer;
    }
}

// 更新流式答案显示
function updateStreamingAnswer(messageId, content, isStreaming = true) {
    const contentElement = document.getElementById(messageId + '-content');
    if (contentElement) {
        contentElement.textContent = content;
        if (isStreaming) {
            contentElement.classList.add('streaming');
            // 添加光标
            if (!contentElement.querySelector('.streaming-cursor')) {
                const cursor = document.createElement('span');
                cursor.className = 'streaming-cursor';
                contentElement.appendChild(cursor);
            }
        } else {
            contentElement.classList.remove('streaming');
            // 移除光标
            const cursor = contentElement.querySelector('.streaming-cursor');
            if (cursor) {
                cursor.remove();
            }
        }
        scrollToBottom();
    }
}

// 显示生成的问题（在对话历史下方）
function displayGeneratedQuestions(questions) {
    if (!questions || questions.length === 0) {
        return;
    }
    
    // 移除之前的问题
    const oldQuestions = document.getElementById('generatedQuestionsContainer');
    if (oldQuestions) {
        oldQuestions.remove();
    }
    
    // 创建新的问题容器
    const container = document.createElement('div');
    container.id = 'generatedQuestionsContainer';
    container.className = 'generated-questions-container';
    container.style.cssText = 'margin-top: 15px; padding: 15px; background: #fff3cd; border-radius: 8px;';
    
    const title = document.createElement('h4');
    title.textContent = '继续提问：';
    title.style.cssText = 'margin: 0 0 10px 0; font-size: 14px; color: #856404;';
    container.appendChild(title);
    
    const buttonsContainer = document.createElement('div');
    buttonsContainer.className = 'question-buttons';
    buttonsContainer.style.cssText = 'display: flex; flex-direction: column; gap: 8px;';
    
    questions.forEach(question => {
        const button = document.createElement('button');
        button.className = 'question-btn-small';
        button.textContent = question;
        button.style.cssText = 'padding: 8px 16px; background: #ffc107; color: #333; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; text-align: left; transition: all 0.2s;';
        button.onmouseover = function() { this.style.background = '#e0a800'; };
        button.onmouseout = function() { this.style.background = '#ffc107'; };
        button.onclick = () => askQuestion(question);
        buttonsContainer.appendChild(button);
    });
    
    container.appendChild(buttonsContainer);
    document.getElementById('conversationHistory').appendChild(container);
    scrollToBottom();
}

// 添加消息到对话历史
function addMessageToHistory(role, content) {
    const history = document.getElementById('conversationHistory');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const roleLabel = role === 'user' ? '您' : 'AI';
    messageDiv.innerHTML = `
        <div class="message-role">${roleLabel}</div>
        <div class="message-content">${escapeHtml(content).replace(/\n/g, '<br>')}</div>
    `;
    
    history.appendChild(messageDiv);
    scrollToBottom();
}

// 显示错误
function showError(messageId, message) {
    const contentElement = document.getElementById(messageId + '-content');
    if (contentElement) {
        contentElement.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
        contentElement.classList.remove('streaming');
    }
}

// 滚动到底部
function scrollToBottom() {
    const history = document.getElementById('conversationHistory');
    if (history) {
        history.scrollTop = history.scrollHeight;
    }
}

// 处理输入框回车
function handleQuestionKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
    }
}

// 清空对话
function clearConversation() {
    if (confirm('确定要清空当前对话吗？')) {
        document.getElementById('conversationHistory').innerHTML = '';
        currentStreamingAnswer = null;
    }
}

// 获取分类名称
function getCategoryName(category) {
    const names = {
        'career_wealth': '事业财富',
        'marriage': '婚姻',
        'health': '健康',
        'children': '子女',
        'liunian': '流年运势',
        'yearly_report': '年运报告',
        'initial': '初始问题'
    };
    return names[category] || category;
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
