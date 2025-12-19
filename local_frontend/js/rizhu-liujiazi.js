// 日元-六十甲子逻辑
let hasResult = false;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    const userInfo = UserInfo.load();
    if (userInfo) {
        // 有保存的信息，显示信息卡片，隐藏表单
        showUserInfo(userInfo);
        // 自动查询
        queryRizhuLiujiazi(userInfo.solar_date, userInfo.solar_time, userInfo.gender);
    } else {
        // 没有保存的信息，显示提示
        showNoBirthInfo();
    }
    
    // 修改按钮事件
    const editBtn = document.getElementById('editBtn');
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            showForm();
        });
    }
    
    // 表单提交事件
    const rizhuForm = document.getElementById('rizhuForm');
    if (rizhuForm) {
        rizhuForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const solar_date = document.getElementById('solar_date').value;
            const solar_time = document.getElementById('solar_time').value;
            const gender = document.getElementById('gender').value;
            
            // 保存用户信息
            UserInfo.save(solar_date, solar_time, gender);
            
            // 显示信息卡片
            showUserInfo({solar_date, solar_time, gender});
            
            // 查询
            queryRizhuLiujiazi(solar_date, solar_time, gender);
        });
    }
});

function showUserInfo(info) {
    const userInfoDisplay = document.getElementById('userInfoDisplay');
    const rizhuForm = document.getElementById('rizhuForm');
    
    if (userInfoDisplay) {
        userInfoDisplay.style.display = 'block';
    }
    if (rizhuForm) {
        rizhuForm.style.display = 'none';
    }
    
    const displayDate = document.getElementById('display_date');
    const displayTime = document.getElementById('display_time');
    const displayGender = document.getElementById('display_gender');
    
    if (displayDate) displayDate.textContent = info.solar_date;
    if (displayTime) displayTime.textContent = info.solar_time;
    const genderText = info.gender === 'male' ? '男' : '女';
    if (displayGender) displayGender.textContent = genderText;
    
    // 更新头部用户信息
    const userNameEl = document.getElementById('userName');
    const userGenderEl = document.getElementById('userGender');
    if (userNameEl) userNameEl.textContent = '用户';
    if (userGenderEl) userGenderEl.textContent = genderText;
}

function showForm() {
    const userInfoDisplay = document.getElementById('userInfoDisplay');
    const rizhuForm = document.getElementById('rizhuForm');
    
    if (userInfoDisplay) {
        userInfoDisplay.style.display = 'none';
    }
    if (rizhuForm) {
        rizhuForm.style.display = 'block';
    }
    UserInfo.fillForm();
}

function showNoBirthInfo() {
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="no-birth-info">
                <p>请先完成基础八字排盘，获取生辰信息</p>
                <p><a href="pan.html">前往基础八字排盘 →</a></p>
            </div>
        `;
    }
}

async function queryRizhuLiujiazi(solar_date, solar_time, gender) {
    const resultDiv = document.getElementById('result');
    if (!resultDiv) return;
    
    resultDiv.innerHTML = '<div class="loading">查询中...</div>';

    try {
        // 调用日元-六十甲子API
        const response = await api.post('/bazi/rizhu-liujiazi', {
            solar_date,
            solar_time,
            gender
        });

        if (response.success && response.data) {
            displayRizhuResult(response.data);
            hasResult = true;
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        console.error('查询失败:', error);
        resultDiv.innerHTML = `<div class="error">${error.message || '查询失败，请稍后重试'}</div>`;
    }
}

function displayRizhuResult(data) {
    const resultDiv = document.getElementById('result');
    if (!resultDiv) return;
    
    let html = '';
    
    // 显示日柱信息卡片
    html += '<div class="card">';
    html += '<div class="card-header">';
    html += '<h2 class="card-title">日元-六十甲子解析</h2>';
    html += '</div>';
    html += '<div class="card-body">';
    
    // 日柱基本信息
    html += '<div style="margin-bottom: 20px;">';
    html += `<p><strong>ID:</strong> ${data.id}</p>`;
    html += `<p><strong>日柱:</strong> ${data.rizhu}</p>`;
    html += '</div>';
    
    // 解析内容（支持格式显示）
    html += '<div class="analysis-content">';
    // 将解析内容按段落分割并格式化
    const analysis = data.analysis || '';
    // 处理【】标记的标题
    const formattedAnalysis = analysis
        .replace(/【([^】]+)】/g, '<h3>【$1】</h3>')
        .replace(/\n/g, '<br>');
    html += formattedAnalysis;
    html += '</div>';
    
    html += '</div>';
    html += '</div>';
    
    resultDiv.innerHTML = html;
}

