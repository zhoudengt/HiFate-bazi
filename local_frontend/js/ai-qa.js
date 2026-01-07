// AI问答页面逻辑
let currentUserId = null;
let currentCategory = null;
let currentBirthInfo = null;
let eventSource = null;
let isAnalysisComplete = false;  // 跟踪详细回答是否完成
let cachedRelatedQuestions = null;  // 缓存相关问题（如果详细回答未完成）

// 生成用户ID（简单实现，实际应该从登录系统获取）
function generateUserId() {
    return 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    currentUserId = generateUserId();
    console.log('用户ID:', currentUserId);

    // 生辰表单提交
    const birthForm = document.getElementById('birthForm');
    birthForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleBirthSubmit();
    });

    // 二级菜单点击
    const categoryItems = document.querySelectorAll('.category-item');
    categoryItems.forEach(item => {
        item.addEventListener('click', () => {
            const category = item.dataset.category;
            handleCategoryClick(category);
        });
    });

    // 输入框回车发送
    const questionInput = document.getElementById('questionInput');
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendQuestion();
        }
    });
});

// 处理生辰表单提交
function handleBirthSubmit() {
    const year = parseInt(document.getElementById('year').value);
    const month = parseInt(document.getElementById('month').value);
    const day = parseInt(document.getElementById('day').value);
    const hour = parseInt(document.getElementById('hour').value) || 12;
    const gender = document.getElementById('gender').value;

    // 保存生辰信息
    currentBirthInfo = { year, month, day, hour, gender };

    // 隐藏生辰表单，显示二级菜单
    document.getElementById('birthFormSection').classList.add('hidden');
    document.getElementById('categorySection').classList.add('active');
}

// 处理二级菜单点击（场景1）
function handleCategoryClick(category) {
    currentCategory = category;
    
    // 隐藏二级菜单，显示聊天窗口和输入框
    document.getElementById('categorySection').classList.remove('active');
    document.getElementById('chatSection').classList.add('active');
    document.getElementById('inputSection').classList.add('active');

    // 添加用户消息
    addMessage('user', `我想了解：${category}`);

    // 调用场景1API
    callScenario1API(category);
}

// 调用场景1API（点击选择项）
function callScenario1API(category) {
    // 关闭之前的连接
    if (eventSource) {
        eventSource.close();
    }

    const { year, month, day, hour, gender } = currentBirthInfo;
    
    // 构建API URL
    const apiUrl = `${API_CONFIG.baseURL}/smart-fortune/smart-analyze-stream?` +
        `category=${encodeURIComponent(category)}` +
        `&user_id=${encodeURIComponent(currentUserId)}` +
        `&year=${year}&month=${month}&day=${day}&hour=${hour}&gender=${gender}`;

    console.log('场景1 API URL:', apiUrl);

    // 显示加载状态
    addMessage('ai', '正在生成简短答复...', true);

    // 使用fetch处理SSE流
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.body.getReader();
        })
        .then(reader => {
            const decoder = new TextDecoder();
            let buffer = '';
            let briefResponseContent = '';
            let presetQuestions = [];

            function readStream() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        console.log('流式响应结束');
                        // 显示预设问题
                        if (presetQuestions.length > 0) {
                            displayPresetQuestions(presetQuestions);
                        }
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    // 解析SSE格式：event: <type>\ndata: <json>\n\n
                    let currentEvent = null;
                    let currentData = null;
                    
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            currentEvent = line.substring(7).trim();
                        } else if (line.startsWith('data: ')) {
                            currentData = line.substring(6).trim();
                            
                            // 当遇到data行时，处理事件
                            if (currentData) {
                                try {
                                    const eventData = JSON.parse(currentData);
                                    // 如果eventData中没有type，使用currentEvent
                                    if (!eventData.type && currentEvent) {
                                        eventData.type = currentEvent;
                                    }
                                    handleSSEEvent(eventData, briefResponseContent, presetQuestions);
                                    
                                    // 更新briefResponseContent
                                    if (eventData.type === 'brief_response_chunk') {
                                        briefResponseContent += eventData.content || '';
                                    }
                                } catch (e) {
                                    console.error('解析SSE事件失败:', e, 'line:', line, 'currentEvent:', currentEvent);
                                }
                            }
                            // 重置
                            currentEvent = null;
                            currentData = null;
                        } else if (line.trim() === '') {
                            // 空行表示事件结束，重置
                            currentEvent = null;
                            currentData = null;
                        }
                    }

                    readStream();
                }).catch(err => {
                    console.error('读取流失败:', err);
                    addMessage('ai', '❌ 读取响应失败: ' + err.message);
                });
            }

            readStream();
        })
        .catch(err => {
            console.error('API调用失败:', err);
            addMessage('ai', '❌ 请求失败: ' + err.message);
        });
}

// 处理SSE事件
function handleSSEEvent(eventData, briefResponseContent, presetQuestions) {
    const { type, content, questions, message } = eventData;

    switch (type) {
        case 'brief_response_start':
            // 移除加载消息，开始显示简短答复
            removeLastAIMessage();
            addMessage('ai', '', true); // 创建新的流式消息
            break;

        case 'brief_response_chunk':
            // 更新最后一条AI消息
            updateLastAIMessage(content);
            break;

        case 'brief_response_end':
            // 完成简短答复
            finishStreamingMessage();
            break;

        case 'preset_questions':
            // 保存预设问题
            if (Array.isArray(questions)) {
                presetQuestions.push(...questions);
            }
            break;

        case 'llm_start':
            // 开始LLM流式输出（场景2）
            // 移除"正在生成"消息（如果存在）
            removeLastAIMessage();
            addMessage('ai', '', true); // 创建新的流式消息
            break;

        case 'llm_chunk':
            // 更新LLM流式输出内容（场景2）
            updateLastAIMessage(content);
            break;

        case 'analysis_start':
            // 开始详细分析
            addMessage('ai', '', true);
            break;

        case 'analysis_chunk':
            // 更新详细分析
            updateLastAIMessage(content);
            break;

        case 'analysis_end':
        case 'llm_end':
            // 完成详细分析
            finishStreamingMessage();
            isAnalysisComplete = true;  // 标记详细回答已完成
            
            // 如果之前缓存了相关问题，现在显示
            if (cachedRelatedQuestions) {
                displayRelatedQuestions(cachedRelatedQuestions);
                cachedRelatedQuestions = null;
            }
            break;

        case 'related_questions':
            // 显示相关问题
            if (Array.isArray(questions)) {
                if (isAnalysisComplete) {
                    // 详细回答已完成，直接显示
                    displayRelatedQuestions(questions);
                } else {
                    // 详细回答未完成，先缓存
                    cachedRelatedQuestions = questions;
                    console.log('详细回答未完成，相关问题已缓存，等待详细回答完成后再显示');
                }
            }
            break;

        case 'error':
            // 显示错误
            removeLastAIMessage();
            addMessage('ai', '❌ ' + (message || content || '发生错误'));
            break;

        case 'end':
            // 流式响应结束
            console.log('流式响应结束');
            break;
    }
}

// 添加消息到聊天窗口
function addMessage(role, content, isStreaming = false) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}${isStreaming ? ' streaming' : ''}`;
    messageDiv.innerHTML = content + (isStreaming ? '<span class="streaming-cursor"></span>' : '');
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageDiv;
}

// 更新最后一条AI消息（流式）
function updateLastAIMessage(content) {
    const chatMessages = document.getElementById('chatMessages');
    const messages = chatMessages.querySelectorAll('.message.ai');
    if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        const currentContent = lastMessage.innerHTML.replace('<span class="streaming-cursor"></span>', '');
        lastMessage.innerHTML = currentContent + content + '<span class="streaming-cursor"></span>';
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 完成流式消息
function finishStreamingMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messages = chatMessages.querySelectorAll('.message.ai');
    if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        lastMessage.innerHTML = lastMessage.innerHTML.replace('<span class="streaming-cursor"></span>', '');
        lastMessage.classList.remove('streaming');
    }
}

// 移除最后一条AI消息
function removeLastAIMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messages = chatMessages.querySelectorAll('.message.ai');
    if (messages.length > 0) {
        messages[messages.length - 1].remove();
    }
}

// 显示预设问题
function displayPresetQuestions(questions) {
    const presetQuestionsList = document.getElementById('presetQuestionsList');
    presetQuestionsList.innerHTML = '';

    questions.forEach(question => {
        const item = document.createElement('div');
        item.className = 'preset-question-item';
        item.textContent = question;
        item.addEventListener('click', () => {
            handlePresetQuestionClick(question);
        });
        presetQuestionsList.appendChild(item);
    });

    document.getElementById('presetQuestionsSection').classList.add('active');
}

// 显示相关问题
function displayRelatedQuestions(questions) {
    // 确保隐藏预设问题区域（场景2不应该显示场景1的预设问题）
    document.getElementById('presetQuestionsSection').classList.remove('active');
    
    const relatedQuestionsList = document.getElementById('relatedQuestionsList');
    relatedQuestionsList.innerHTML = '';

    questions.forEach(question => {
        const item = document.createElement('div');
        item.className = 'related-question-item';
        item.textContent = question;
        item.addEventListener('click', () => {
            handlePresetQuestionClick(question);
        });
        relatedQuestionsList.appendChild(item);
    });

    document.getElementById('relatedQuestionsSection').classList.add('active');
}

// 处理预设问题点击（场景2）
function handlePresetQuestionClick(question) {
    // 添加用户消息
    addMessage('user', question);

    // 隐藏预设问题和相关问题
    document.getElementById('presetQuestionsSection').classList.remove('active');
    document.getElementById('relatedQuestionsSection').classList.remove('active');

    // 调用场景2API
    callScenario2API(question);
}

// 发送用户输入的问题（场景2）
function sendQuestion() {
    const questionInput = document.getElementById('questionInput');
    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    // 清空输入框
    questionInput.value = '';

    // 添加用户消息
    addMessage('user', question);

    // 隐藏预设问题和相关问题
    document.getElementById('presetQuestionsSection').classList.remove('active');
    document.getElementById('relatedQuestionsSection').classList.remove('active');

    // 调用场景2API
    callScenario2API(question);
}

// 调用场景2API（点击预设问题或输入问题）
function callScenario2API(question) {
    // 重置标志变量
    isAnalysisComplete = false;
    cachedRelatedQuestions = null;
    
    // 关闭之前的连接
    if (eventSource) {
        eventSource.close();
    }

    // 获取生辰参数（作为 fallback，以防 session 丢失）
    const { year, month, day, hour, gender } = currentBirthInfo;

    // 构建API URL（注意：API_CONFIG.baseURL已经包含/api/v1）
    // ⭐ 添加生辰参数作为 fallback，确保多轮对话时后端有完整信息
    const baseURL = API_CONFIG.baseURL.replace(/\/api\/v1$/, ''); // 移除末尾的/api/v1
    const apiUrl = `${baseURL}/api/v1/smart-fortune/smart-analyze-stream?` +
        `category=${encodeURIComponent(currentCategory)}` +
        `&user_id=${encodeURIComponent(currentUserId)}` +
        `&question=${encodeURIComponent(question)}` +
        `&year=${year}&month=${month}&day=${day}&hour=${hour}&gender=${gender}`;

    console.log('场景2 API URL:', apiUrl);

    // 显示加载状态
    addMessage('ai', '正在生成详细分析...', true);
    
    // 添加超时处理
    const timeout = 120000; // 120秒超时（场景2实际耗时约70-75秒）
    let timeoutId = setTimeout(() => {
        removeLastAIMessage();
        addMessage('ai', '❌ 请求超时（120秒），请稍后重试。如果问题持续，请联系客服。');
    }, timeout);
    
    // 添加进度监控
    let lastChunkTime = Date.now();
    let progressCheckInterval = setInterval(() => {
        const timeSinceLastChunk = Date.now() - lastChunkTime;
        if (timeSinceLastChunk > 30000) { // 30秒没有收到数据
            const lastMessage = document.querySelector('.chat-messages .message:last-child');
            if (lastMessage && lastMessage.textContent.includes('正在生成')) {
                updateLastAIMessage('正在生成详细分析...（响应较慢，请稍候）');
            }
        }
    }, 5000);
    
    let firstChunkReceived = false; // 标记是否收到第一个chunk

    // 使用fetch处理SSE流
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                clearTimeout(timeoutId);
                clearInterval(progressCheckInterval);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.body.getReader();
        })
        .then(reader => {
            const decoder = new TextDecoder();
            let buffer = '';
            let analysisContent = '';

            function readStream() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        clearTimeout(timeoutId);
                        clearInterval(progressCheckInterval);
                        console.log('流式响应结束');
                        return;
                    }

                    lastChunkTime = Date.now(); // 更新最后收到数据的时间
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    // 解析SSE格式：event: <type>\ndata: <json>\n\n
                    let currentEvent = null;
                    let currentData = null;
                    
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            currentEvent = line.substring(7).trim();
                        } else if (line.startsWith('data: ')) {
                            currentData = line.substring(6).trim();
                            
                            // 当遇到data行时，处理事件
                            if (currentData) {
                                try {
                                    const eventData = JSON.parse(currentData);
                                    // 如果eventData中没有type，使用currentEvent
                                    if (!eventData.type && currentEvent) {
                                        eventData.type = currentEvent;
                                    }
                                    
                                    // 如果收到第一个chunk，移除"正在生成"消息
                                    if (!firstChunkReceived && (eventData.type === 'llm_start' || eventData.type === 'analysis_start' || eventData.type === 'llm_chunk' || eventData.type === 'analysis_chunk')) {
                                        firstChunkReceived = true;
                                        removeLastAIMessage();
                                        addMessage('ai', '', true);
                                    }
                                    
                                    handleSSEEvent(eventData, analysisContent, []);

                                    // 更新analysisContent
                                    if (eventData.type === 'analysis_chunk' || eventData.type === 'llm_chunk') {
                                        analysisContent += eventData.content || '';
                                    }
                                } catch (e) {
                                    console.error('解析SSE事件失败:', e, 'line:', line, 'currentEvent:', currentEvent);
                                }
                            }
                            // 重置
                            currentEvent = null;
                            currentData = null;
                        } else if (line.trim() === '') {
                            // 空行表示事件结束，重置
                            currentEvent = null;
                            currentData = null;
                        }
                    }

                    readStream();
                }).catch(err => {
                    clearTimeout(timeoutId);
                    clearInterval(progressCheckInterval);
                    console.error('读取流失败:', err);
                    removeLastAIMessage();
                    addMessage('ai', '❌ 读取响应失败: ' + err.message);
                });
            }

            readStream();
        })
        .catch(err => {
            clearTimeout(timeoutId);
            clearInterval(progressCheckInterval);
            console.error('API调用失败:', err);
            removeLastAIMessage();
            addMessage('ai', '❌ 请求失败: ' + err.message);
        });
}

