// 大运流年流月时间轴渲染（按照 FateTell 截图样式）

console.log('fortune-timeline.js 开始加载');

// 获取五行对应的CSS类名（展示逻辑，合理）
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

// ✅ 删除五行判断函数（业务逻辑已移到后端）
// 天干地支到五行的映射现在由后端API返回，前端直接使用 item.stem.wuxing 和 item.branch.wuxing

// 渲染大运时间轴表格
function renderDayunTimeline(dayunData) {
    const table = document.getElementById('dayunTable');
    if (!table || !dayunData || !dayunData.list) {
        console.error('renderDayunTimeline: 缺少数据', { table, dayunData });
        return;
    }
    
    // 过滤掉无效数据（ganzhi为空且不是小运的情况）
    const validList = dayunData.list.filter(item => {
        // 保留有小运标记的，或者有有效ganzhi的
        return (item.stem?.char === '小运') || (item.ganzhi && item.ganzhi.length >= 2);
    });
    
    if (validList.length === 0) {
        table.innerHTML = '<tbody><tr><td colspan="100%">暂无数据</td></tr></tbody>';
        return;
    }
    
    let html = '<thead><tr>';
    html += '<th>大运</th>';
    
    // 表头：年份
    validList.forEach(item => {
        if (item.year_range) {
            html += `<th>${item.year_range.start || ''}</th>`;
        } else {
            html += `<th>-</th>`;
        }
    });
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // 年龄行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        // ✅ 修复：判断是否是小运
        const isXiaoyun = item.stem?.char === '小运' || item.stem === '小运';
        const ageRange = item.age_range || {};
        
        let ageText = '';
        if (isXiaoyun) {
            // 小运：显示年龄范围，如 "0-1岁" 或 "1-1岁"
            if (ageRange.start !== undefined && ageRange.end !== undefined) {
                ageText = `${ageRange.start}-${ageRange.end}岁`;
            } else {
                ageText = item.age_display || '';
            }
        } else {
            // 其他大运：只显示开始年龄，如 "1"、"11"、"21" 等（不显示"岁"）
            if (ageRange.start !== undefined) {
                ageText = `${ageRange.start}`;
            } else if (item.age_display) {
                // 如果 age_display 是 "1岁" 格式，提取数字
                const match = item.age_display.match(/^(\d+)/);
                ageText = match ? match[1] : item.age_display;
            } else {
                ageText = '';
            }
        }
        html += `<td class="timeline-age">${ageText}</td>`;
    });
    html += '</tr>';
    
    // 小运行（如果有）
    html += '<tr>';
    html += '<th>小运</th>';
    validList.forEach(item => {
        // 检查是否是小运
        if (item.stem?.char === '小运') {
            html += `<td>小运</td>`;
        } else {
            html += `<td>-</td>`;
        }
    });
    html += '</tr>';
    
    // 大运行（天干地支）
    html += '<tr>';
    html += '<th>运</th>';
    validList.forEach((item, idx) => {
        const isCurrent = item.is_current;
        const ganzhi = item.ganzhi || '';
        const dayunIndex = item.index;
        const isSelected = window.currentData?.selectedDayun?.index === dayunIndex;
        
        // ✅ 修复：如果是小运，显示"小运"文字，并且可以点击选中
        const isXiaoyun = item.stem?.char === '小运' || item.stem === '小运';
        
        if (isXiaoyun) {
            // 小运时，显示"小运"文字，并且可以点击选中
            const clickClass = isSelected ? 'timeline-selected' : '';
            const cursorClass = 'timeline-clickable';
            
            html += `<td class="timeline-dayun-cell ${isCurrent ? 'timeline-current' : ''} ${clickClass} ${cursorClass}" 
                         data-dayun-index="${dayunIndex}" 
                         onclick="selectDayunByIndex(${dayunIndex})">`;
            html += `<div class="timeline-ganzhi">小运</div>`;
            html += `</td>`;
            return;
        }
        
        // 跳过无效数据（但不是小运的情况）
        if (!ganzhi || ganzhi.length < 2) {
            html += `<td class="${isCurrent ? 'timeline-current' : ''}">-</td>`;
            return;
        }
        
        const stem = item.stem?.char || ganzhi[0] || '';
        const branch = item.branch?.char || ganzhi[1] || '';
        // ✅ 使用后端返回的五行属性（业务逻辑在后端）
        const stemWuxing = item.stem?.wuxing || '';
        const branchWuxing = item.branch?.wuxing || '';
        
        // 添加点击事件和选中样式
        const clickClass = isSelected ? 'timeline-selected' : '';
        const cursorClass = 'timeline-clickable';
        
        html += `<td class="timeline-dayun-cell ${isCurrent ? 'timeline-current' : ''} ${clickClass} ${cursorClass}" 
                     data-dayun-index="${dayunIndex}" 
                     onclick="selectDayunByIndex(${dayunIndex})">`;
        html += `<div class="timeline-ganzhi">`;
        if (stem && stem !== '小运') {
            html += `<div class="timeline-ganzhi-item">`;
            html += `<div class="stem-circle ${getWuxingClass(stemWuxing)}">${stem}</div>`;
            html += `</div>`;
        }
        if (branch) {
            html += `<div class="timeline-ganzhi-item">`;
            html += `<div class="branch-circle ${getWuxingClass(branchWuxing)}">${branch}</div>`;
            html += `</div>`;
        }
        if (item.ten_gods) {
            html += `<div class="timeline-term">${item.ten_gods}</div>`;
        }
        html += `</div>`;
        html += `</td>`;
    });
    html += '</tr>';
    
    // ✅ 新增：十神简称行
    html += '<tr>';
    html += '<th>十神</th>';
    validList.forEach(item => {
        const shishenCombined = item.shishen_combined || '';
        html += `<td class="timeline-term" style="color: #dc3545; font-weight: bold;">${shishenCombined || '-'}</td>`;
    });
    html += '</tr>';
    
    html += '</tbody>';
    table.innerHTML = html;
}

// 渲染流年时间轴表格
function renderLiunianTimeline(liunianData) {
    const table = document.getElementById('liunianTable');
    if (!table || !liunianData || !liunianData.list) {
        console.error('renderLiunianTimeline: 缺少数据', { table, liunianData });
        if (table) {
            table.innerHTML = '<tbody><tr><td colspan="100%">暂无数据</td></tr></tbody>';
        }
        return;
    }
    
    // 过滤有效数据
    const validList = liunianData.list.filter(item => item.year && item.ganzhi);
    
    if (validList.length === 0) {
        table.innerHTML = '<tbody><tr><td colspan="100%">暂无数据</td></tr></tbody>';
        return;
    }
    
    console.log('渲染流年数据，数量:', validList.length);
    console.log('当前选中的流年:', window.currentData?.selectedLiunian?.year);
    
    let html = '<thead><tr>';
    html += '<th>流年</th>';
    
    // 表头：年份
    validList.forEach(item => {
        html += `<th>${item.year || ''}</th>`;
    });
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // 生肖行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const zodiac = item.zodiac || '';
        html += `<td class="timeline-age">${zodiac}年</td>`;
    });
    html += '</tr>';
    
    // 天干行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const isCurrent = item.is_current;
        const year = item.year;
        const isSelected = window.currentData?.selectedLiunian?.year === year;
        const stem = item.stem?.char || (item.ganzhi ? item.ganzhi[0] : '');
        // ✅ 使用后端返回的五行属性（业务逻辑在后端）
        const stemWuxing = item.stem?.wuxing || '';
        
        const clickClass = isSelected ? 'timeline-selected' : '';
        const cursorClass = 'timeline-clickable';
        
        html += `<td class="timeline-liunian-cell ${isCurrent ? 'timeline-current' : ''} ${clickClass} ${cursorClass}" 
                     data-year="${year}" 
                     onclick="selectLiunianByYear(${year})">`;
        if (stem) {
            html += `<div class="stem-circle ${getWuxingClass(stemWuxing)}">${stem}</div>`;
        }
        html += `</td>`;
    });
    html += '</tr>';
    
    // 地支行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const isCurrent = item.is_current;
        const year = item.year;
        const isSelected = window.currentData?.selectedLiunian?.year === year;
        const branch = item.branch?.char || (item.ganzhi ? item.ganzhi[1] : '');
        // ✅ 使用后端返回的五行属性（业务逻辑在后端）
        const branchWuxing = item.branch?.wuxing || '';
        
        const clickClass = isSelected ? 'timeline-selected' : '';
        const cursorClass = 'timeline-clickable';
        
        html += `<td class="timeline-liunian-cell ${isCurrent ? 'timeline-current' : ''} ${clickClass} ${cursorClass}" 
                     data-year="${year}" 
                     onclick="selectLiunianByYear(${year})">`;
        if (branch) {
            html += `<div class="branch-circle ${getWuxingClass(branchWuxing)}">${branch}</div>`;
        }
        html += `</td>`;
    });
    html += '</tr>';
    
    // 十神行（全称）
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const tenGods = item.ten_gods || '';
        html += `<td class="timeline-term">${tenGods}</td>`;
    });
    html += '</tr>';
    
    // ✅ 新增：十神简称行（红色字）
    html += '<tr>';
    html += '<th>十神</th>';
    validList.forEach(item => {
        const shishenCombined = item.shishen_combined || '';
        html += `<td class="timeline-term" style="color: #dc3545; font-weight: bold;">${shishenCombined || '-'}</td>`;
    });
    html += '</tr>';
    
    // ✅ 新增：小运行
    html += '<tr>';
    html += '<th>小运</th>';
    validList.forEach(item => {
        const xiaoyunGanzhi = item.xiaoyun_ganzhi || '';
        html += `<td class="timeline-term">${xiaoyunGanzhi || '-'}</td>`;
    });
    html += '</tr>';
    
    // 关系行
    html += '<tr>';
    html += '<th>关系</th>';
    validList.forEach(item => {
        const relations = item.relations || [];
        let relationsText = '-';
        
        if (Array.isArray(relations) && relations.length > 0) {
            // 过滤并提取有效的关系
            const validRelations = relations
                .filter(rel => {
                    // 过滤掉 null、undefined、空字符串
                    if (!rel) return false;
                    // 如果是对象，必须有 type 或 description
                    if (typeof rel === 'object') {
                        return rel.type || rel.description;
                    }
                    // 如果是字符串，必须非空
                    if (typeof rel === 'string') {
                        return rel.trim().length > 0;
                    }
                    return false;
                })
                .map(rel => {
                    // 提取关系文本
                    if (typeof rel === 'string') {
                        return rel.trim();
                    } else if (rel && typeof rel === 'object') {
                        // 优先使用 type，其次使用 description
                        return (rel.type || rel.description || '').trim();
                    }
                    return '';
                })
                .filter(text => text.length > 0); // 再次过滤空字符串
            
            if (validRelations.length > 0) {
                relationsText = validRelations.join('、');
            }
        }
        
        html += `<td class="timeline-relations">${relationsText}</td>`;
    });
    html += '</tr>';
    
    html += '</tbody>';
    table.innerHTML = html;
}

// 点击大运（通过索引）
function selectDayunByIndex(dayunIndex) {
    console.log('点击大运，索引:', dayunIndex);
    // ✅ 修复：直接调用全局函数，确保函数存在
    if (typeof window.selectDayun === 'function') {
        window.selectDayun(dayunIndex);
    } else if (typeof selectDayun === 'function') {
        selectDayun(dayunIndex);
    } else {
        console.error('selectDayun 函数不存在，尝试延迟调用');
        // 延迟重试，等待 fortune.js 加载完成
        setTimeout(() => {
            if (typeof window.selectDayun === 'function') {
                window.selectDayun(dayunIndex);
            } else {
                console.error('selectDayun 函数仍然不存在');
            }
        }, 100);
    }
}

// 点击流年（通过年份）
function selectLiunianByYear(year) {
    console.log('点击流年，年份:', year);
    // ✅ 修复：直接调用全局函数，确保函数存在
    if (typeof window.selectLiunian === 'function') {
        window.selectLiunian(year);
    } else if (typeof selectLiunian === 'function') {
        selectLiunian(year);
    } else {
        console.error('selectLiunian 函数不存在，尝试延迟调用');
        // 延迟重试，等待 fortune.js 加载完成
        setTimeout(() => {
            if (typeof window.selectLiunian === 'function') {
                window.selectLiunian(year);
            } else {
                console.error('selectLiunian 函数仍然不存在');
            }
        }, 100);
    }
}

// 将函数暴露到全局（确保在任何情况下都可以访问）
// ✅ 修复：立即暴露到全局，确保 onclick 事件可以访问
window.selectDayunByIndex = selectDayunByIndex;
window.selectLiunianByYear = selectLiunianByYear;

console.log('fortune-timeline.js 函数已暴露到全局:', {
    selectDayunByIndex: typeof window.selectDayunByIndex,
    selectLiunianByYear: typeof window.selectLiunianByYear
});

// 渲染流月时间轴表格
function renderLiuyueTimeline(liuyueData) {
    const table = document.getElementById('liuyueTable');
    if (!table || !liuyueData || !liuyueData.list) {
        console.error('renderLiuyueTimeline: 缺少数据', { table, liuyueData });
        if (table) {
            table.innerHTML = '<tbody><tr><td colspan="100%">暂无数据</td></tr></tbody>';
        }
        return;
    }
    
    // 过滤有效数据
    const validList = liuyueData.list.filter(item => item.solar_term && item.ganzhi);
    
    if (validList.length === 0) {
        table.innerHTML = '<tbody><tr><td colspan="100%">暂无数据</td></tr></tbody>';
        return;
    }
    
    console.log('渲染流月数据，数量:', validList.length);
    console.log('第一个流月数据示例:', validList[0]);
    
    let html = '<thead><tr>';
    html += '<th>流月</th>';
    
    // 表头：节气
    validList.forEach(item => {
        html += `<th>${item.solar_term || ''}</th>`;
    });
    html += '</tr></thead>';
    
    html += '<tbody>';
    
    // 日期行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        html += `<td class="timeline-age">${item.term_date || ''}</td>`;
    });
    html += '</tr>';
    
    // 天干行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const isCurrent = item.is_current;
        // ✅ 修复：优先使用 stem.char，如果没有则从 ganzhi 提取
        const stem = item.stem?.char || (item.stem && typeof item.stem === 'string' ? item.stem : '') || (item.ganzhi && item.ganzhi.length >= 1 ? item.ganzhi[0] : '');
        // ✅ 使用后端返回的五行属性（业务逻辑在后端）
        const stemWuxing = item.stem?.wuxing || '';
        
        html += `<td class="${isCurrent ? 'timeline-current' : ''}">`;
        if (stem) {
            html += `<div class="stem-circle ${getWuxingClass(stemWuxing)}">${stem}</div>`;
        }
        html += `</td>`;
    });
    html += '</tr>';
    
    // 地支行
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const isCurrent = item.is_current;
        // ✅ 修复：优先使用 branch.char，如果没有则从 ganzhi 提取
        const branch = item.branch?.char || (item.branch && typeof item.branch === 'string' ? item.branch : '') || (item.ganzhi && item.ganzhi.length >= 2 ? item.ganzhi[1] : '');
        // ✅ 使用后端返回的五行属性（业务逻辑在后端）
        const branchWuxing = item.branch?.wuxing || '';
        
        html += `<td class="${isCurrent ? 'timeline-current' : ''}">`;
        if (branch) {
            html += `<div class="branch-circle ${getWuxingClass(branchWuxing)}">${branch}</div>`;
        }
        html += `</td>`;
    });
    html += '</tr>';
    
    // 十神行（全称）
    html += '<tr>';
    html += '<th></th>';
    validList.forEach(item => {
        const tenGods = item.ten_gods || '';
        html += `<td class="timeline-term">${tenGods}</td>`;
    });
    html += '</tr>';
    
    // ✅ 新增：十神简称行（红色字）
    html += '<tr>';
    html += '<th>十神</th>';
    validList.forEach(item => {
        const shishenCombined = item.shishen_combined || '';
        html += `<td class="timeline-term" style="color: #dc3545; font-weight: bold;">${shishenCombined || '-'}</td>`;
    });
    html += '</tr>';
    
    html += '</tbody>';
    table.innerHTML = html;
}


// ✅ 渲染细盘表格
function renderXipanTable(data) {
    const table = document.getElementById('xipanTable');
    if (!table || !data) {
        console.error('renderXipanTable: 缺少数据', { table, data });
        return;
    }
    
    // 获取选中的流年和大运（或小运）
    // ✅ 修复：优先使用 selectedXXX（用户点击选中的），没有才用 current（当前的）
    const selectedLiunian = data.selectedLiunian || data.liunian?.current;
    const selectedDayun = data.selectedDayun || data.dayun?.current;
    const pillars = data.pillars || {};
    
    console.log('=== 细盘渲染调试 ===');
    console.log('data.selectedDayun:', data.selectedDayun);
    console.log('data.dayun?.current:', data.dayun?.current);
    console.log('最终选中的大运:', selectedDayun);
    console.log('大运干支:', selectedDayun?.stem?.char, selectedDayun?.branch?.char);
    console.log('大运详细信息:', {
        nayin: selectedDayun?.nayin,
        hidden_stems: selectedDayun?.hidden_stems,
        main_star: selectedDayun?.main_star,
        star_fortune: selectedDayun?.star_fortune,
        self_sitting: selectedDayun?.self_sitting,
        kongwang: selectedDayun?.kongwang,
        deities: selectedDayun?.deities
    });
    console.log('==================');
    
    // 判断是否是小运
    const isXiaoyun = selectedDayun && (selectedDayun.stem?.char === '小运' || selectedDayun.stem === '小运');
    
    // 构建表头：流年、大运（或小运）、年柱、月柱、日柱、时柱
    let html = '<thead><tr>';
    html += '<th>行</th>';
    html += '<th>流年</th>';
    html += `<th>${isXiaoyun ? '小运' : '大运'}</th>`;
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
        { name: '神煞', key: 'deities' },
        { name: '十神', key: 'shishen_combined' }  // ✅ 新增：十神简称行
    ];
    
    // 获取流年数据
    const liunianStem = selectedLiunian?.stem?.char || '';
    const liunianBranch = selectedLiunian?.branch?.char || '';
    
    // 获取大运（或小运）数据
    // ✅ 修复：小运后端数据不完整，前端只显示"小运"或"-"
    let dayunStem = '';
    let dayunBranch = '';
    
    if (isXiaoyun) {
        // 小运：后端没有返回详细数据，显示标识符
        dayunStem = '小运';
        dayunBranch = '';
        console.log('小运：后端数据不完整，显示"小运"标识');
    } else {
        // 正常大运：使用实际的天干地支
        dayunStem = selectedDayun?.stem?.char || '';
        dayunBranch = selectedDayun?.branch?.char || '';
    }
    
    // 渲染每一行
    rows.forEach(row => {
        html += '<tr>';
        html += `<th>${row.name}</th>`;
        
        // 流年列
        const liunianValue = getRowValue(selectedLiunian, row.key, liunianStem, liunianBranch);
        html += `<td>${liunianValue}</td>`;
        
        // 大运（或小运）列
        const dayunValue = getRowValue(selectedDayun, row.key, dayunStem, dayunBranch);
        html += `<td>${dayunValue}</td>`;
        
        // 四柱列
        ['year', 'month', 'day', 'hour'].forEach(pillarType => {
            const pillar = pillars[pillarType] || {};
            const pillarStem = pillar.stem || '';
            const pillarBranch = pillar.branch || '';
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
    
    // ✅ 修复：如果是小运（stem 为"小运"），所有详细信息都显示为"-"或"小运"
    const isXiaoyun = stem === '小运';
    
    switch (key) {
        case 'main_star':
            return isXiaoyun ? '-' : (item.main_star || '-');
        case 'stem':
            return stem || '-';
        case 'branch':
            return isXiaoyun ? '-' : (branch || '-');
        case 'hidden_stems':
            if (isXiaoyun) return '-';
            const hiddenStems = item.hidden_stems || [];
            return hiddenStems.length > 0 ? hiddenStems.join(' ') : '-';
        case 'star_fortune':
            return isXiaoyun ? '-' : (item.star_fortune || '-');
        case 'self_sitting':
            return isXiaoyun ? '-' : (item.self_sitting || '-');
        case 'kongwang':
            return isXiaoyun ? '-' : (item.kongwang || '-');
        case 'nayin':
            return isXiaoyun ? '-' : (item.nayin || '-');
        case 'deities':
            if (isXiaoyun) return '-';
            const deities = item.deities || [];
            return deities.length > 0 ? deities.join(' ') : '-';
        case 'shishen_combined':
            // ✅ 新增：十神简称（红色字显示）
            const shishenCombined = item.shishen_combined || '';
            return shishenCombined ? `<span style="color: #dc3545; font-weight: bold;">${shishenCombined}</span>` : '-';
        default:
            return '-';
    }
}
