// 大运流年流月整合页面逻辑

console.log('fortune.js 开始加载');

let currentData = {
    solar_date: '',
    solar_time: '',
    gender: '',
    dayun: null,
    liunian: null,
    liuyue: null,
    selectedDayun: null,
    selectedLiunian: null
};

// 暴露到全局，供 fortune-timeline.js 使用
window.currentData = currentData;

// 页面加载时填充用户信息
document.addEventListener('DOMContentLoaded', () => {
    UserInfo.fillForm();
    checkSavedInfo();
});

// 检查是否有保存的用户信息
function checkSavedInfo() {
    const savedDate = localStorage.getItem('solar_date');
    const savedTime = localStorage.getItem('solar_time');
    const savedGender = localStorage.getItem('gender');
    
    const userInfoCard = document.getElementById('userInfoCard');
    const fortuneForm = document.getElementById('fortuneForm');
    const infoDate = document.getElementById('infoDate');
    const infoTime = document.getElementById('infoTime');
    const infoGender = document.getElementById('infoGender');
    
    if (savedDate && savedTime && savedGender) {
        // 显示用户信息卡片
        if (userInfoCard) userInfoCard.style.display = 'block';
        if (infoDate) infoDate.textContent = savedDate;
        if (infoTime) infoTime.textContent = savedTime;
        if (infoGender) infoGender.textContent = savedGender === 'male' ? '男' : '女';
        
        // 隐藏表单
        if (fortuneForm) fortuneForm.style.display = 'none';
        
        // 自动查询
        currentData.solar_date = savedDate;
        currentData.solar_time = savedTime;
        currentData.gender = savedGender;
        
        // 延迟加载，确保DOM完全准备好
        setTimeout(() => {
            loadFortuneData();
        }, 100);
    } else {
        // 显示表单
        if (fortuneForm) fortuneForm.style.display = 'block';
    }
}

// 显示表单
function showForm() {
    const userInfoCard = document.getElementById('userInfoCard');
    const fortuneForm = document.getElementById('fortuneForm');
    if (userInfoCard) userInfoCard.style.display = 'none';
    if (fortuneForm) fortuneForm.style.display = 'block';
}

// 表单提交
const fortuneForm = document.getElementById('fortuneForm');
if (fortuneForm) {
    fortuneForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const solar_date = document.getElementById('solar_date')?.value;
        const solar_time = document.getElementById('solar_time')?.value;
        const gender = document.getElementById('gender')?.value;
        
        if (!solar_date || !solar_time || !gender) {
            alert('请填写完整信息');
            return;
        }
        
        // 保存用户信息
        UserInfo.save(solar_date, solar_time, gender);
        
        currentData.solar_date = solar_date;
        currentData.solar_time = solar_time;
        currentData.gender = gender;
        
        // 隐藏表单，显示用户信息卡片
        const formEl = document.getElementById('fortuneForm');
        const cardEl = document.getElementById('userInfoCard');
        const infoDateEl = document.getElementById('infoDate');
        const infoTimeEl = document.getElementById('infoTime');
        const infoGenderEl = document.getElementById('infoGender');
        
        if (formEl) formEl.style.display = 'none';
        if (cardEl) cardEl.style.display = 'block';
        if (infoDateEl) infoDateEl.textContent = solar_date;
        if (infoTimeEl) infoTimeEl.textContent = solar_time;
        if (infoGenderEl) infoGenderEl.textContent = gender === 'male' ? '男' : '女';
        
        await loadFortuneData();
    });
}

// 加载大运流年流月数据（使用统一接口，性能优化）
async function loadFortuneData(dayunIndex = null) {
    const resultDiv = document.getElementById('result');
    if (!resultDiv) {
        console.error('找不到 result 元素');
        return;
    }
    
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading">正在计算大运流年流月，请稍候...</div>';
    
    try {
        // 获取当前时间
        const now = new Date();
        const current_time = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
        
        // 构建请求参数
        const requestData = {
            solar_date: currentData.solar_date,
            solar_time: currentData.solar_time,
            gender: currentData.gender,
            current_time: current_time
        };
        
        // 如果指定了大运索引，只获取该大运范围内的流年（性能优化）
        if (dayunIndex !== null) {
            requestData.dayun_index = dayunIndex;
        }
        
        // 使用统一接口，一次获取所有数据（性能优化）
        const response = await api.post('/bazi/fortune/display', requestData);
        
        if (response.success) {
            console.log('API返回数据:', response);
            
            currentData.dayun = response.dayun;
            currentData.liunian = response.liunian;
            currentData.liuyue = response.liuyue;
            currentData.pillars = response.pillars;  // ✅ 添加四柱信息
            
            // 确定当前选中的大运和流年
            const currentDayun = currentData.dayun?.current;
            const currentLiunian = currentData.liunian?.current;
            
            // ✅ 修复：恢复原有逻辑，默认选中当前大运（不是小运）
            // 小运列只是显示"小运"文字，用户可以手动点击选中
            if (dayunIndex !== null && currentData.dayun?.list) {
                const selectedDayun = currentData.dayun.list.find(item => item.index === dayunIndex);
                if (selectedDayun) {
                    currentData.selectedDayun = selectedDayun;
                } else {
                    currentData.selectedDayun = currentDayun || null;
                }
            } else {
                currentData.selectedDayun = currentDayun || null;
            }
            
            currentData.selectedLiunian = currentLiunian || null;
            
            // 显示结果区域
            resultDiv.style.display = 'block';
            
            // 确保结果区域有正确的HTML结构（如果被清空了）
            if (!document.getElementById('dayunTable')) {
                resultDiv.innerHTML = `
                    <!-- 细盘表格 -->
                    <div class="card" id="xipanCard">
                        <div class="card-header">
                            <h2 class="card-title">细盘</h2>
                        </div>
                        <div class="timeline-container">
                            <table class="timeline-table" id="xipanTable"></table>
                        </div>
                    </div>
                    
                    <!-- 起运和交运信息 -->
                    <div class="card" id="qiyunInfoCard" style="display: none;">
                        <div class="card-header">
                            <h2 class="card-title">起运与交运</h2>
                        </div>
                        <div class="card-body">
                            <div id="qiyunInfo" style="display: flex; gap: 30px; padding: 15px;">
                                <div>
                                    <strong>起运：</strong>
                                    <span id="qiyunDate"></span>
                                    <span id="qiyunAge"></span>
                                </div>
                                <div>
                                    <strong>交运：</strong>
                                    <span id="jiaoyunDate"></span>
                                    <span id="jiaoyunAge"></span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 大运时间轴表格 -->
                    <div class="card" id="dayunCard">
                        <div class="card-header">
                            <h2 class="card-title">大运</h2>
                        </div>
                        <div class="timeline-container">
                            <table class="timeline-table" id="dayunTable"></table>
                        </div>
                    </div>
                    
                    <!-- 流年时间轴表格 -->
                    <div class="card" id="liunianCard">
                        <div class="card-header">
                            <h2 class="card-title">流年</h2>
                        </div>
                        <div class="timeline-container">
                            <table class="timeline-table" id="liunianTable"></table>
                        </div>
                    </div>
                    
                    <!-- 流月时间轴表格 -->
                    <div class="card" id="liuyueCard">
                        <div class="card-header">
                            <h2 class="card-title">流月</h2>
                        </div>
                        <div class="timeline-container">
                            <table class="timeline-table" id="liuyueTable"></table>
                        </div>
                    </div>
                `;
            }
            
            // 渲染所有数据（时间轴表格形式）
            console.log('开始渲染数据...', {
                dayun: currentData.dayun,
                liunian: currentData.liunian,
                liuyue: currentData.liuyue
            });
            
            try {
                renderDayun();
                console.log('大运渲染完成');
            } catch (e) {
                console.error('大运渲染失败:', e);
            }
            
            try {
                renderLiunian();
                console.log('流年渲染完成');
            } catch (e) {
                console.error('流年渲染失败:', e);
            }
            
            try {
                renderLiuyue();
                console.log('流月渲染完成');
            } catch (e) {
                console.error('流月渲染失败:', e);
            }
            
            // ✅ 渲染细盘表格
            try {
                renderXipanTable(currentData);
                console.log('细盘渲染完成');
            } catch (e) {
                console.error('细盘渲染失败:', e);
            }
            
            // ✅ 显示起运和交运信息
            try {
                displayQiyunInfo(response.dayun);
                console.log('起运交运信息显示完成');
            } catch (e) {
                console.error('起运交运信息显示失败:', e);
            }
            
            console.log('所有渲染完成');
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        const errorMsg = error.message || '加载失败';
        resultDiv.innerHTML = `
            <div class="error">
                <p><strong>错误：</strong>${errorMsg}</p>
                <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    如果问题持续，请检查：<br>
                    1. 后端服务是否运行（端口 8001）<br>
                    2. 网络连接是否正常<br>
                    3. 浏览器控制台是否有错误信息
                </p>
                <button onclick="loadFortuneData()" class="btn btn-primary" style="margin-top: 15px;">重试</button>
            </div>
        `;
    }
}

// 加载流月数据
async function loadLiuyue(targetYear) {
    try {
        const liuyueResponse = await api.post('/bazi/liuyue/display', {
            solar_date: currentData.solar_date,
            solar_time: currentData.solar_time,
            gender: currentData.gender,
            target_year: targetYear
        });
        
        if (liuyueResponse.success) {
            currentData.liuyue = liuyueResponse.liuyue;
            renderLiuyue();
        }
    } catch (error) {
        console.error('加载流月失败:', error);
    }
}

// 渲染大运（时间轴表格形式）
function renderDayun() {
    console.log('renderDayun 被调用', { dayun: currentData.dayun });
    
    // 使用时间轴表格渲染
    if (typeof renderDayunTimeline === 'function') {
        renderDayunTimeline(currentData.dayun);
    } else {
        console.warn('renderDayunTimeline 函数不存在，使用降级方案');
        // 降级到列表形式
        const dayunList = document.getElementById('dayunList');
        if (!dayunList) {
            console.error('找不到 dayunList 元素');
            return;
        }
        
        if (!currentData.dayun || !currentData.dayun.list) {
            dayunList.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }
        
        let html = '';
        currentData.dayun.list.forEach(item => {
            if (!item.ganzhi) return;
            
            const isCurrent = item.is_current ? 'current' : '';
            const isActive = currentData.selectedDayun && item.index === currentData.selectedDayun.index ? 'active' : '';
            const ageRange = item.age_range || {};
            
            html += `
                <div class="fortune-item dayun-item ${isCurrent} ${isActive}" 
                     onclick="selectDayun(${item.index})">
                    <div class="dayun-info">
                        <div class="dayun-ganzhi">${item.ganzhi}</div>
                        <div class="dayun-age">
                            ${ageRange.start !== undefined && ageRange.end !== undefined 
                                ? `${ageRange.start}-${ageRange.end}岁` 
                                : item.age_display || ''}
                            ${item.is_current ? '<span class="current-badge">当前</span>' : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        dayunList.innerHTML = html || '<div class="loading">暂无数据</div>';
    }
}

// 渲染流年（时间轴表格形式）
function renderLiunian() {
    console.log('renderLiunian 被调用', { liunian: currentData.liunian });
    
    // 使用时间轴表格渲染
    if (typeof renderLiunianTimeline === 'function') {
        renderLiunianTimeline(currentData.liunian);
    } else {
        console.warn('renderLiunianTimeline 函数不存在，使用降级方案');
        // 降级到列表形式
        const liunianList = document.getElementById('liunianList');
        if (!liunianList) {
            console.error('找不到 liunianList 元素');
            return;
        }
        
        if (!currentData.liunian || !currentData.liunian.list) {
            liunianList.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }
        
        const filteredLiunian = currentData.liunian.list;
        
        let html = '';
        filteredLiunian.forEach(item => {
            if (!item.year) return;
            
            const isCurrent = item.is_current ? 'current' : '';
            const isActive = currentData.selectedLiunian && item.year === currentData.selectedLiunian.year ? 'active' : '';
            
            html += `
                <div class="fortune-item liunian-item ${isCurrent} ${isActive}" 
                     onclick="selectLiunian(${item.year})">
                    <div class="liunian-year">${item.year}年</div>
                    <div class="liunian-ganzhi">${item.ganzhi || ''}</div>
                    <div class="liunian-age">
                        ${item.age !== undefined ? `${item.age}岁` : item.age_display || ''}
                        ${item.is_current ? '<span class="current-badge">当前</span>' : ''}
                    </div>
                </div>
            `;
        });
        
        liunianList.innerHTML = html || '<div class="loading">暂无数据</div>';
    }
}

// 渲染流月（时间轴表格形式）
function renderLiuyue() {
    console.log('renderLiuyue 被调用', { liuyue: currentData.liuyue });
    
    // 使用时间轴表格渲染
    if (typeof renderLiuyueTimeline === 'function') {
        renderLiuyueTimeline(currentData.liuyue);
    } else {
        console.warn('renderLiuyueTimeline 函数不存在，使用降级方案');
        // 降级到列表形式
        const liuyueList = document.getElementById('liuyueList');
        if (!liuyueList) {
            console.error('找不到 liuyueList 元素');
            return;
        }
        
        if (!currentData.liuyue || !currentData.liuyue.list) {
            liuyueList.innerHTML = '<div class="loading">暂无数据</div>';
            return;
        }
        
        let html = '';
        currentData.liuyue.list.forEach(item => {
            if (!item.month) return;
            
            const isCurrent = item.is_current ? 'current' : '';
            
            html += `
                <div class="fortune-item liuyue-item ${isCurrent}">
                    <div>
                        <div class="liuyue-month">${item.month}月</div>
                        <div class="liuyue-term">${item.solar_term || ''} ${item.term_date || ''}</div>
                    </div>
                    <div class="liuyue-ganzhi">${item.ganzhi || ''}</div>
                    ${item.is_current ? '<span class="current-badge">当前</span>' : ''}
                </div>
            `;
        });
        
        liuyueList.innerHTML = html || '<div class="loading">暂无数据</div>';
    }
}

// 选择大运
async function selectDayun(dayunIndex) {
    console.log('selectDayun 被调用，索引:', dayunIndex);
    
    // ✅ 修复：确保 currentData 和 dayun 数据存在
    if (!currentData || !currentData.dayun || !currentData.dayun.list) {
        console.error('currentData 或 dayun 数据不存在');
        return;
    }
    
    // 找到对应的大运
    const selectedDayun = currentData.dayun.list.find(item => item.index === dayunIndex);
    if (!selectedDayun) {
        console.error('找不到对应的大运，索引:', dayunIndex);
        return;
    }
    
    // ✅ 清除之前的流年选中状态
    currentData.selectedLiunian = null;
    
    currentData.selectedDayun = selectedDayun;
    console.log('=== selectDayun 调试 ===');
    console.log('选中的大运完整数据:', selectedDayun);
    console.log('大运干支:', selectedDayun.stem?.char, selectedDayun.branch?.char);
    console.log('大运详细信息:', {
        nayin: selectedDayun.nayin,
        hidden_stems: selectedDayun.hidden_stems,
        main_star: selectedDayun.main_star,
        star_fortune: selectedDayun.star_fortune,
        self_sitting: selectedDayun.self_sitting,
        kongwang: selectedDayun.kongwang,
        deities: selectedDayun.deities
    });
    console.log('====================');
    
    // ✅ 修复：确保 window.currentData 同步更新
    if (window.currentData) {
        window.currentData.selectedDayun = selectedDayun;
        window.currentData.selectedLiunian = null;
    }
    
    // 重新渲染大运（更新active状态）
    renderDayun();
    
    // ✅ 检查是否是小运
    const isXiaoyun = selectedDayun.stem?.char === '小运' || selectedDayun.stem === '小运';
    
    // 重新加载数据，只获取该大运范围内的流年（性能优化）
    const now = new Date();
    const current_time = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    // 获取大运的起始年份（用于默认加载流月）
    const startYear = selectedDayun.year_range?.start;
    
    try {
        // ✅ 修复：传递大运的年份范围，而不是索引（避免中间多列时出错）
        const yearStart = selectedDayun.year_range?.start;
        const yearEnd = selectedDayun.year_range?.end;
        console.log('请求大运范围内的流年数据，年份范围:', yearStart, '-', yearEnd);
        
        // ✅ 所有数据由后端提供，前端只传递参数（使用年份范围而不是索引）
        const response = await api.post('/bazi/fortune/display', {
            solar_date: currentData.solar_date,
            solar_time: currentData.solar_time,
            gender: currentData.gender,
            current_time: current_time,
            dayun_year_start: yearStart,  // 传递大运起始年份
            dayun_year_end: yearEnd      // 传递大运结束年份
        });
        
        if (response.success) {
            console.log('获取流年数据成功:', response.liunian);
            console.log('流年列表:', response.liunian?.list);
            
            // ✅ 直接使用后端返回的数据，不做任何前端计算或过滤
            currentData.liunian = response.liunian;
            
            // ✅ 清除流月数据，等待重新加载
            currentData.liuyue = null;
            
            // 清空流月显示
            const liuyueTable = document.getElementById('liuyueTable');
            if (liuyueTable) {
                liuyueTable.innerHTML = '<tbody><tr><td colspan="100%">请先选择流年</td></tr></tbody>';
            }
            
            // 重新渲染流年（清除之前的选中状态）
            renderLiunian();
            
            // ✅ 更新细盘表格
            if (typeof renderXipanTable === 'function') {
                renderXipanTable(currentData);
            }
            
            // ✅ 自动选择流年首年（year_start），并加载其流月
            if (currentData.liunian && currentData.liunian.list && currentData.liunian.list.length > 0) {
                // ✅ 如果是小运，选择 year_start（出生年份）对应的流年
                // ✅ 如果不是小运，选择起始年或第一个
                const targetYear = isXiaoyun ? yearStart : (startYear || currentData.liunian.list[0].year);
                console.log('自动选择流年，年份:', targetYear, isXiaoyun ? '(小运)' : '');
                await selectLiunian(targetYear);
            } else {
                console.warn('该大运范围内没有流年数据');
            }
        } else {
            console.error('获取流年数据失败:', response.error);
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        console.error('加载大运数据失败:', error);
    }
}

// 暴露到全局（确保在任何情况下都可以访问）
// ✅ 修复：立即暴露到全局，确保可以被 fortune-timeline.js 调用
window.selectDayun = selectDayun;
console.log('fortune.js selectDayun 已暴露到全局:', typeof window.selectDayun);

// 选择流年
async function selectLiunian(year) {
    console.log('selectLiunian 被调用，年份:', year);
    
    // ✅ 修复：确保 currentData 和 liunian 数据存在
    if (!currentData || !currentData.liunian || !currentData.liunian.list) {
        console.error('currentData 或 liunian 数据不存在');
        return;
    }
    
    // 找到对应的流年
    const selectedLiunian = currentData.liunian.list.find(item => item.year === year);
    if (!selectedLiunian) {
        console.error('找不到对应的流年，年份:', year);
        return;
    }
    
    currentData.selectedLiunian = selectedLiunian;
    console.log('选中的流年:', selectedLiunian);
    
    // ✅ 修复：确保 window.currentData 同步更新
    if (window.currentData) {
        window.currentData.selectedLiunian = selectedLiunian;
    }
    
    // 重新渲染流年（更新active状态）
    renderLiunian();
    
    // 加载并显示该流年的流月（只加载该年份的12个月，性能优化）
    try {
        const now = new Date();
        const current_time = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
        
        // 获取当前大运索引（如果已选中）
        const dayunIndex = currentData.selectedDayun?.index;
        
        console.log('请求流月数据，target_year:', year, 'dayun_index:', dayunIndex);
        const response = await api.post('/bazi/fortune/display', {
            solar_date: currentData.solar_date,
            solar_time: currentData.solar_time,
            gender: currentData.gender,
            current_time: current_time,
            dayun_index: dayunIndex,  // 保持当前大运范围
            target_year: year  // 只获取该年份的流月
        });
        
        if (response.success && response.liuyue) {
            console.log('获取流月数据成功:', response.liuyue);
            console.log('流月列表:', response.liuyue?.list);
            if (response.liuyue?.list && response.liuyue.list.length > 0) {
                console.log('第一个流月数据:', response.liuyue.list[0]);
                console.log('第一个流月stem:', response.liuyue.list[0].stem);
                console.log('第一个流月branch:', response.liuyue.list[0].branch);
            }
            
            // ✅ 确保流月数据正确更新
            currentData.liuyue = response.liuyue;
            renderLiuyue();
            
            // ✅ 更新细盘表格
            if (typeof renderXipanTable === 'function') {
                renderXipanTable(currentData);
            }
        } else {
            console.error('获取流月数据失败:', response.error || '没有返回流月数据');
            console.error('完整响应:', response);
        }
    } catch (error) {
        console.error('加载流月失败:', error);
        // 如果失败，尝试使用旧的接口
        try {
            await loadLiuyue(year);
        } catch (e) {
            console.error('使用旧接口也失败:', e);
        }
    }
}

// 暴露到全局（确保在任何情况下都可以访问）
// ✅ 修复：立即暴露到全局，确保可以被 fortune-timeline.js 调用
window.selectLiunian = selectLiunian;
console.log('fortune.js selectLiunian 已暴露到全局:', typeof window.selectLiunian);


// ✅ 显示起运和交运信息
function displayQiyunInfo(dayunData) {
    if (!dayunData) return;
    
    const qiyunInfo = dayunData.qiyun || {};
    const jiaoyunInfo = dayunData.jiaoyun || {};
    
    const qiyunDateEl = document.getElementById('qiyunDate');
    const qiyunAgeEl = document.getElementById('qiyunAge');
    const jiaoyunDateEl = document.getElementById('jiaoyunDate');
    const jiaoyunAgeEl = document.getElementById('jiaoyunAge');
    const qiyunInfoCard = document.getElementById('qiyunInfoCard');
    
    if (qiyunDateEl) qiyunDateEl.textContent = qiyunInfo.date || '-';
    if (qiyunAgeEl) qiyunAgeEl.textContent = qiyunInfo.age_display ? `(${qiyunInfo.age_display})` : '';
    if (jiaoyunDateEl) jiaoyunDateEl.textContent = jiaoyunInfo.date || '-';
    if (jiaoyunAgeEl) jiaoyunAgeEl.textContent = jiaoyunInfo.age_display ? `(${jiaoyunInfo.age_display})` : '';
    
    // 显示起运交运信息卡片
    if (qiyunInfoCard && (qiyunInfo.date || jiaoyunInfo.date)) {
        qiyunInfoCard.style.display = 'block';
    }
}
