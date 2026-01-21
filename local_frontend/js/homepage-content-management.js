/**
 * 首页内容管理 JavaScript
 */

const HomepageContentManager = {
    api: null,
    currentTags: [],
    editingId: null,
    
    init() {
        // 初始化 API 客户端
        this.api = new ApiClient(API_CONFIG.baseURL);
        
        // 加载内容列表
        this.loadContents();
        
        // 标签输入框回车事件
        document.getElementById('newTag').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.addTag();
            }
        });
    },
    
    /**
     * 加载内容列表
     */
    async loadContents() {
        const listContainer = document.getElementById('contentList');
        listContainer.innerHTML = '<div class="loading">加载中...</div>';
        
        try {
            // 使用 gRPC-Web 调用
            const result = await this.api.post('/homepage/contents', { enabled_only: false });
            
            if (result && result.success && result.data) {
                this.renderContentList(result.data);
            } else {
                throw new Error(result?.error || '加载失败');
            }
        } catch (error) {
            console.error('加载内容列表失败:', error);
            ErrorHandler.handleApiError(error, {
                containerId: 'errorMessage'
            });
            listContainer.innerHTML = '<div class="empty-state">加载失败，请刷新重试</div>';
        }
    },
    
    /**
     * 渲染内容列表
     */
    renderContentList(contents) {
        const listContainer = document.getElementById('contentList');
        
        if (!contents || contents.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">暂无内容，请创建新内容</div>';
            return;
        }
        
        // 按 sort_order 排序
        const sortedContents = [...contents].sort((a, b) => a.sort_order - b.sort_order);
        
        listContainer.innerHTML = sortedContents.map(content => `
            <div class="content-item" data-id="${content.id}">
                <div class="content-item-header">
                    <div class="content-item-title">${this.escapeHtml(content.title)}</div>
                    <div class="content-item-meta">
                        <span>排序: ${content.sort_order}</span>
                        <span>${content.enabled ? '✓ 启用' : '✗ 禁用'}</span>
                    </div>
                </div>
                
                ${content.tags && content.tags.length > 0 ? `
                    <div class="content-item-tags">
                        ${content.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
                    </div>
                ` : ''}
                
                <div style="color: #666; font-size: 14px; margin: 10px 0; max-height: 60px; overflow: hidden;">
                    ${this.escapeHtml(content.description.substring(0, 100))}${content.description.length > 100 ? '...' : ''}
                </div>
                
                ${content.image_base64 ? `
                    <img src="${content.image_base64}" style="max-width: 100px; max-height: 60px; border-radius: 5px; margin: 10px 0;">
                ` : ''}
                
                <div class="content-item-actions">
                    <button class="btn btn-primary btn-small" onclick="HomepageContentManager.editContent(${content.id})">编辑</button>
                    <div class="sort-controls">
                        <button class="btn btn-secondary btn-small sort-btn" onclick="HomepageContentManager.updateSort(${content.id}, ${content.sort_order - 1})">↑</button>
                        <button class="btn btn-secondary btn-small sort-btn" onclick="HomepageContentManager.updateSort(${content.id}, ${content.sort_order + 1})">↓</button>
                    </div>
                    <button class="btn btn-danger btn-small" onclick="HomepageContentManager.deleteContent(${content.id})">删除</button>
                </div>
            </div>
        `).join('');
    },
    
    /**
     * 编辑内容
     */
    async editContent(id) {
        try {
            // 使用 gRPC-Web 获取详情（与其他接口保持一致）
            const result = await this.api.post('/homepage/contents/detail', { id: parseInt(id) });
            
            if (result && result.success && result.data) {
                const content = result.data;
                this.editingId = id;
                
                // 填充表单
                document.getElementById('contentId').value = id;
                document.getElementById('title').value = content.title;
                document.getElementById('description').value = content.description;
                document.getElementById('sortOrder').value = content.sort_order;
                document.getElementById('enabled').checked = content.enabled;
                document.getElementById('enabledGroup').style.display = 'block';
                
                // 设置标签
                this.currentTags = content.tags || [];
                this.renderTags();
                
                // 设置图片
                if (content.image_base64) {
                    document.getElementById('imageBase64').value = content.image_base64;
                    document.getElementById('imagePreview').src = content.image_base64;
                    document.getElementById('imagePreview').style.display = 'block';
                }
                
                // 更新表单标题
                document.getElementById('formTitle').textContent = '编辑内容';
                
                // 滚动到表单
                document.querySelector('.content-form').scrollIntoView({ behavior: 'smooth' });
                
                // 高亮当前项
                document.querySelectorAll('.content-item').forEach(item => {
                    item.classList.remove('active');
                    if (item.dataset.id == id) {
                        item.classList.add('active');
                    }
                });
            } else {
                throw new Error(result?.error || '获取内容详情失败');
            }
        } catch (error) {
            console.error('获取内容详情失败:', error);
            ErrorHandler.handleApiError(error, {
                containerId: 'errorMessage'
            });
        }
    },
    
    /**
     * 处理表单提交
     */
    async handleSubmit(event) {
        event.preventDefault();
        
        const formData = {
            title: document.getElementById('title').value.trim(),
            tags: this.currentTags,
            description: document.getElementById('description').value.trim(),
            image_base64: document.getElementById('imageBase64').value,
            sort_order: parseInt(document.getElementById('sortOrder').value) || 0
        };
        
        // 验证
        if (!formData.title) {
            ErrorHandler.showError('请输入标题', { containerId: 'errorMessage' });
            return;
        }
        
        if (!formData.description) {
            ErrorHandler.showError('请输入详细描述', { containerId: 'errorMessage' });
            return;
        }
        
        if (!formData.image_base64) {
            ErrorHandler.showError('请上传图片', { containerId: 'errorMessage' });
            return;
        }
        
        try {
            const id = document.getElementById('contentId').value;
            
            if (id) {
                // 更新 - 使用 gRPC-Web（与其他接口保持一致）
                const updateData = { ...formData, id: parseInt(id) };
                if (document.getElementById('enabledGroup').style.display !== 'none') {
                    updateData.enabled = document.getElementById('enabled').checked;
                }
                
                const result = await this.api.post('/admin/homepage/contents/update', updateData);
                
                if (result && result.success) {
                    ErrorHandler.showSuccess('内容更新成功', { containerId: 'successMessage' });
                    this.resetForm();
                    this.loadContents();
                } else {
                    throw new Error(result?.error || result?.detail || '更新失败');
                }
            } else {
                // 创建 - 使用 gRPC-Web（与其他接口保持一致）
                const result = await this.api.post('/admin/homepage/contents', formData);
                
                if (result && result.success) {
                    ErrorHandler.showSuccess('内容创建成功', { containerId: 'successMessage' });
                    this.resetForm();
                    this.loadContents();
                } else {
                    throw new Error(result?.error || result?.detail || '创建失败');
                }
            }
        } catch (error) {
            console.error('保存失败:', error);
            ErrorHandler.handleApiError(error, {
                containerId: 'errorMessage'
            });
        }
    },
    
    /**
     * 删除内容
     */
    async deleteContent(id) {
        if (!confirm('确定要删除这个内容吗？')) {
            return;
        }
        
        try {
            // 使用 gRPC-Web（与其他接口保持一致）
            const result = await this.api.post('/admin/homepage/contents/delete', { id: id });
            
            if (result && result.success) {
                ErrorHandler.showSuccess('内容已删除', { containerId: 'successMessage' });
                this.loadContents();
                
                // 如果删除的是正在编辑的内容，重置表单
                if (this.editingId == id) {
                    this.resetForm();
                }
            } else {
                throw new Error(result?.error || result?.detail || '删除失败');
            }
        } catch (error) {
            console.error('删除失败:', error);
            ErrorHandler.handleApiError(error, {
                containerId: 'errorMessage'
            });
        }
    },
    
    /**
     * 更新排序
     */
    async updateSort(id, newSortOrder) {
        if (newSortOrder < 0) {
            newSortOrder = 0;
        }
        
        try {
            // 使用 gRPC-Web（与其他接口保持一致）
            const result = await this.api.post('/admin/homepage/contents/sort', { 
                id: id, 
                sort_order: newSortOrder 
            });
            
            if (result && result.success) {
                ErrorHandler.showSuccess('排序更新成功', { containerId: 'successMessage' });
                this.loadContents();
            } else {
                throw new Error(result?.error || result?.detail || '更新排序失败');
            }
        } catch (error) {
            console.error('更新排序失败:', error);
            ErrorHandler.handleApiError(error, {
                containerId: 'errorMessage'
            });
        }
    },
    
    /**
     * 处理图片选择
     */
    async handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }
        
        try {
            const base64 = await this.fileToBase64(file);
            document.getElementById('imageBase64').value = base64;
            document.getElementById('imagePreview').src = base64;
            document.getElementById('imagePreview').style.display = 'block';
        } catch (error) {
            console.error('图片转换失败:', error);
            ErrorHandler.showError('图片转换失败: ' + error.message, { containerId: 'errorMessage' });
        }
    },
    
    /**
     * 文件转Base64
     */
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                resolve(reader.result);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
    
    /**
     * 添加标签
     */
    addTag() {
        const input = document.getElementById('newTag');
        const tag = input.value.trim();
        
        if (tag && !this.currentTags.includes(tag)) {
            this.currentTags.push(tag);
            this.renderTags();
            input.value = '';
        }
    },
    
    /**
     * 渲染标签
     */
    renderTags() {
        const container = document.getElementById('tagsContainer');
        container.innerHTML = this.currentTags.map((tag, index) => `
            <span class="tag">
                ${this.escapeHtml(tag)}
                <span style="cursor: pointer; margin-left: 5px;" onclick="HomepageContentManager.removeTag(${index})">×</span>
            </span>
        `).join('');
    },
    
    /**
     * 移除标签
     */
    removeTag(index) {
        this.currentTags.splice(index, 1);
        this.renderTags();
    },
    
    /**
     * 重置表单
     */
    resetForm() {
        document.getElementById('contentForm').reset();
        document.getElementById('contentId').value = '';
        document.getElementById('imagePreview').style.display = 'none';
        document.getElementById('imageBase64').value = '';
        document.getElementById('enabledGroup').style.display = 'none';
        this.currentTags = [];
        this.renderTags();
        this.editingId = null;
        document.getElementById('formTitle').textContent = '创建新内容';
        
        // 移除高亮
        document.querySelectorAll('.content-item').forEach(item => {
            item.classList.remove('active');
        });
    },
    
    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    HomepageContentManager.init();
});
