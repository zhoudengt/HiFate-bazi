// 面相分析V2前端逻辑

const FaceAnalysisV2 = {
    imageFile: null,
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        const uploadBox = document.getElementById('uploadBox');
        const imageInput = document.getElementById('imageInput');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        // 上传框点击
        uploadBox.addEventListener('click', () => {
            imageInput.click();
        });
        
        // 文件选择
        imageInput.addEventListener('change', (e) => {
            this.handleFileSelect(e);
        });
        
        // 分析按钮
        analyzeBtn.addEventListener('click', () => {
            this.analyzeImage();
        });
    },
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        this.imageFile = file;
        
        // 显示预览
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewImage = document.getElementById('previewImage');
            const placeholder = document.querySelector('.upload-placeholder');
            
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            placeholder.style.display = 'none';
        };
        reader.readAsDataURL(file);
        
        // 启用分析按钮
        document.getElementById('analyzeBtn').disabled = false;
    },
    
    // 将文件转换为 base64
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // 返回 base64 字符串（包含 data:image/xxx;base64, 前缀）
                resolve(reader.result);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    async analyzeImage() {
        if (!this.imageFile) {
            alert('请先上传照片');
            return;
        }
        
        // 获取分析选项
        const analysisTypes = Array.from(document.querySelectorAll('input[name="analysis"]:checked'))
            .map(cb => cb.value)
            .join(',');
        
        // 获取生辰信息
        const birthYear = document.getElementById('birthYear').value;
        const birthMonth = document.getElementById('birthMonth').value;
        const birthDay = document.getElementById('birthDay').value;
        const gender = document.getElementById('gender').value;
        
        // 显示加载状态
        this.showLoading();
        
        try {
            // 将文件转换为 base64
            const imageBase64 = await this.fileToBase64(this.imageFile);
            
            // 构建请求数据
            const requestData = {
                image_base64: imageBase64,
                filename: this.imageFile.name,
                content_type: this.imageFile.type || 'image/jpeg',
                analysis_types: analysisTypes
            };
            
            if (birthYear && birthMonth && birthDay) {
                requestData.birth_year = parseInt(birthYear);
                requestData.birth_month = parseInt(birthMonth);
                requestData.birth_day = parseInt(birthDay);
                if (gender) requestData.gender = gender;
            }
            
            console.log('使用 gRPC-Web 调用面相分析接口');
            
            // 使用 gRPC-Web 调用
            const result = await api.post('/api/v2/face/analyze', requestData);
            
            console.log('分析结果:', result);
            
            if (result.success) {
                this.displayResult(result.data);
            } else {
                const errorMsg = result.error || result.message || result.detail || '未知错误';
                alert('分析失败：' + errorMsg);
            }
        } catch (error) {
            console.error('分析错误：', error);
            alert('分析失败：' + error.message + '\n请检查网络连接和服务是否启动');
        } finally {
            this.hideLoading();
        }
    },
    
    showLoading() {
        document.getElementById('loadingSection').style.display = 'block';
        document.getElementById('resultSection').style.display = 'none';
    },
    
    hideLoading() {
        document.getElementById('loadingSection').style.display = 'none';
    },
    
    displayResult(data) {
        // 显示结果区域
        document.getElementById('resultSection').style.display = 'block';
        
        // 显示关键点信息
        if (data.landmarks) {
            document.getElementById('landmarksInfo').innerHTML = `
                <p>✅ 人脸检测成功</p>
                <p>检测到 <strong>${data.landmarks.mediapipe_points || 468}</strong> 个MediaPipe关键点</p>
                <p>映射到 <strong>${data.landmarks.mapped_features || 99}</strong> 个面相特征点</p>
            `;
        }
        
        // 显示三停五眼
        if (data.santing_analysis && data.wuyan_analysis) {
            const santing = data.santing_analysis;
            const wuyan = data.wuyan_analysis;
            
            document.getElementById('santingWuyan').innerHTML = `
                <div class="analysis-item">
                    <h4>三停分析</h4>
                    <p><strong>上停：</strong>${(santing.upper_ratio * 100).toFixed(1)}%</p>
                    <p><strong>中停：</strong>${(santing.middle_ratio * 100).toFixed(1)}%</p>
                    <p><strong>下停：</strong>${(santing.lower_ratio * 100).toFixed(1)}%</p>
                    <p class="interpretation">${santing.evaluation}</p>
                </div>
                <div class="analysis-item">
                    <h4>五眼分析</h4>
                    <p class="interpretation">${wuyan.evaluation}</p>
                </div>
            `;
        }
        
        // 显示宫位分析
        if (data.gongwei_analysis && data.gongwei_analysis.length > 0) {
            document.getElementById('gongweiCard').style.display = 'block';
            document.getElementById('gongweiResult').innerHTML = this.renderAnalysisList(data.gongwei_analysis);
        }
        
        // 显示六亲分析
        if (data.liuqin_analysis && data.liuqin_analysis.length > 0) {
            document.getElementById('liuqinCard').style.display = 'block';
            document.getElementById('liuqinResult').innerHTML = this.renderAnalysisList(data.liuqin_analysis);
        }
        
        // 显示十神分析
        if (data.shishen_analysis && data.shishen_analysis.length > 0) {
            document.getElementById('shishenCard').style.display = 'block';
            document.getElementById('shishenResult').innerHTML = this.renderAnalysisList(data.shishen_analysis);
        }
        
        // 显示总结
        document.getElementById('summaryResult').innerHTML = `
            <p>${data.overall_summary || '综合面相分析完成'}</p>
        `;
    },
    
    renderAnalysisList(list) {
        return list.map(item => {
            const name = item.name || item.relation || item.shishen || '未知';
            const interpretations = item.interpretations || [];
            
            return `
                <div class="analysis-item">
                    <h4>${name}</h4>
                    ${interpretations.length > 0 ? `
                        <ul>
                            ${interpretations.map(interp => `<li>${interp}</li>`).join('')}
                        </ul>
                    ` : '<p class="no-data">暂无断语</p>'}
                </div>
            `;
        }).join('');
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    FaceAnalysisV2.init();
});

