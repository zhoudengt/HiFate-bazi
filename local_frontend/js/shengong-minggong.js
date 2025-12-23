// 身宫命宫页面逻辑

console.log('shengong-minggong.js 开始加载');

let currentData = {
    solar_date: '',
    solar_time: '',
    gender: '',
    shengong: null,
    minggong: null,
    pillars: null
};

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
    const form = document.getElementById('shengongMinggongForm');
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
        if (form) form.style.display = 'none';
        
        // 自动查询
        currentData.solar_date = savedDate;
        currentData.solar_time = savedTime;
        currentData.gender = savedGender;
        
        // 延迟加载，确保DOM完全准备好
        setTimeout(() => {
            loadShengongMinggongData();
        }, 100);
    } else {
        // 显示表单
        if (form) form.style.display = 'block';
    }
}

// 显示表单
function showForm() {
    const userInfoCard = document.getElementById('userInfoCard');
    const form = document.getElementById('shengongMinggongForm');
    if (userInfoCard) userInfoCard.style.display = 'none';
    if (form) form.style.display = 'block';
}

// 表单提交
const form = document.getElementById('shengongMinggongForm');
if (form) {
    form.addEventListener('submit', async (e) => {
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
        const formEl = document.getElementById('shengongMinggongForm');
        const cardEl = document.getElementById('userInfoCard');
        const infoDateEl = document.getElementById('infoDate');
        const infoTimeEl = document.getElementById('infoTime');
        const infoGenderEl = document.getElementById('infoGender');
        
        if (formEl) formEl.style.display = 'none';
        if (cardEl) cardEl.style.display = 'block';
        if (infoDateEl) infoDateEl.textContent = solar_date;
        if (infoTimeEl) infoTimeEl.textContent = solar_time;
        if (infoGenderEl) infoGenderEl.textContent = gender === 'male' ? '男' : '女';
        
        await loadShengongMinggongData();
    });
}

// 加载身宫命宫数据
async function loadShengongMinggongData() {
    const resultDiv = document.getElementById('result');
    if (!resultDiv) {
        console.error('找不到 result 元素');
        return;
    }
    
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading">正在计算身宫命宫，请稍候...</div>';
    
    try {
        // 构建请求参数
        const requestData = {
            solar_date: currentData.solar_date,
            solar_time: currentData.solar_time,
            gender: currentData.gender
        };
        
        // 调用API获取身宫命宫数据
        const response = await api.post('/bazi/shengong-minggong', requestData);
        
        if (response.success) {
            console.log('API返回数据:', response);
            
            // ✅ 修复：从 response.data 中获取数据（符合 BaziResponse 结构）
            if (response.data) {
                currentData.shengong = response.data.shengong || {};
                currentData.minggong = response.data.minggong || {};
                currentData.taiyuan = response.data.taiyuan || {};
                currentData.pillars = response.data.pillars || {};
                
                // ✅ 提取大运流年流月数据
                currentData.dayun = response.data.dayun || {};
                currentData.liunian = response.data.liunian || {};
                currentData.liuyue = response.data.liuyue || {};
                
                // 调试日志（详细输出）
                console.log('=== 细盘渲染调试 ===');
                console.log('身宫数据:', currentData.shengong);
                console.log('命宫数据:', currentData.minggong);
                console.log('胎元数据:', currentData.taiyuan);
                console.log('四柱数据:', currentData.pillars);
                console.log('大运数据:', currentData.dayun);
                console.log('流年数据:', currentData.liunian);
                console.log('流月数据:', currentData.liuyue);
                console.log('大运数据详情:', JSON.stringify(currentData.dayun, null, 2));
                console.log('流年数据详情:', JSON.stringify(currentData.liunian, null, 2));
                console.log('流月数据详情:', JSON.stringify(currentData.liuyue, null, 2));
                console.log('==================');
            } else {
                console.warn('API 返回成功但 data 为空:', response);
                currentData.shengong = {};
                currentData.minggong = {};
                currentData.taiyuan = {};
                currentData.pillars = {};
                currentData.dayun = {};
                currentData.liunian = {};
                currentData.liuyue = {};
            }
            
            // 显示结果区域
            resultDiv.style.display = 'block';
            
            // 确保结果区域有正确的HTML结构
            // 检查并创建细盘表格
            if (!document.getElementById('xipanTable')) {
                const xipanCard = document.createElement('div');
                xipanCard.className = 'card';
                xipanCard.id = 'xipanCard';
                xipanCard.innerHTML = `
                    <div class="card-header">
                        <h2 class="card-title">细盘</h2>
                    </div>
                    <div class="timeline-container">
                        <table class="timeline-table" id="xipanTable"></table>
                    </div>
                `;
                resultDiv.appendChild(xipanCard);
            }
            
            // 检查并创建起运和交运信息卡片
            if (!document.getElementById('qiyunInfoCard')) {
                const qiyunCard = document.createElement('div');
                qiyunCard.className = 'card';
                qiyunCard.id = 'qiyunInfoCard';
                qiyunCard.style.display = 'none';
                qiyunCard.innerHTML = `
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
                `;
                resultDiv.appendChild(qiyunCard);
            }
            
            // 检查并创建大运时间轴表格
            if (!document.getElementById('dayunCard')) {
                const dayunCard = document.createElement('div');
                dayunCard.className = 'card';
                dayunCard.id = 'dayunCard';
                dayunCard.style.display = 'none';
                dayunCard.innerHTML = `
                    <div class="card-header">
                        <h2 class="card-title">大运</h2>
                    </div>
                    <div class="timeline-container">
                        <table class="timeline-table" id="dayunTable"></table>
                    </div>
                `;
                resultDiv.appendChild(dayunCard);
            }
            
            // 检查并创建流年时间轴表格
            if (!document.getElementById('liunianCard')) {
                const liunianCard = document.createElement('div');
                liunianCard.className = 'card';
                liunianCard.id = 'liunianCard';
                liunianCard.style.display = 'none';
                liunianCard.innerHTML = `
                    <div class="card-header">
                        <h2 class="card-title">流年</h2>
                    </div>
                    <div class="timeline-container">
                        <table class="timeline-table" id="liunianTable"></table>
                    </div>
                `;
                resultDiv.appendChild(liunianCard);
            }
            
            // 检查并创建流月时间轴表格
            if (!document.getElementById('liuyueCard')) {
                const liuyueCard = document.createElement('div');
                liuyueCard.className = 'card';
                liuyueCard.id = 'liuyueCard';
                liuyueCard.style.display = 'none';
                liuyueCard.innerHTML = `
                    <div class="card-header">
                        <h2 class="card-title">流月</h2>
                    </div>
                    <div class="timeline-container">
                        <table class="timeline-table" id="liuyueTable"></table>
                    </div>
                `;
                resultDiv.appendChild(liuyueCard);
            }
            
            // 渲染细盘表格
            renderXipanTable(currentData);
            
            // ✅ 显示起运和交运信息
            try {
                displayQiyunJiaoyun(currentData.dayun);
                console.log('起运交运信息显示完成');
            } catch (e) {
                console.error('起运交运信息显示失败:', e);
            }
            
            // ✅ 渲染大运流年流月
            try {
                renderDayunSection();
                console.log('大运渲染完成');
            } catch (e) {
                console.error('大运渲染失败:', e);
            }
            
            try {
                renderLiunianSection();
                console.log('流年渲染完成');
            } catch (e) {
                console.error('流年渲染失败:', e);
            }
            
            try {
                renderLiuyueSection();
                console.log('流月渲染完成');
            } catch (e) {
                console.error('流月渲染失败:', e);
            }
            
        } else {
            console.error('获取身宫命宫数据失败:', response.error);
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        console.error('加载身宫命宫数据失败:', error);
        resultDiv.innerHTML = `<div class="error">加载失败: ${error.message || '未知错误'}</div>`;
    }
}

// 渲染细盘表格
function renderXipanTable(data) {
    const table = document.getElementById('xipanTable');
    if (!table || !data) {
        console.error('renderXipanTable: 缺少数据', { table, data });
        return;
    }
    
    const shengong = data.shengong || {};
    const minggong = data.minggong || {};
    const taiyuan = data.taiyuan || {};
    const pillars = data.pillars || {};
    
    // 调试日志（仅在开发环境）
    if (API_CONFIG.env === 'development') {
        console.log('=== 细盘渲染调试 ===');
        console.log('身宫数据:', shengong);
        console.log('命宫数据:', minggong);
        console.log('胎元数据:', taiyuan);
        console.log('四柱数据:', pillars);
        console.log('==================');
    }
    
    // 构建表头：身宫、命宫、胎元、年柱、月柱、日柱、时柱
    let html = '<thead><tr>';
    html += '<th>行</th>';
    html += '<th>身宫</th>';
    html += '<th>命宫</th>';
    html += '<th>胎元</th>';
    html += '<th>年柱</th>';
    html += '<th>月柱</th>';
    html += '<th>日柱</th>';
    html += '<th>时柱</th>';
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // 定义行数据
    const rows = [
        { name: '主星', key: 'main_star' },
        { name: '天干', key: 'stem' },
        { name: '地支', key: 'branch' },
        { name: '藏干', key: 'hidden_stems' },
        { name: '星运', key: 'star_fortune' },
        { name: '自坐', key: 'self_sitting' },
        { name: '空亡', key: 'kongwang' },
        { name: '纳音', key: 'nayin' },
        { name: '神煞', key: 'deities' }
    ];
    
    // 获取身宫数据
    const shengongStem = shengong.stem?.char || shengong.stem || '';
    const shengongBranch = shengong.branch?.char || shengong.branch || '';
    
    // 获取命宫数据
    const minggongStem = minggong.stem?.char || minggong.stem || '';
    const minggongBranch = minggong.branch?.char || minggong.branch || '';
    
    // 获取胎元数据
    const taiyuanStem = taiyuan.stem?.char || taiyuan.stem || '';
    const taiyuanBranch = taiyuan.branch?.char || taiyuan.branch || '';
    
    // 渲染每一行
    rows.forEach(row => {
        html += '<tr>';
        html += `<th>${row.name}</th>`;
        
        // 身宫列
        const shengongValue = getRowValue(shengong, row.key, shengongStem, shengongBranch);
        html += `<td>${shengongValue}</td>`;
        
        // 命宫列
        const minggongValue = getRowValue(minggong, row.key, minggongStem, minggongBranch);
        html += `<td>${minggongValue}</td>`;
        
        // 胎元列
        const taiyuanValue = getRowValue(taiyuan, row.key, taiyuanStem, taiyuanBranch);
        html += `<td>${taiyuanValue}</td>`;
        
        // 四柱列
        ['year', 'month', 'day', 'hour'].forEach(pillarType => {
            const pillar = pillars[pillarType] || {};
            const pillarStem = pillar.stem?.char || pillar.stem || '';
            const pillarBranch = pillar.branch?.char || pillar.branch || '';
            const pillarValue = getRowValue(pillar, row.key, pillarStem, pillarBranch);
            html += `<td>${pillarValue}</td>`;
        });
        
        html += '</tr>';
    });
    
    html += '</tbody>';
    table.innerHTML = html;
}

// 辅助函数：获取行值
function getRowValue(item, key, stem, branch) {
    if (!item) return '-';
    
    switch (key) {
        case 'main_star':
            return item.main_star || '-';
        case 'stem':
            return stem || '-';
        case 'branch':
            return branch || '-';
        case 'hidden_stems':
            const hiddenStems = item.hidden_stems || [];
            if (Array.isArray(hiddenStems)) {
                return hiddenStems.length > 0 ? hiddenStems.join(' ') : '-';
            }
            return hiddenStems || '-';
        case 'star_fortune':
            return item.star_fortune || '-';
        case 'self_sitting':
            return item.self_sitting || '-';
        case 'kongwang':
            return item.kongwang || '-';
        case 'nayin':
            return item.nayin || '-';
        case 'deities':
            const deities = item.deities || [];
            if (Array.isArray(deities)) {
                return deities.length > 0 ? deities.join(' ') : '-';
            }
            return deities || '-';
        default:
            return '-';
    }
}

// 显示起运和交运信息
function displayQiyunJiaoyun(dayunData) {
    if (!dayunData) {
        console.warn('displayQiyunJiaoyun: 缺少大运数据');
        return;
    }
    
    const qiyunInfo = dayunData.qiyun || {};
    const jiaoyunInfo = dayunData.jiaoyun || {};
    
    const qiyunDateEl = document.getElementById('qiyunDate');
    const qiyunAgeEl = document.getElementById('qiyunAge');
    const jiaoyunDateEl = document.getElementById('jiaoyunDate');
    const jiaoyunAgeEl = document.getElementById('jiaoyunAge');
    const qiyunInfoCard = document.getElementById('qiyunInfoCard');
    
    // 使用 description 字段显示起运交运信息
    if (qiyunDateEl) qiyunDateEl.textContent = qiyunInfo.description || qiyunInfo.date || '-';
    if (qiyunAgeEl) qiyunAgeEl.textContent = qiyunInfo.age_display ? `(${qiyunInfo.age_display})` : '';
    if (jiaoyunDateEl) jiaoyunDateEl.textContent = jiaoyunInfo.description || jiaoyunInfo.date || '-';
    if (jiaoyunAgeEl) jiaoyunAgeEl.textContent = jiaoyunInfo.age_display ? `(${jiaoyunInfo.age_display})` : '';
    
    // 只要有 description 或 date 就显示卡片
    if (qiyunInfoCard && (qiyunInfo.description || qiyunInfo.date || jiaoyunInfo.description || jiaoyunInfo.date)) {
        qiyunInfoCard.style.display = 'block';
    }
}

// 渲染大运部分
function renderDayunSection() {
    console.log('renderDayunSection 被调用', { dayun: currentData.dayun });
    
    const dayunCard = document.getElementById('dayunCard');
    if (!dayunCard) {
        console.error('找不到 dayunCard 元素');
        return;
    }
    
    if (!currentData.dayun || !currentData.dayun.current) {
        dayunCard.style.display = 'none';
        return;
    }
    
    // 使用时间轴渲染函数（如果可用）
    if (typeof renderDayunTimeline === 'function') {
        // 构建大运数据（只包含当前大运）
        const dayunData = {
            current: currentData.dayun.current,
            list: currentData.dayun.current ? [currentData.dayun.current] : []
        };
        renderDayunTimeline(dayunData);
        dayunCard.style.display = 'block';
    } else {
        console.warn('renderDayunTimeline 函数不存在，使用降级方案');
        // 降级方案：显示当前大运信息
        const dayunTable = document.getElementById('dayunTable');
        if (!dayunTable) {
            console.error('找不到 dayunTable 元素');
            return;
        }
        
        const currentDayun = currentData.dayun.current;
        let html = '<tbody><tr>';
        html += '<th>大运</th>';
        html += '<th>年份</th>';
        html += '<th>年龄</th>';
        html += '</tr>';
        html += '<tr>';
        html += `<td>${currentDayun.ganzhi || '-'}</td>`;
        const yearRange = currentDayun.year_range || {};
        html += `<td>${yearRange.start && yearRange.end ? `${yearRange.start}-${yearRange.end}` : currentDayun.year_display || '-'}</td>`;
        const ageRange = currentDayun.age_range || {};
        html += `<td>${ageRange.start !== undefined && ageRange.end !== undefined ? `${ageRange.start}-${ageRange.end}岁` : currentDayun.age_display || '-'}</td>`;
        html += '</tr></tbody>';
        dayunTable.innerHTML = html;
        dayunCard.style.display = 'block';
    }
}

// 渲染流年部分
function renderLiunianSection() {
    console.log('renderLiunianSection 被调用', { liunian: currentData.liunian });
    
    const liunianCard = document.getElementById('liunianCard');
    if (!liunianCard) {
        console.error('找不到 liunianCard 元素');
        return;
    }
    
    if (!currentData.liunian || !currentData.liunian.list || currentData.liunian.list.length === 0) {
        liunianCard.style.display = 'none';
        return;
    }
    
    // 使用时间轴渲染函数（如果可用）
    if (typeof renderLiunianTimeline === 'function') {
        renderLiunianTimeline(currentData.liunian);
        liunianCard.style.display = 'block';
    } else {
        console.warn('renderLiunianTimeline 函数不存在，使用降级方案');
        // 降级方案：显示流年列表
        const liunianTable = document.getElementById('liunianTable');
        if (!liunianTable) {
            console.error('找不到 liunianTable 元素');
            return;
        }
        
        const liunianList = currentData.liunian.list;
        let html = '<thead><tr>';
        html += '<th>流年</th>';
        liunianList.forEach(item => {
            html += `<th>${item.year || '-'}</th>`;
        });
        html += '</tr></thead>';
        html += '<tbody><tr>';
        html += '<th>干支</th>';
        liunianList.forEach(item => {
            html += `<td>${item.ganzhi || '-'}</td>`;
        });
        html += '</tr></tbody>';
        liunianTable.innerHTML = html;
        liunianCard.style.display = 'block';
    }
}

// 渲染流月部分
function renderLiuyueSection() {
    console.log('renderLiuyueSection 被调用', { liuyue: currentData.liuyue });
    
    const liuyueCard = document.getElementById('liuyueCard');
    if (!liuyueCard) {
        console.error('找不到 liuyueCard 元素');
        return;
    }
    
    if (!currentData.liuyue || !currentData.liuyue.list || currentData.liuyue.list.length === 0) {
        liuyueCard.style.display = 'none';
        return;
    }
    
    // 使用时间轴渲染函数（如果可用）
    if (typeof renderLiuyueTimeline === 'function') {
        renderLiuyueTimeline(currentData.liuyue);
        liuyueCard.style.display = 'block';
    } else {
        console.warn('renderLiuyueTimeline 函数不存在，使用降级方案');
        // 降级方案：显示流月列表
        const liuyueTable = document.getElementById('liuyueTable');
        if (!liuyueTable) {
            console.error('找不到 liuyueTable 元素');
            return;
        }
        
        const liuyueList = currentData.liuyue.list;
        let html = '<thead><tr>';
        html += '<th>流月</th>';
        liuyueList.forEach(item => {
            html += `<th>${item.month || '-'}月</th>`;
        });
        html += '</tr></thead>';
        html += '<tbody><tr>';
        html += '<th>干支</th>';
        liuyueList.forEach(item => {
            html += `<td>${item.ganzhi || '-'}</td>`;
        });
        html += '</tr></tbody>';
        liuyueTable.innerHTML = html;
        liuyueCard.style.display = 'block';
    }
}
