# 首页内容管理 - 端到端测试指南

## 测试环境准备

### 1. 启动后端服务

确保后端服务正在运行：

```bash
# 如果使用Docker
docker-compose up -d

# 或者直接运行
python server/main.py
```

服务应该运行在 `http://localhost:8001`

### 2. 确认数据库表已创建

```bash
# 执行数据库迁移（如果还没执行）
python scripts/db/migrate_homepage_contents.py
```

## 测试方式

### 方式1: 使用管理界面（推荐）

1. **打开管理界面**
   - 在浏览器中打开: `local_frontend/homepage-content-management.html`
   - 或者通过本地服务器访问（如果配置了）

2. **功能测试清单**

   - [ ] **查看内容列表**
     - 打开页面后应该能看到内容列表（如果已有数据）
     - 点击"刷新"按钮应该能重新加载列表
   
   - [ ] **创建新内容**
     - 填写标题、描述
     - 添加标签（输入标签后按回车或点击"添加"）
     - 上传图片（选择图片文件，会自动转换为Base64）
     - 设置排序值
     - 点击"保存"按钮
     - 应该看到成功消息，列表自动刷新
   
   - [ ] **编辑内容**
     - 在内容列表中点击"编辑"按钮
     - 表单应该自动填充该内容的数据
     - 修改任意字段
     - 点击"保存"按钮
     - 应该看到成功消息，列表自动更新
   
   - [ ] **调整排序**
     - 在内容列表中点击"↑"或"↓"按钮
     - 排序值应该相应增减
     - 列表应该按新的排序重新排列
   
   - [ ] **删除内容**
     - 在内容列表中点击"删除"按钮
     - 确认删除
     - 内容应该从列表中消失（软删除，设置enabled=false）

### 方式2: 使用API测试脚本

运行自动化测试脚本：

```bash
# 安装依赖（如果还没安装）
pip install requests

# 运行测试
python scripts/test_homepage_content_api.py
```

测试脚本会依次测试：
1. 获取内容列表
2. 创建内容
3. 更新内容
4. 更新排序
5. 删除内容

### 方式3: 使用curl命令手动测试

#### 获取内容列表
```bash
curl -X GET "http://localhost:8001/api/v1/homepage/contents?enabled_only=false"
```

#### 创建内容
```bash
curl -X POST "http://localhost:8001/api/v1/admin/homepage/contents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试内容",
    "tags": ["测试", "API"],
    "description": "这是一个测试内容",
    "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "sort_order": 1
  }'
```

#### 更新内容（替换{id}为实际ID）
```bash
curl -X PUT "http://localhost:8001/api/v1/admin/homepage/contents/{id}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "更新后的标题",
    "sort_order": 2
  }'
```

#### 更新排序（替换{id}为实际ID）
```bash
curl -X PUT "http://localhost:8001/api/v1/admin/homepage/contents/{id}/sort" \
  -H "Content-Type: application/json" \
  -d '{
    "sort_order": 1
  }'
```

#### 删除内容（替换{id}为实际ID）
```bash
curl -X DELETE "http://localhost:8001/api/v1/admin/homepage/contents/{id}"
```

## 测试检查点

### 功能检查

- [x] 内容列表能正常加载
- [x] 创建内容功能正常
- [x] 编辑内容功能正常
- [x] 删除内容功能正常（软删除）
- [x] 排序功能正常
- [x] 图片上传和显示正常
- [x] 标签添加和删除正常
- [x] 表单验证正常（必填字段）

### 数据检查

- [x] 数据正确保存到数据库
- [x] 排序字段正确更新
- [x] 图片Base64正确存储
- [x] 标签JSON格式正确
- [x] 软删除后enabled字段为false

### 界面检查

- [x] 响应式布局正常（移动端适配）
- [x] 错误消息正确显示
- [x] 成功消息正确显示
- [x] 加载状态正确显示
- [x] 图片预览正常

### API检查

- [x] REST API端点正常
- [x] gRPC-Web端点正常（查询接口）
- [x] 错误处理正确
- [x] 响应格式正确

## 常见问题

### 1. 页面无法加载

**问题**: 打开HTML页面后显示空白或错误

**解决**:
- 检查浏览器控制台是否有错误
- 确认 `config.js` 和 `js/api.js` 文件存在
- 确认API服务正在运行

### 2. API调用失败

**问题**: 创建/更新/删除操作失败

**解决**:
- 检查后端服务是否运行: `curl http://localhost:8001/api/v1/homepage/contents`
- 检查数据库连接是否正常
- 查看后端日志

### 3. 图片上传失败

**问题**: 图片无法上传或显示

**解决**:
- 检查图片格式是否支持（建议使用JPG/PNG）
- 检查图片大小（Base64编码后可能很大）
- 查看浏览器控制台是否有错误

### 4. 排序不生效

**问题**: 调整排序后列表顺序没有变化

**解决**:
- 刷新页面查看
- 检查sort_order字段是否正确更新
- 确认列表按sort_order排序

## 测试数据建议

为了完整测试，建议创建以下测试数据：

1. **AI守护神** - sort_order: 1
2. **八字命理** - sort_order: 2
3. **流年运势** - sort_order: 3
4. **相术风水** - sort_order: 4

每个内容都应该包含：
- 标题
- 2-3个标签
- 详细描述
- 图片

## 性能测试（可选）

如果内容较多，可以测试：

1. **列表加载性能**: 创建100条内容，测试列表加载时间
2. **图片大小影响**: 上传不同大小的图片，测试性能
3. **并发请求**: 同时发送多个请求，测试并发处理能力

## 测试报告模板

```
测试日期: YYYY-MM-DD
测试人员: XXX
测试环境: localhost:8001

功能测试结果:
- 获取内容列表: ✅/❌
- 创建内容: ✅/❌
- 编辑内容: ✅/❌
- 删除内容: ✅/❌
- 更新排序: ✅/❌
- 图片上传: ✅/❌

发现的问题:
1. [问题描述]
2. [问题描述]

建议:
1. [建议内容]
2. [建议内容]
```
