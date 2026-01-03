// 排盘逻辑
let hasResult = false;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    const userInfo = UserInfo.load();
    if (userInfo) {
        // 有保存的信息，显示信息卡片，隐藏表单
        showUserInfo(userInfo);
        // 延迟自动查询（性能优化：避免阻塞页面渲染）
        // 使用 requestIdleCallback 或 setTimeout 延迟执行
        if (window.requestIdleCallback) {
            requestIdleCallback(function() {
                queryPan(userInfo.solar_date, userInfo.solar_time, userInfo.gender);
            }, { timeout: 2000 }); // 最多等待2秒
        } else {
            // 降级方案：延迟500ms执行，让页面先渲染
            setTimeout(function() {
                queryPan(userInfo.solar_date, userInfo.solar_time, userInfo.gender);
            }, 500);
        }
    } else {
        // 没有保存的信息，显示表单
        showForm();
    }
    
    // 修改按钮事件
    document.getElementById('editBtn').addEventListener('click', () => {
        showForm();
    });
    
    // 表单提交事件
    document.getElementById('panForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const solar_date = document.getElementById('solar_date').value;
        const solar_time = document.getElementById('solar_time').value;
        const gender = document.getElementById('gender').value;
        
        // 保存用户信息
        UserInfo.save(solar_date, solar_time, gender);
        
        // 显示信息卡片
        showUserInfo({solar_date, solar_time, gender});
        
        // 查询（用户主动操作，立即执行）
        queryPan(solar_date, solar_time, gender);
    });
});

function showUserInfo(info) {
    document.getElementById('userInfoDisplay').style.display = 'block';
    document.getElementById('panForm').style.display = 'none';
    document.getElementById('display_date').textContent = info.solar_date;
    document.getElementById('display_time').textContent = info.solar_time;
    const genderText = info.gender === 'male' ? '男' : '女';
    document.getElementById('display_gender').textContent = genderText;
    
    // 更新头部用户信息
    const userNameEl = document.getElementById('userName');
    const userGenderEl = document.getElementById('userGender');
    if (userNameEl) userNameEl.textContent = '用户';
    if (userGenderEl) userGenderEl.textContent = genderText;
}

function showForm() {
    document.getElementById('userInfoDisplay').style.display = 'none';
    document.getElementById('panForm').style.display = 'block';
    UserInfo.fillForm();
}

async function queryPan(solar_date, solar_time, gender) {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<div class="loading">查询中...</div>';

    try {
        // 调用前端展示接口
        const response = await api.post('/bazi/pan/display', {
            solar_date,
            solar_time,
            gender
        });

        // 🔍 调试：检查婚姻规则数据
        if (response.success && response.pan.marriage_rules) {
            console.log('📊 婚姻规则数量:', response.pan.marriage_rules.length);
            console.log('📊 第1条规则名:', response.pan.marriage_rules[0]?.rule_name);
            console.log('📊 第1条规则名(字节):', 
                Array.from(response.pan.marriage_rules[0]?.rule_name || '').map(c => c.charCodeAt(0).toString(16)).join(' '));
        }

        if (response.success) {
            displayPanResult(response.pan, solar_date, solar_time, gender);
            hasResult = true;
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
    }
}

function displayPanResult(pan, solar_date, solar_time, gender) {
    const resultDiv = document.getElementById('result');
    let html = '';

    // 八字排盘表格（按照截图样式：表格形式，四列）
    html += '<div class="card">';
    html += '<div class="card-header">';
    html += '<h2 class="card-title">基础八字排盘</h2>';
    html += '</div>';
    
    html += '<table class="bazi-table">';
    
    // 表头行
    html += '<thead><tr>';
    html += '<th></th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            html += `<th>${pillar.label}</th>`;
        });
    }
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // ✅ 1. 主星行
    html += '<tr>';
    html += '<th>主星</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const mainStar = pillar.main_star || pillar.stem?.ten_god || '';
            html += `<td>${mainStar || '-'}</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 2. 天干行
    html += '<tr>';
    html += '<th>天干</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const stemWuxing = pillar.stem.wuxing || '';
            const stemChar = pillar.stem.char || '';
            html += `<td>`;
            html += `<div class="stem-circle ${getWuxingClass(stemWuxing)}">${stemChar}</div>`;
            html += `</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 3. 地支行
    html += '<tr>';
    html += '<th>地支</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const branchWuxing = pillar.branch.wuxing || '';
            const branchChar = pillar.branch.char || '';
            html += `<td>`;
            html += `<div class="branch-circle ${getWuxingClass(branchWuxing)}">${branchChar}</div>`;
            html += `</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 4. 藏干行（支持换行显示，每个藏干单独一行，居中显示）
    html += '<tr>';
    html += '<th>藏干</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const hiddenStems = pillar.branch?.hidden_stems || [];
            html += `<td>`;
            html += `<div class="hidden-stem" style="display: flex; flex-direction: column; gap: 4px; align-items: center; justify-content: center;">`;
            if (hiddenStems.length > 0) {
                hiddenStems.forEach((h, idx) => {
                    // ✅ 修复：显示完整的藏干字符串（如"己土"、"丁火"）
                    const stemChar = (typeof h === 'string') ? h : (h.char || h);
                    html += `<div class="hidden-stem-item" style="white-space: nowrap; text-align: center;">`;
                    html += `<span>${stemChar}</span>`;
                    html += `</div>`;
                });
            } else {
                html += `<div class="hidden-stem-item" style="text-align: center;">-</div>`;
            }
            html += `</div>`;
            html += `</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 4.5. 副星行（支持换行显示，每个副星单独一行，居中显示）
    html += '<tr>';
    html += '<th>副星</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const hiddenStems = pillar.branch?.hidden_stems || [];
            const hiddenStars = pillar.hidden_stars || [];
            html += `<td>`;
            html += `<div class="hidden-stem" style="display: flex; flex-direction: column; gap: 4px; align-items: center; justify-content: center;">`;
            if (hiddenStars.length > 0) {
                // ✅ 使用 hidden_stars 数组
                hiddenStars.forEach((star, idx) => {
                    html += `<div class="hidden-stem-item" style="white-space: nowrap; text-align: center;">`;
                    html += `<span>${star}</span>`;
                    html += `</div>`;
                });
            } else if (hiddenStems.length > 0) {
                // ✅ 降级方案：从藏干的 ten_god 获取副星
                hiddenStems.forEach((h, idx) => {
                    const tenGod = (typeof h === 'object' && h.ten_god) ? h.ten_god : '';
                    if (tenGod) {
                        html += `<div class="hidden-stem-item" style="white-space: nowrap; text-align: center;">`;
                        html += `<span>${tenGod}</span>`;
                        html += `</div>`;
                    }
                });
                // 如果所有藏干都没有 ten_god，显示 "-"
                if (!hiddenStems.some(h => (typeof h === 'object' && h.ten_god))) {
                    html += `<div class="hidden-stem-item" style="text-align: center;">-</div>`;
                }
            } else {
                html += `<div class="hidden-stem-item" style="text-align: center;">-</div>`;
            }
            html += `</div>`;
            html += `</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 5. 星运行
    html += '<tr>';
    html += '<th>星运</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const starFortune = pillar.star_fortune || '-';
            html += `<td>${starFortune}</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 6. 自坐行
    html += '<tr>';
    html += '<th>自坐</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const selfSitting = pillar.self_sitting || '-';
            html += `<td>${selfSitting}</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 7. 空亡行
    html += '<tr>';
    html += '<th>空亡</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const kongwang = pillar.kongwang || '-';
            html += `<td>${kongwang}</td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 8. 纳音行
    html += '<tr>';
    html += '<th>纳音</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            html += `<td><div class="nayin-text">${pillar.nayin || '-'}</div></td>`;
        });
    }
    html += '</tr>';
    
    // ✅ 9. 神煞行（支持换行显示）
    html += '<tr>';
    html += '<th>神煞</th>';
    if (pan.pillars && pan.pillars.length > 0) {
        pan.pillars.forEach(pillar => {
            const deities = pillar.deities || [];
            html += `<td>`;
            html += `<div class="deities-list" style="display: flex; flex-direction: column; gap: 4px;">`;
            if (deities.length > 0) {
                deities.forEach((deity, idx) => {
                    html += `<div class="deity-item">${deity}</div>`;
                });
            } else {
                html += `<div class="deity-item">-</div>`;
            }
            html += `</div>`;
            html += `</td>`;
        });
    }
    html += '</tr>';
    
    html += '</tbody>';
    html += '</table>';
    html += '</div>';

    // ✅ 日柱解析卡片（可展开）
    const rizhuAnalysis = pan.rizhu_analysis;
    const hasRizhuData = rizhuAnalysis && rizhuAnalysis.descriptions && rizhuAnalysis.descriptions.length > 0;
    html += '<div class="expandable-card expandable-card-rizhu" id="rizhuCard">';
    html += '<div class="expandable-card-header" onclick="toggleExpandableCard(\'rizhuCard\')">';
    html += '<div class="expandable-card-icon">💬</div>';
    html += '<div class="expandable-card-title">日柱';
    if (hasRizhuData) {
        html += `<span class="expandable-card-count">(${rizhuAnalysis.descriptions.length}条)</span>`;
    }
    html += '</div>';
    html += '<div class="expandable-card-arrow" id="rizhuCardArrow">▼</div>';
    html += '</div>';
    html += '<div class="expandable-card-content" id="rizhuCardContent" style="display: none;">';
    if (hasRizhuData) {
        html += '<div class="rizhu-analysis-content">';
        html += '<div class="analysis-title">【性格与命运解析】</div>';
        rizhuAnalysis.descriptions.forEach((desc, idx) => {
            html += `<div class="analysis-item">`;
            html += `<span class="analysis-number">${idx + 1}.</span>`;
            html += `<span class="analysis-text">${desc}</span>`;
            html += `</div>`;
        });
        html += '</div>';
    } else {
        html += '<div class="no-data">暂无日柱解析数据</div>';
    }
    html += '</div>';
    html += '</div>';

    // ✅ 婚姻规则卡片（可展开）
    const marriageRules = pan.marriage_rules || [];
    const hasMarriageData = marriageRules.length > 0;
    html += '<div class="expandable-card expandable-card-marriage" id="marriageCard">';
    html += '<div class="expandable-card-header" onclick="toggleExpandableCard(\'marriageCard\')">';
    html += '<div class="expandable-card-icon">💬</div>';
    html += '<div class="expandable-card-title">婚姻';
    if (hasMarriageData) {
        html += `<span class="expandable-card-count">(命中${marriageRules.length}条规则)</span>`;
    }
    html += '</div>';
    html += '<div class="expandable-card-arrow" id="marriageCardArrow">▼</div>';
    html += '</div>';
    html += '<div class="expandable-card-content" id="marriageCardContent" style="display: none;">';
    if (hasMarriageData) {
        html += '<div class="marriage-rules-content">';
        marriageRules.forEach((rule, idx) => {
            const ruleName = rule.rule_name || rule.rule_id || `规则${idx + 1}`;
            const content = rule.content || {};
            let ruleText = '';
            
            // 处理规则内容（可能是文本、对象或数组）
            if (typeof content === 'string') {
                ruleText = content;
            } else if (content.text) {
                ruleText = content.text;
            } else if (content.items && Array.isArray(content.items)) {
                ruleText = content.items.map(item => item.text || item).join('\n');
            } else if (Array.isArray(content)) {
                ruleText = content.join('\n');
            }
            
            html += `<div class="rule-item">`;
            html += `<div class="rule-header">`;
            html += `<span class="rule-number">${idx + 1}/${marriageRules.length}</span>`;
            html += `<span class="rule-name">${ruleName}</span>`;
            html += `</div>`;
            if (ruleText) {
                html += `<div class="rule-content">${ruleText}</div>`;
            }
            html += `</div>`;
        });
        html += '</div>';
    } else {
        html += '<div class="no-data">暂无婚姻规则数据</div>';
    }
    html += '</div>';
    html += '</div>';

    // ✅ 旺衰分析卡片（放在婚姻后面）
    html += '<div class="expandable-card expandable-card-wangshuai" id="wangshuaiCard">';
    html += '<div class="expandable-card-header" onclick="toggleExpandableCard(\'wangshuaiCard\')">';
    html += '<div class="expandable-card-icon">💬</div>';
    html += '<div class="expandable-card-title">命局旺衰';
    html += '<span class="expandable-card-count" id="wangshuaiCount"></span>';
    html += '</div>';
    html += '<div class="expandable-card-arrow" id="wangshuaiCardArrow">▼</div>';
    html += '</div>';
    html += '<div class="expandable-card-content" id="wangshuaiCardContent" style="display: none;">';
    html += '<div class="wangshuai-content" id="wangshuaiContent">';
    html += '<div class="loading">加载中...</div>';
    html += '</div>';
    html += '</div>';
    html += '</div>';

    resultDiv.innerHTML = html;
    
    // 异步加载旺衰分析（确保参数传递正确）
    if (solar_date && solar_time && gender) {
        console.log('开始加载旺衰分析:', { solar_date, solar_time, gender });
        loadWangshuaiAnalysis(solar_date, solar_time, gender);
    } else {
        console.warn('旺衰分析参数缺失:', { solar_date, solar_time, gender });
    }
}

// ✅ 加载旺衰分析
async function loadWangshuaiAnalysis(solar_date, solar_time, gender) {
    console.log('loadWangshuaiAnalysis 被调用:', { solar_date, solar_time, gender });
    
    const contentDiv = document.getElementById('wangshuaiContent');
    const countSpan = document.getElementById('wangshuaiCount');
    
    if (!contentDiv) {
        console.error('旺衰分析容器未找到');
        return;
    }
    
    try {
        console.log('发送旺衰分析请求:', '/bazi/wangshuai');
        const response = await api.post('/bazi/wangshuai', {
            solar_date,
            solar_time,
            gender
        });
        
        console.log('旺衰分析响应:', response);
        
        if (response.success && response.data) {
            const data = response.data;
            let html = '';
            
            // 显示旺衰状态
            html += '<div class="wangshuai-status">';
            html += `<div class="status-title">旺衰状态</div>`;
            html += `<div class="status-value ${getWangshuaiClass(data.wangshuai)}">${data.wangshuai}</div>`;
            html += `<div class="status-score">总分: ${data.total_score} 分</div>`;
            html += '</div>';
            
            // 显示得分详情
            html += '<div class="wangshuai-scores">';
            html += '<div class="score-title">得分详情</div>';
            html += '<div class="score-item">';
            html += `<span class="score-label">得令分（月支权重）:</span>`;
            html += `<span class="score-value">${data.scores.de_ling} 分</span>`;
            html += '</div>';
            html += '<div class="score-item">';
            html += `<span class="score-label">得地分（年日时支）:</span>`;
            html += `<span class="score-value">${data.scores.de_di} 分</span>`;
            html += '</div>';
            html += '<div class="score-item">';
            html += `<span class="score-label">得势分（天干生扶）:</span>`;
            html += `<span class="score-value">${data.scores.de_shi} 分</span>`;
            html += '</div>';
            html += '</div>';
            
            // 显示喜忌
            html += '<div class="wangshuai-xi-ji">';
            html += '<div class="xi-ji-row">';
            html += '<div class="xi-ji-item">';
            html += '<div class="xi-ji-title">喜神</div>';
            html += '<div class="xi-ji-content">';
            if (data.xi_shen && data.xi_shen.length > 0) {
                html += data.xi_shen.map(s => `<span class="xi-ji-tag">${s}</span>`).join('');
            } else {
                html += '<span class="no-data">无</span>';
            }
            html += '</div>';
            html += '</div>';
            html += '<div class="xi-ji-item">';
            html += '<div class="xi-ji-title">忌神</div>';
            html += '<div class="xi-ji-content">';
            if (data.ji_shen && data.ji_shen.length > 0) {
                html += data.ji_shen.map(s => `<span class="ji-ji-tag">${s}</span>`).join('');
            } else {
                html += '<span class="no-data">无</span>';
            }
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
            
            // 显示喜忌五行
            html += '<div class="wangshuai-elements">';
            html += '<div class="elements-row">';
            html += '<div class="elements-item">';
            html += '<div class="elements-title">喜神五行</div>';
            html += '<div class="elements-content">';
            if (data.xi_shen_elements && data.xi_shen_elements.length > 0) {
                html += data.xi_shen_elements.map(e => `<span class="element-tag xi-element">${e}</span>`).join('');
            } else {
                html += '<span class="no-data">无</span>';
            }
            html += '</div>';
            html += '</div>';
            html += '<div class="elements-item">';
            html += '<div class="elements-title">忌神五行</div>';
            html += '<div class="elements-content">';
            if (data.ji_shen_elements && data.ji_shen_elements.length > 0) {
                html += data.ji_shen_elements.map(e => `<span class="element-tag ji-element">${e}</span>`).join('');
            } else {
                html += '<span class="no-data">无</span>';
            }
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
            
            // 显示调候信息
            if (data.tiaohou) {
                html += '<div class="wangshuai-tiaohou">';
                html += '<div class="tiaohou-title">🌡️ 调候</div>';
                html += '<div class="tiaohou-content">';
                
                if (data.tiaohou.tiaohou_element) {
                    html += '<div class="tiaohou-item">';
                    html += '<span class="tiaohou-label">调候五行:</span>';
                    html += `<span class="tiaohou-element element-${data.tiaohou.tiaohou_element}">${data.tiaohou.tiaohou_element}</span>`;
                    html += '</div>';
                    html += `<div class="tiaohou-desc">${data.tiaohou.description}</div>`;
                } else {
                    html += `<div class="tiaohou-desc">${data.tiaohou.description}</div>`;
                }
                
                html += '</div>';
                html += '</div>';
            }
            
            contentDiv.innerHTML = html;
            
            // 更新计数
            if (countSpan) {
                countSpan.textContent = `(${data.wangshuai})`;
            }
        } else {
            console.warn('旺衰分析响应格式错误:', response);
            contentDiv.innerHTML = '<div class="no-data">暂无旺衰分析数据</div>';
        }
    } catch (error) {
        console.error('加载旺衰分析失败:', error);
        contentDiv.innerHTML = `<div class="error">加载失败: ${error.message || '未知错误'}</div>`;
        
        // 显示错误详情（开发调试用）
        if (error.stack) {
            console.error('错误堆栈:', error.stack);
        }
    }
}

// ✅ 获取旺衰状态样式类
function getWangshuaiClass(wangshuai) {
    const classMap = {
        '极旺': 'wangshuai-very-strong',
        '身旺': 'wangshuai-strong',
        '平衡': 'wangshuai-balance',
        '身弱': 'wangshuai-weak',
        '极弱': 'wangshuai-very-weak'
    };
    return classMap[wangshuai] || 'wangshuai-balance';
}

// ✅ 切换可展开卡片
function toggleExpandableCard(cardId) {
    const content = document.getElementById(cardId + 'Content');
    const arrow = document.getElementById(cardId + 'Arrow');
    
    if (content && arrow) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            arrow.textContent = '▲';
        } else {
            content.style.display = 'none';
            arrow.textContent = '▼';
        }
    }
}

// 暴露到全局
window.toggleExpandableCard = toggleExpandableCard;
window.loadWangshuaiAnalysis = loadWangshuaiAnalysis;
window.getWangshuaiClass = getWangshuaiClass;

// 获取五行对应的CSS类名
function getWuxingClass(wuxing) {
    const map = {
        '木': 'wuxing-wood',
        '火': 'wuxing-fire',
        '土': 'wuxing-earth',
        '金': 'wuxing-metal',
        '水': 'wuxing-water'
    };
    return map[wuxing] || '';
}


