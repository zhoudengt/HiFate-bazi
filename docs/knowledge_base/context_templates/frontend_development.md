# 前端开发上下文模板

## 开发步骤

1. **创建 HTML 文件**
   - 位置：`local_frontend/xxx.html`
   - 使用 gRPC-Web 客户端调用 API

2. **创建 JS 文件**
   - 位置：`local_frontend/js/xxx.js`
   - 使用 `api.js` 中的 gRPC-Web 客户端

3. **创建 CSS 文件（可选）**
   - 位置：`local_frontend/css/xxx.css`
   - 样式文件

4. **API 对接**
   - 使用 `api.post()` 调用后端 API
   - 处理响应和错误

5. **完整性验证**
   - 运行：`python3 scripts/ai/completeness_validator.py --type frontend --name xxx`
   - 确保所有检查项通过

6. **触发热更新（如涉及后端）**
   - 运行：`python3 scripts/ai/auto_hot_reload.py --trigger`
   - 验证热更新成功

## 必需文件

- `local_frontend/xxx.html` - HTML 文件
- `local_frontend/js/xxx.js` - JS 文件
- `local_frontend/css/xxx.css` - CSS 文件（可选）

## 必需实现

- API 对接（使用 gRPC-Web 客户端）

## 检查清单

- [ ] HTML 文件已创建
- [ ] JS 文件已创建
- [ ] CSS 文件已创建（可选）
- [ ] API 对接已实现
- [ ] 前端功能测试通过

