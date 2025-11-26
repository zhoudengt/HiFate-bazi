// 办公桌风水分析 - 前端交互脚本

class DeskFengshuiAnalyzer {
    constructor() {
        this.apiBaseUrl = window.API_BASE_URL || 'http://localhost:8001';
        this.selectedImage = null;
        
        this.init();
    }
    
    init() {
        // 绑定事件
        this.bindEvents();
        
        console.log('✅ 办公桌风水分析器初始化成功');
    }
    
    bindEvents() {
        // 上传区域点击
        const uploadArea = document.getElementById('uploadArea');
        const imageInput = document.getElementById('imageInput');
        
        uploadArea.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-remove')) {
                imageInput.click();
            }
        });
        
        // 文件选择
        imageInput.addEventListener('change', (e) => {
            this.handleFileSelect(e);
        });
        
        // 拖拽上传
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.loadImage(files[0]);
            }
        });
        
        // 删除图片
        document.getElementById('btnRemove').addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeImage();
        });
        
        // 八字开关
        const useBazi = document.getElementById('useBazi');
        const baziForm = document.getElementById('baziForm');
        
        useBazi.addEventListener('change', () => {
            baziForm.style.display = useBazi.checked ? 'block' : 'none';
        });
        
        // 分析按钮
        document.getElementById('btnAnalyze').addEventListener('click', () => {
            this.analyze();
        });
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.loadImage(files[0]);
        }
    }
    
    loadImage(file) {
        // 验证文件类型
        if (!file.type.startsWith('image/')) {
            alert('请上传图片文件');
            return;
        }
        
        // 验证文件大小（最大10MB）
        if (file.size > 10 * 1024 * 1024) {
            alert('图片文件不能超过10MB');
            return;
        }
        
        this.selectedImage = file;
        
        // 显示预览
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImage').src = e.target.result;
            document.querySelector('.upload-prompt').style.display = 'none';
            document.getElementById('preview').style.display = 'block';
            document.getElementById('btnAnalyze').disabled = false;
        };
        reader.readAsDataURL(file);
    }
    
    removeImage() {
        this.selectedImage = null;
        document.getElementById('imageInput').value = '';
        document.getElementById('previewImage').src = '';
        document.querySelector('.upload-prompt').style.display = 'block';
        document.getElementById('preview').style.display = 'none';
        document.getElementById('btnAnalyze').disabled = true;
        document.getElementById('resultSection').style.display = 'none';
    }
    
    async analyze() {
        if (!this.selectedImage) {
            alert('请先上传照片');
            return;
        }
        
        // 准备数据
        const formData = new FormData();
        formData.append('image', this.selectedImage);
        
        const useBazi = document.getElementById('useBazi').checked;
        formData.append('use_bazi', useBazi);
        
        if (useBazi) {
            const solarDate = document.getElementById('solarDate').value;
            const solarTime = document.getElementById('solarTime').value;
            const gender = document.getElementById('gender').value;
            
            if (!solarDate || !solarTime) {
                alert('请填写完整的八字信息');
                return;
            }
            
            formData.append('solar_date', solarDate);
            formData.append('solar_time', solarTime);
            formData.append('gender', gender);
        }
        
        // 显示加载状态
        this.setLoading(true);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v2/desk-fengshui/analyze`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.displayResult(result.data);
            } else {
                throw new Error(result.error || '分析失败');
            }
            
        } catch (error) {
            console.error('分析失败:', error);
            alert(`分析失败: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        const btnAnalyze = document.getElementById('btnAnalyze');
        const btnText = btnAnalyze.querySelector('.btn-text');
        const btnLoading = btnAnalyze.querySelector('.btn-loading');
        
        if (loading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline-flex';
            btnAnalyze.disabled = true;
        } else {
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            btnAnalyze.disabled = false;
        }
    }
    
    displayResult(data) {
        // 显示结果区域
        document.getElementById('resultSection').style.display = 'block';
        
        // 滚动到结果区域
        setTimeout(() => {
            document.getElementById('resultSection').scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }, 100);
        
        // 显示警告信息（如果有）
        if (data.warning) {
            this.displayWarning(data.warning);
        }
        
        // 显示评分
        this.displayScore(data.score, data.summary);
        
        // 显示八字信息
        if (data.xishen || data.jishen) {
            document.getElementById('baziInfo').style.display = 'block';
            document.getElementById('xishen').textContent = data.xishen || '-';
            document.getElementById('jishen').textContent = data.jishen || '-';
        } else {
            document.getElementById('baziInfo').style.display = 'none';
        }
        
        // 显示检测到的物品
        this.displayItems(data.items || []);
        
        // 显示调整建议
        this.displaySuggestions('adjustments', data.adjustments || []);
        
        // 显示增加建议
        this.displaySuggestions('additions', data.additions || []);
        
        // 显示删除建议
        this.displaySuggestions('removals', data.removals || []);
    }
    
    displayWarning(warning) {
        // 在结果区域顶部显示警告
        const resultSection = document.getElementById('resultSection');
        const existingWarning = resultSection.querySelector('.warning-banner');
        if (existingWarning) {
            existingWarning.remove();
        }
        
        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-banner';
        warningDiv.innerHTML = `
            <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">⚠️</span>
                    <div>
                        <strong style="color: #856404;">检测功能受限</strong>
                        <p style="margin: 5px 0 0 0; color: #856404;">
                            ${warning}<br>
                            <small>建议联系管理员安装YOLO模型以获得更准确的物品检测。<br>
                            当前系统仍会根据风水原理为您提供完整的布局建议。</small>
                        </p>
                    </div>
                </div>
            </div>
        `;
        
        resultSection.insertBefore(warningDiv, resultSection.firstChild);
    }
    
    displayScore(score, summary) {
        // 更新评分数字
        const scoreValue = document.getElementById('scoreValue');
        this.animateNumber(scoreValue, 0, score, 1000);
        
        // 更新进度圆环
        const scoreCircle = document.getElementById('scoreCircle');
        const circumference = 408; // 2 * π * r (r=65)
        const offset = circumference - (score / 100) * circumference;
        scoreCircle.style.strokeDashoffset = offset;
        
        // 根据分数设置颜色
        if (score >= 90) {
            scoreCircle.style.stroke = '#4caf50';
        } else if (score >= 75) {
            scoreCircle.style.stroke = '#2196f3';
        } else if (score >= 60) {
            scoreCircle.style.stroke = '#ff9800';
        } else {
            scoreCircle.style.stroke = '#f44336';
        }
        
        // 更新总结
        document.getElementById('scoreDescription').textContent = summary;
        
        // 更新标题
        let level = '一般';
        if (score >= 90) level = '优秀';
        else if (score >= 75) level = '良好';
        else if (score < 60) level = '待改善';
        
        document.getElementById('scoreSummary').textContent = `办公桌风水布局：${level}`;
    }
    
    animateNumber(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.round(current);
        }, 16);
    }
    
    displayItems(items) {
        const grid = document.getElementById('itemsGrid');
        grid.innerHTML = '';
        
        if (items.length === 0) {
            grid.innerHTML = '<p style="color: #999;">未检测到物品</p>';
            return;
        }
        
        items.forEach(item => {
            const position = item.position || {};
            const itemEl = document.createElement('div');
            itemEl.className = 'item-tag';
            itemEl.innerHTML = `
                <div class="item-name">${item.label}</div>
                <div class="item-position">${position.relative_name || '未知位置'}</div>
                <div class="item-position" style="font-size: 0.8em; color: #999;">
                    ${position.bagua_name || ''}
                </div>
            `;
            grid.appendChild(itemEl);
        });
    }
    
    displaySuggestions(type, suggestions) {
        const cardId = type === 'adjustments' ? 'adjustmentsCard' :
                      type === 'additions' ? 'additionsCard' : 'removalsCard';
        const listId = type === 'adjustments' ? 'adjustmentsList' :
                      type === 'additions' ? 'additionsList' : 'removalsList';
        
        const card = document.getElementById(cardId);
        const list = document.getElementById(listId);
        
        if (suggestions.length === 0) {
            card.style.display = 'none';
            return;
        }
        
        card.style.display = 'block';
        list.innerHTML = '';
        
        suggestions.forEach(sugg => {
            const priority = sugg.priority || 'low';
            const item = document.createElement('div');
            item.className = `suggestion-item priority-${priority}`;
            
            let content = '';
            
            if (type === 'adjustments') {
                content = `
                    <div class="suggestion-header">
                        <span class="suggestion-title">${sugg.item_label || sugg.item}</span>
                        <span class="suggestion-badge badge-${priority}">
                            ${priority === 'high' ? '高优先级' : priority === 'medium' ? '中优先级' : '低优先级'}
                        </span>
                    </div>
                    <div class="suggestion-detail">
                        当前位置：${sugg.current_position} → 建议位置：${sugg.ideal_position}
                    </div>
                    <div class="suggestion-reason">${sugg.reason}</div>
                `;
            } else if (type === 'additions') {
                content = `
                    <div class="suggestion-header">
                        <span class="suggestion-title">建议增加：${sugg.item_label || sugg.item}</span>
                        <span class="suggestion-badge badge-${priority}">
                            ${sugg.element ? `五行：${sugg.element}` : '建议'}
                        </span>
                    </div>
                    <div class="suggestion-detail">
                        建议位置：${sugg.ideal_position || sugg.position}
                    </div>
                    <div class="suggestion-reason">${sugg.reason}</div>
                `;
            } else {
                content = `
                    <div class="suggestion-header">
                        <span class="suggestion-title">${sugg.item_label || sugg.item}</span>
                        <span class="suggestion-badge badge-high">不宜摆放</span>
                    </div>
                    <div class="suggestion-detail">
                        当前位置：${sugg.current_position}
                    </div>
                    <div class="suggestion-reason">${sugg.reason}</div>
                `;
            }
            
            item.innerHTML = content;
            list.appendChild(item);
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new DeskFengshuiAnalyzer();
});

