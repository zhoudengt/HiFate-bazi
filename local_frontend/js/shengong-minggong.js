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
                currentData.pillars = response.data.pillars || {};
                
                // 调试日志（仅在开发环境）
                if (typeof API_CONFIG !== 'undefined' && API_CONFIG.env === 'development') {
                    console.log('=== 细盘渲染调试 ===');
                    console.log('身宫数据:', currentData.shengong);
                    console.log('命宫数据:', currentData.minggong);
                    console.log('四柱数据:', currentData.pillars);
                    console.log('==================');
                }
            } else {
                console.warn('API 返回成功但 data 为空:', response);
                currentData.shengong = {};
                currentData.minggong = {};
                currentData.pillars = {};
            }
            
            // 显示结果区域
            resultDiv.style.display = 'block';
            
            // 确保结果区域有正确的HTML结构（如果被清空了）
            if (!document.getElementById('xipanTable')) {
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
                `;
            }
            
            // 渲染细盘表格
            renderXipanTable(currentData);
            
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
    const pillars = data.pillars || {};
    
    // 调试日志（仅在开发环境）
    if (API_CONFIG.env === 'development') {
        console.log('=== 细盘渲染调试 ===');
        console.log('身宫数据:', shengong);
        console.log('命宫数据:', minggong);
        console.log('四柱数据:', pillars);
        console.log('==================');
    }
    
    // 构建表头：身宫、命宫、年柱、月柱、日柱、时柱
    let html = '<thead><tr>';
    html += '<th>行</th>';
    html += '<th>身宫</th>';
    html += '<th>命宫</th>';
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
