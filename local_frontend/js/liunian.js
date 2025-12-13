// 流年逻辑
// 页面加载时填充用户信息
document.addEventListener('DOMContentLoaded', () => {
    UserInfo.fillForm();
});

document.getElementById('liunianForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<div class="loading">查询中...</div>';

    const solar_date = document.getElementById('solar_date').value;
    const solar_time = document.getElementById('solar_time').value;
    const gender = document.getElementById('gender').value;
    const start_year = document.getElementById('start_year').value;
    const end_year = document.getElementById('end_year').value;

    // 保存用户信息
    UserInfo.save(solar_date, solar_time, gender);

    try {
        const requestData = {
            solar_date,
            solar_time,
            gender
        };
        
        if (start_year && end_year) {
            requestData.year_range = {
                start: parseInt(start_year),
                end: parseInt(end_year)
            };
        }

        const response = await api.post('/bazi/liunian/display', requestData);

        if (response.success) {
            displayLiunianResult(response.liunian);
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
    }
});

function displayLiunianResult(liunian) {
    const resultDiv = document.getElementById('result');
    let html = '<div class="liunian-result">';
    
    // 当前流年
    if (liunian.current && liunian.current.year) {
        html += '<div class="section"><h2>当前流年</h2>';
        html += '<div class="liunian-item current">';
        html += `<div class="year">${liunian.current.year}</div>`;
        html += `<div class="ganzhi">${liunian.current.ganzhi || ''}</div>`;
        if (liunian.current.age !== undefined) {
            html += `<div class="age">${liunian.current.age}岁</div>`;
        }
        html += '</div></div>';
    }

    // 流年列表
    if (liunian.list && liunian.list.length > 0) {
        html += '<div class="section"><h2>流年序列</h2>';
        html += '<div class="liunian-list">';
        
        liunian.list.forEach(item => {
            if (!item.year) return;
            
            const isCurrent = item.is_current ? 'current' : '';
            html += `<div class="liunian-item ${isCurrent}">`;
            html += `<div class="year">${item.year}</div>`;
            html += `<div class="ganzhi">${item.ganzhi || ''}</div>`;
            if (item.age !== undefined) {
                html += `<div class="age">${item.age}岁</div>`;
            }
            if (item.age_display) {
                html += `<div class="age">${item.age_display}</div>`;
            }
            if (item.nayin) {
                html += `<div style="font-size: 12px; color: #999; margin-top: 5px;">${item.nayin}</div>`;
            }
            if (item.is_current) {
                html += `<div style="color: #28a745; font-weight: bold; margin-top: 5px;">当前</div>`;
            }
            html += '</div>';
        });
        
        html += '</div></div>';
    }

    html += '</div>';
    resultDiv.innerHTML = html;
}

