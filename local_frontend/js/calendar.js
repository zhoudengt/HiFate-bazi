/**
 * 万年历功能
 * 调用万年历API并渲染展示
 */

/**
 * 加载万年历数据
 * @param {string} date - 日期，格式：YYYY-MM-DD，默认为今天
 */
async function loadCalendar(date = null) {
    const calendarContainer = document.getElementById('calendarContainer');
    if (!calendarContainer) {
        console.error('万年历容器不存在');
        return;
    }

    // 显示加载状态
    calendarContainer.innerHTML = '<div class="calendar-loading">加载中...</div>';

    try {
        // 如果没有提供日期，使用今天
        if (!date) {
            const today = new Date();
            date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        }

        // 调用API
        const response = await api.post('/calendar/query', { date });
        
        if (response.success) {
            renderCalendar(response);
        } else {
            calendarContainer.innerHTML = `<div class="calendar-error">${response.error || '加载失败'}</div>`;
        }
    } catch (error) {
        console.error('加载万年历失败:', error);
        calendarContainer.innerHTML = `<div class="calendar-error">加载失败: ${error.message}</div>`;
    }
}

/**
 * 渲染万年历数据
 * @param {object} data - 万年历数据
 */
function renderCalendar(data) {
    const calendarContainer = document.getElementById('calendarContainer');
    if (!calendarContainer) {
        return;
    }

    const {
        solar_date,
        weekday,
        weekday_en,
        lunar_date,
        lunar_year,
        shengxiao,
        xingzuo,
        ganzhi,
        wuxing = [],
        nayin = [],
        yi = [],
        ji = [],
        luck_level,
        deities = {},
        chong_he_sha = {},
        xingxiu = {},
        pengzu = {},
        shensha = {},
        jiuxing = {},
        other = {},
        festivals = []
    } = data;

    // 构建HTML
    let html = `
        <div class="calendar-card">
            <div class="calendar-header">
                <h2 class="calendar-title">📅 万年历</h2>
                <input type="date" id="calendarDatePicker" class="calendar-date-picker" value="${data.date || ''}" onchange="loadCalendar(this.value)">
            </div>
            <div class="calendar-content">
                <!-- 日期区域 -->
                <div class="calendar-date-section">
                    <div class="calendar-solar-date">${solar_date || ''}</div>
                    <div class="calendar-weekday">${weekday || ''} / ${weekday_en || ''}</div>
                    <div class="calendar-lunar-date">${lunar_date || ''}</div>
                    <div class="calendar-extra-info">
                        ${shengxiao ? `<span class="info-tag shengxiao">🐍 ${shengxiao}年</span>` : ''}
                        ${xingzuo ? `<span class="info-tag xingzuo">⭐ ${xingzuo}座</span>` : ''}
                        ${other.jieqi ? `<span class="info-tag jieqi">🌿 ${other.jieqi}</span>` : ''}
                    </div>
                </div>

                <!-- 节日 -->
                ${festivals.length > 0 ? `
                <div class="calendar-festivals-section">
                    <div class="festivals-items">
                        ${festivals.map(f => `<span class="festival-tag">🎉 ${f}</span>`).join('')}
                    </div>
                </div>
                ` : ''}

                <!-- 干支八字 -->
                <div class="calendar-ganzhi-section">
                    <div class="section-title">干支八字</div>
                    <div class="ganzhi-grid">
                        <div class="ganzhi-item">
                            <span class="ganzhi-label">年柱</span>
                            <span class="ganzhi-value">${ganzhi?.year || ''}</span>
                            ${nayin[0] ? `<span class="nayin-value">${nayin[0]}</span>` : ''}
                        </div>
                        <div class="ganzhi-item">
                            <span class="ganzhi-label">月柱</span>
                            <span class="ganzhi-value">${ganzhi?.month || ''}</span>
                            ${nayin[1] ? `<span class="nayin-value">${nayin[1]}</span>` : ''}
                        </div>
                        <div class="ganzhi-item">
                            <span class="ganzhi-label">日柱</span>
                            <span class="ganzhi-value">${ganzhi?.day || ''}</span>
                            ${nayin[2] ? `<span class="nayin-value">${nayin[2]}</span>` : ''}
                        </div>
                        <div class="ganzhi-item">
                            <span class="ganzhi-label">时柱</span>
                            <span class="ganzhi-value">${ganzhi?.hour || ''}</span>
                            ${nayin[3] ? `<span class="nayin-value">${nayin[3]}</span>` : ''}
                        </div>
                    </div>
                    ${wuxing.length > 0 ? `
                    <div class="wuxing-row">
                        <span class="wuxing-label">五行：</span>
                        ${wuxing.map(wx => `<span class="wuxing-value">${wx}</span>`).join('')}
                    </div>
                    ` : ''}
                </div>
    `;

    // 宜忌信息
    if (yi.length > 0 || ji.length > 0) {
        html += `
            <div class="calendar-yiji-section">
                ${yi.length > 0 ? `
                    <div class="yi-section">
                        <div class="yiji-label yi-label">宜</div>
                        <div class="yiji-items">
                            ${yi.map(item => `<span class="yiji-item yi-item">${item}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
                ${ji.length > 0 ? `
                    <div class="ji-section">
                        <div class="yiji-label ji-label">忌</div>
                        <div class="yiji-items">
                            ${ji.map(item => `<span class="yiji-item ji-item">${item}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }

    // 吉凶等级
    if (luck_level) {
        html += `
            <div class="calendar-luck-section">
                <div class="luck-level ${luck_level.includes('凶') ? 'luck-bad' : luck_level.includes('吉') ? 'luck-good' : ''}">${luck_level}</div>
            </div>
        `;
    }

    // 神煞方位
    if (deities.xishen || deities.caishen || deities.fushen || deities.yanggui || deities.yingui) {
        html += `
            <div class="calendar-deities-section">
                <div class="section-title">神煞方位</div>
                <div class="deities-grid">
                    ${deities.xishen ? `<div class="deity-item"><span class="deity-label">喜神</span><span class="deity-value">${deities.xishen}</span></div>` : ''}
                    ${deities.caishen ? `<div class="deity-item"><span class="deity-label">财神</span><span class="deity-value">${deities.caishen}</span></div>` : ''}
                    ${deities.fushen ? `<div class="deity-item"><span class="deity-label">福神</span><span class="deity-value">${deities.fushen}</span></div>` : ''}
                    ${deities.yanggui ? `<div class="deity-item"><span class="deity-label">阳贵</span><span class="deity-value">${deities.yanggui}</span></div>` : ''}
                    ${deities.yingui ? `<div class="deity-item"><span class="deity-label">阴贵</span><span class="deity-value">${deities.yingui}</span></div>` : ''}
                </div>
            </div>
        `;
    }

    // 冲合煞
    if (chong_he_sha.chong || chong_he_sha.he || chong_he_sha.sha) {
        html += `
            <div class="calendar-chonghesha-section">
                <div class="section-title">冲合煞</div>
                <div class="chonghesha-grid">
                    ${chong_he_sha.chong ? `<div class="chonghesha-item"><span class="chonghesha-label">冲</span><span class="chonghesha-value chong-value">${chong_he_sha.chong}</span></div>` : ''}
                    ${chong_he_sha.he ? `<div class="chonghesha-item"><span class="chonghesha-label">合</span><span class="chonghesha-value he-value">${chong_he_sha.he}</span></div>` : ''}
                    ${chong_he_sha.sha ? `<div class="chonghesha-item"><span class="chonghesha-label">煞</span><span class="chonghesha-value sha-value">${chong_he_sha.sha}</span></div>` : ''}
                </div>
            </div>
        `;
    }

    // 吉神凶煞
    if ((shensha.jishen && shensha.jishen.length > 0) || (shensha.xiongsha && shensha.xiongsha.length > 0)) {
        html += `
            <div class="calendar-shensha-section">
                <div class="section-title">吉神凶煞</div>
                ${shensha.jishen && shensha.jishen.length > 0 ? `
                <div class="shensha-row jishen-row">
                    <span class="shensha-label jishen-label">吉神</span>
                    <div class="shensha-items">
                        ${shensha.jishen.map(s => `<span class="shensha-tag jishen-tag">${s}</span>`).join('')}
                    </div>
                </div>
                ` : ''}
                ${shensha.xiongsha && shensha.xiongsha.length > 0 ? `
                <div class="shensha-row xiongsha-row">
                    <span class="shensha-label xiongsha-label">凶煞</span>
                    <div class="shensha-items">
                        ${shensha.xiongsha.map(s => `<span class="shensha-tag xiongsha-tag">${s}</span>`).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    // 星宿信息
    if (xingxiu.name) {
        html += `
            <div class="calendar-xingxiu-section">
                <div class="section-title">星宿</div>
                <div class="xingxiu-info">
                    <div class="xingxiu-main">
                        <span class="xingxiu-name">${xingxiu.name}宿</span>
                        <span class="xingxiu-luck ${xingxiu.luck === '吉' ? 'luck-good' : xingxiu.luck === '凶' ? 'luck-bad' : ''}">${xingxiu.luck || ''}</span>
                        ${xingxiu.zheng ? `<span class="xingxiu-zheng">${xingxiu.zheng}</span>` : ''}
                        ${xingxiu.animal ? `<span class="xingxiu-animal">${xingxiu.animal}</span>` : ''}
                    </div>
                    ${xingxiu.song ? `<div class="xingxiu-song">${xingxiu.song}</div>` : ''}
                </div>
            </div>
        `;
    }

    // 彭祖百忌
    if (pengzu.gan || pengzu.zhi) {
        html += `
            <div class="calendar-pengzu-section">
                <div class="section-title">彭祖百忌</div>
                <div class="pengzu-items">
                    ${pengzu.gan ? `<div class="pengzu-item">${pengzu.gan}</div>` : ''}
                    ${pengzu.zhi ? `<div class="pengzu-item">${pengzu.zhi}</div>` : ''}
                </div>
            </div>
        `;
    }

    // 九星
    if (jiuxing.year || jiuxing.month || jiuxing.day) {
        html += `
            <div class="calendar-jiuxing-section">
                <div class="section-title">九星</div>
                <div class="jiuxing-grid">
                    ${jiuxing.year ? `<div class="jiuxing-item"><span class="jiuxing-label">年九星</span><span class="jiuxing-value">${jiuxing.year}</span></div>` : ''}
                    ${jiuxing.month ? `<div class="jiuxing-item"><span class="jiuxing-label">月九星</span><span class="jiuxing-value">${jiuxing.month}</span></div>` : ''}
                    ${jiuxing.day ? `<div class="jiuxing-item"><span class="jiuxing-label">日九星</span><span class="jiuxing-value">${jiuxing.day}</span></div>` : ''}
                </div>
            </div>
        `;
    }

    // 其他信息（六曜、建除、月相、物候）
    if (other.liuyao || other.zhixing || other.yuexiang || other.wuhou) {
        html += `
            <div class="calendar-other-section">
                <div class="section-title">其他</div>
                <div class="other-grid">
                    ${other.liuyao ? `<div class="other-item"><span class="other-label">六曜</span><span class="other-value">${other.liuyao}</span></div>` : ''}
                    ${other.zhixing ? `<div class="other-item"><span class="other-label">建除</span><span class="other-value">${other.zhixing}</span></div>` : ''}
                    ${other.yuexiang ? `<div class="other-item"><span class="other-label">月相</span><span class="other-value">${other.yuexiang}</span></div>` : ''}
                    ${other.hou ? `<div class="other-item"><span class="other-label">物候</span><span class="other-value">${other.hou}</span></div>` : ''}
                </div>
                ${other.wuhou ? `<div class="wuhou-desc">${other.wuhou}</div>` : ''}
            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;

    calendarContainer.innerHTML = html;
}

// 页面加载时延迟加载万年历（性能优化：避免阻塞页面渲染）
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('calendarContainer')) {
        // 使用 requestIdleCallback 延迟加载（浏览器空闲时执行）
        // 如果不支持，使用 setTimeout 作为降级方案
        if (window.requestIdleCallback) {
            requestIdleCallback(function() {
                loadCalendar();
            }, { timeout: 2000 }); // 最多等待2秒
        } else {
            // 降级方案：延迟500ms执行，让页面先渲染
            setTimeout(function() {
                loadCalendar();
            }, 500);
        }
    }
});
