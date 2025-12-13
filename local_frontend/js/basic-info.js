/**
 * 基本信息页面逻辑
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('basicInfoForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingSection = document.getElementById('loadingSection');
    const errorMessage = document.getElementById('errorMessage');
    const resultSection = document.getElementById('resultSection');

    // 检查必要的元素是否存在
    if (!form || !submitBtn || !loadingSection || !errorMessage || !resultSection) {
        console.error('页面元素未找到，请检查 HTML 结构');
        return;
    }

    // 表单提交处理
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // 获取表单数据
        const solarDate = document.getElementById('solar_date').value;
        const solarTime = document.getElementById('solar_time').value;
        const gender = document.getElementById('gender').value;
        const name = document.getElementById('name').value || '';
        const location = document.getElementById('location').value || '';

        // 验证输入
        if (!solarDate || !solarTime || !gender) {
            showError('请填写完整的出生信息');
            return;
        }

        // 显示加载状态
        showLoading();
        hideError();
        hideResult();

        try {
            // 调用 API
            const result = await api.post('/bazi/interface', {
                solar_date: solarDate,
                solar_time: solarTime,
                gender: gender,
                name: name,
                location: location
            });

            // 处理响应
            console.log('API 响应:', result);
            if (result && result.success && result.data) {
                displayBasicInfo(result.data);
            } else if (result && result.data) {
                // 如果直接返回数据，没有 success 字段
                displayBasicInfo(result.data);
            } else {
                showError(result?.error || result?.message || result?.detail || '查询失败，请稍后重试');
            }
        } catch (error) {
            console.error('查询基本信息失败:', error);
            showError('查询失败: ' + (error.message || '未知错误'));
        } finally {
            hideLoading();
        }
    });

    // 显示加载状态
    function showLoading() {
        loadingSection.style.display = 'block';
        submitBtn.disabled = true;
    }

    // 隐藏加载状态
    function hideLoading() {
        loadingSection.style.display = 'none';
        submitBtn.disabled = false;
    }

    // 显示错误信息
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    // 隐藏错误信息
    function hideError() {
        errorMessage.style.display = 'none';
    }

    // 隐藏结果
    function hideResult() {
        resultSection.classList.remove('active');
    }

    // 显示基本信息
    function displayBasicInfo(data) {
        // 处理嵌套数据结构，转换为扁平结构
        const flatData = flattenData(data);
        
        // 显示基本信息卡片
        displayBasicInfoCards(flatData);
        
        // 显示四柱信息
        displayBaziPillars(flatData);
        
        // 显示详细信息
        displayDetailInfo(flatData);
        
        // 显示结果区域
        resultSection.classList.add('active');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 将嵌套数据转换为扁平结构
    function flattenData(data) {
        // 如果已经是扁平结构，直接返回
        if (data.name || data.solar_date) {
            return data;
        }

        // 处理嵌套结构
        const flat = {};
        
        // 基本信息
        if (data.basic_info) {
            Object.assign(flat, data.basic_info);
        }
        
        // 四柱信息
        if (data.bazi_pillars) {
            flat.year_stem_branch = data.bazi_pillars.year || '';
            flat.month_stem_branch = data.bazi_pillars.month || '';
            flat.day_stem_branch = data.bazi_pillars.day || '';
            flat.hour_stem_branch = data.bazi_pillars.hour || '';
        }
        
        // 占星信息
        if (data.astrology) {
            flat.zodiac = data.astrology.zodiac || '';
            flat.constellation = data.astrology.constellation || '';
            flat.mansion = data.astrology.mansion || '';
            flat.bagua = data.astrology.bagua || '';
        }
        
        // 宫位信息
        if (data.palaces) {
            if (data.palaces.life_palace) {
                flat.life_palace = data.palaces.life_palace.ganzhi || '';
                flat.life_palace_nayin = data.palaces.life_palace.nayin || '';
            }
            if (data.palaces.body_palace) {
                flat.body_palace = data.palaces.body_palace.ganzhi || '';
                flat.body_palace_nayin = data.palaces.body_palace.nayin || '';
            }
            if (data.palaces.fetal_origin) {
                flat.fetal_origin = data.palaces.fetal_origin.ganzhi || '';
                flat.fetal_origin_nayin = data.palaces.fetal_origin.nayin || '';
            }
            if (data.palaces.fetal_breath) {
                flat.fetal_breath = data.palaces.fetal_breath.ganzhi || '';
                flat.fetal_breath_nayin = data.palaces.fetal_breath.nayin || '';
            }
        }
        
        // 节气信息
        if (data.solar_terms) {
            flat.current_jieqi_name = data.solar_terms.current_jieqi || '';
            flat.current_jieqi_time = data.solar_terms.current_jieqi_time || '';
            flat.next_jieqi_name = data.solar_terms.next_jieqi || '';
            flat.next_jieqi_time = data.solar_terms.next_jieqi_time || '';
            flat.days_to_current = data.solar_terms.days_to_current || 0;
            flat.days_to_next = data.solar_terms.days_to_next || 0;
        }
        
        // 其他信息
        if (data.other_info) {
            flat.commander = data.other_info.commander_element || '';
            flat.void_emptiness = data.other_info.void_emptiness || '';
            flat.day_master = data.other_info.day_master || '';
        }
        
        // 保留原始数据中的其他字段
        Object.keys(data).forEach(key => {
            if (!['basic_info', 'bazi_pillars', 'astrology', 'palaces', 'solar_terms', 'other_info'].includes(key)) {
                flat[key] = data[key];
            }
        });
        
        return flat;
    }

    // 显示基本信息卡片
    function displayBasicInfoCards(data) {
        const grid = document.getElementById('basicInfoGrid');
        if (!grid) {
            console.error('基本信息网格元素未找到');
            return;
        }
        grid.innerHTML = '';

        // 基本信息卡片
        const basicCard = createInfoCard('基本信息', [
            { label: '姓名', value: data.name || '未填写' },
            { label: '性别', value: data.gender || '未知' },
            { label: '阳历日期', value: data.solar_date || '未知' },
            { label: '阳历时间', value: data.solar_time || '未知' },
            { label: '农历日期', value: data.lunar_date || '未知' },
            { label: '出生地点', value: data.location || '未知' }
        ]);
        grid.appendChild(basicCard);

        // 生肖星座卡片
        const zodiacCard = createInfoCard('生肖星座', [
            { label: '生肖', value: data.zodiac || '未知' },
            { label: '星座', value: data.constellation || '未知' },
            { label: '星宿', value: data.mansion || '未知' }
        ]);
        grid.appendChild(zodiacCard);

        // 命宫身宫卡片
        const palaceCard = createInfoCard('命宫身宫', [
            { 
                label: '命宫', 
                value: data.life_palace || '未知',
                badge: data.life_palace_nayin 
            },
            { 
                label: '身宫', 
                value: data.body_palace || '未知',
                badge: data.body_palace_nayin 
            }
        ]);
        grid.appendChild(palaceCard);

        // 胎元胎息卡片
        const fetalCard = createInfoCard('胎元胎息', [
            { 
                label: '胎元', 
                value: data.fetal_origin || '未知',
                badge: data.fetal_origin_nayin 
            },
            { 
                label: '胎息', 
                value: data.fetal_breath || '未知',
                badge: data.fetal_breath_nayin 
            }
        ]);
        grid.appendChild(fetalCard);

        // 命卦卡片
        if (data.bagua) {
            const baguaCard = createInfoCard('命卦', [
                { label: '命卦', value: data.bagua, highlight: true }
            ]);
            grid.appendChild(baguaCard);
        }

        // 空亡卡片
        if (data.void_emptiness) {
            const voidCard = createInfoCard('空亡', [
                { label: '空亡', value: data.void_emptiness }
            ]);
            grid.appendChild(voidCard);
        }

        // 日主属性卡片
        if (data.day_master) {
            const dayMasterCard = createInfoCard('日主属性', [
                { label: '日主', value: data.day_master, highlight: true }
            ]);
            grid.appendChild(dayMasterCard);
        }
    }

    // 显示四柱信息
    function displayBaziPillars(data) {
        const section = document.getElementById('baziPillarsSection');
        const grid = document.getElementById('baziPillarsGrid');
        if (!section || !grid) {
            console.error('四柱信息元素未找到');
            return;
        }
        grid.innerHTML = '';

        // 尝试从格式化文本中获取纳音信息
        const getNayin = (pillarValue) => {
            if (!pillarValue) return '';
            // 这里可以根据需要从其他数据源获取纳音信息
            // 暂时返回空，如果需要可以扩展
            return '';
        };

        const pillars = [
            { label: '年柱', value: data.year_stem_branch, nayin: getNayin(data.year_stem_branch) },
            { label: '月柱', value: data.month_stem_branch, nayin: getNayin(data.month_stem_branch) },
            { label: '日柱', value: data.day_stem_branch, nayin: getNayin(data.day_stem_branch) },
            { label: '时柱', value: data.hour_stem_branch, nayin: getNayin(data.hour_stem_branch) }
        ];

        let hasPillars = false;
        pillars.forEach(pillar => {
            if (pillar.value) {
                hasPillars = true;
                const pillarCard = document.createElement('div');
                pillarCard.className = 'pillar-card';
                pillarCard.innerHTML = `
                    <div class="pillar-label">${pillar.label}</div>
                    <div class="pillar-value">${pillar.value}</div>
                    ${pillar.nayin ? `<div class="pillar-nayin">${pillar.nayin}</div>` : ''}
                `;
                grid.appendChild(pillarCard);
            }
        });

        if (hasPillars) {
            section.style.display = 'block';
        } else {
            section.style.display = 'none';
        }
    }

    // 显示详细信息
    function displayDetailInfo(data) {
        const grid = document.getElementById('detailInfoGrid');
        if (!grid) {
            console.error('详细信息网格元素未找到');
            return;
        }
        grid.innerHTML = '';

        // 节气信息
        if (data.current_jieqi_name || data.next_jieqi_name) {
            const jieqiCard = createInfoCard('节气信息', [
                { label: '当前节气', value: data.current_jieqi_name || '未知' },
                { label: '下个节气', value: data.next_jieqi_name || '未知' },
                { label: '距当前节气', value: formatJieqiTime(data.days_to_current, data.hours_to_current) },
                { label: '距下个节气', value: formatJieqiTime(data.days_to_next, data.hours_to_next) }
            ]);
            grid.appendChild(jieqiCard);
        }

        // 地理位置信息
        if (data.latitude || data.longitude) {
            const locationCard = createInfoCard('地理位置', [
                { label: '纬度', value: data.latitude ? data.latitude.toFixed(2) : '未知' },
                { label: '经度', value: data.longitude ? data.longitude.toFixed(2) : '未知' }
            ]);
            grid.appendChild(locationCard);
        }

        // 其他信息（如果有）
        const otherInfo = [];
        if (data.commander) {
            otherInfo.push({ label: '司令', value: data.commander });
        }
        if (data.lunar_date_info) {
            const lunarInfo = data.lunar_date_info;
            if (lunarInfo.year) otherInfo.push({ label: '农历年', value: lunarInfo.year });
            if (lunarInfo.month) otherInfo.push({ label: '农历月', value: lunarInfo.month });
            if (lunarInfo.day) otherInfo.push({ label: '农历日', value: lunarInfo.day });
        }

        if (otherInfo.length > 0) {
            const otherCard = createInfoCard('其他信息', otherInfo);
            grid.appendChild(otherCard);
        }
    }

    // 创建信息卡片
    function createInfoCard(title, items) {
        const card = document.createElement('div');
        card.className = 'info-card';
        
        const titleEl = document.createElement('div');
        titleEl.className = 'info-card-title';
        titleEl.textContent = title;
        card.appendChild(titleEl);

        items.forEach(item => {
            const itemEl = document.createElement('div');
            itemEl.className = 'info-item';
            
            const labelEl = document.createElement('span');
            labelEl.className = 'info-label';
            labelEl.textContent = item.label;
            
            const valueEl = document.createElement('span');
            valueEl.className = item.highlight ? 'info-value highlight' : 'info-value';
            valueEl.textContent = item.value || '未知';
            
            if (item.badge) {
                const badgeEl = document.createElement('span');
                badgeEl.className = 'nayin-badge';
                badgeEl.textContent = item.badge;
                valueEl.appendChild(badgeEl);
            }
            
            itemEl.appendChild(labelEl);
            itemEl.appendChild(valueEl);
            card.appendChild(itemEl);
        });

        return card;
    }

    // 格式化节气时间
    function formatJieqiTime(days, hours) {
        if (days === undefined && hours === undefined) {
            return '未知';
        }
        const parts = [];
        if (days !== undefined && days > 0) {
            parts.push(`${days}天`);
        }
        if (hours !== undefined && hours > 0) {
            parts.push(`${hours}小时`);
        }
        return parts.length > 0 ? parts.join(' ') : '0';
    }
});
