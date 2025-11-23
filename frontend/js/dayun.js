// 大运逻辑
// 页面加载时填充用户信息
document.addEventListener('DOMContentLoaded', () => {
    UserInfo.fillForm();
});

document.getElementById('dayunForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<div class="loading">查询中...</div>';

    const solar_date = document.getElementById('solar_date').value;
    const solar_time = document.getElementById('solar_time').value;
    const gender = document.getElementById('gender').value;
    const current_time = document.getElementById('current_time').value;

    // 保存用户信息
    UserInfo.save(solar_date, solar_time, gender);

    try {
        const requestData = {
            solar_date,
            solar_time,
            gender
        };
        
        if (current_time) {
            requestData.current_time = current_time;
        }

        const response = await api.post('/bazi/dayun/display', requestData);

        if (response.success) {
            displayDayunResult(response.dayun);
        } else {
            resultDiv.innerHTML = `<div class="error">${response.error || '查询失败'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">${error.message}</div>`;
    }
});

function displayDayunResult(dayun) {
    const resultDiv = document.getElementById('result');
    let html = '<div class="dayun-result">';
    
    // 起运和交运信息
    if (dayun.qiyun || dayun.jiaoyun) {
        html += '<div class="section"><h2>起运交运信息</h2>';
        if (dayun.qiyun) {
            html += `<p><strong>起运：</strong>${dayun.qiyun.age_display || dayun.qiyun.date || '-'}</p>`;
            if (dayun.qiyun.description) {
                html += `<p>${dayun.qiyun.description}</p>`;
            }
        }
        if (dayun.jiaoyun) {
            html += `<p><strong>交运：</strong>${dayun.jiaoyun.age_display || dayun.jiaoyun.date || '-'}</p>`;
            if (dayun.jiaoyun.description) {
                html += `<p>${dayun.jiaoyun.description}</p>`;
            }
        }
        html += '</div>';
    }

    // 当前大运
    if (dayun.current && dayun.current.ganzhi) {
        html += '<div class="section"><h2>当前大运</h2>';
        html += '<div class="dayun-item current">';
        html += `<h3>${dayun.current.ganzhi}</h3>`;
        html += '<div class="info">';
        if (dayun.current.age_range) {
            html += `<div class="info-item"><strong>年龄：</strong>${dayun.current.age_range.start}-${dayun.current.age_range.end}岁</div>`;
        }
        if (dayun.current.year_range) {
            html += `<div class="info-item"><strong>年份：</strong>${dayun.current.year_range.start}-${dayun.current.year_range.end}年</div>`;
        }
        if (dayun.current.nayin) {
            html += `<div class="info-item"><strong>纳音：</strong>${dayun.current.nayin}</div>`;
        }
        html += '</div></div></div>';
    }

    // 大运列表
    if (dayun.list && dayun.list.length > 0) {
        html += '<div class="section"><h2>大运序列</h2>';
        html += '<div class="dayun-list">';
        
        dayun.list.forEach(item => {
            if (!item.ganzhi) return;
            
            const isCurrent = item.is_current ? 'current' : '';
            html += `<div class="dayun-item ${isCurrent}">`;
            html += `<h3>第${item.index || 0}步：${item.ganzhi}</h3>`;
            html += '<div class="info">';
            if (item.age_range) {
                html += `<div class="info-item"><strong>年龄：</strong>${item.age_range.start}-${item.age_range.end}岁</div>`;
            }
            if (item.age_display) {
                html += `<div class="info-item"><strong>年龄显示：</strong>${item.age_display}</div>`;
            }
            if (item.year_range) {
                html += `<div class="info-item"><strong>年份：</strong>${item.year_range.start}-${item.year_range.end}年</div>`;
            }
            if (item.nayin) {
                html += `<div class="info-item"><strong>纳音：</strong>${item.nayin}</div>`;
            }
            if (item.is_current) {
                html += `<div class="info-item"><strong style="color: #28a745;">当前大运</strong></div>`;
            }
            html += '</div></div>';
        });
        
        html += '</div></div>';
    }

    html += '</div>';
    resultDiv.innerHTML = html;
}

