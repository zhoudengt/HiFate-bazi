# 登录页面 "Auth is not defined" 问题修复

## 问题描述

访问登录页面 `http://localhost:8001/frontend/login.html` 时，出现错误：
```
Auth is not defined
```

## 问题原因

1. **路径映射问题**：
   - 用户访问的是 `/frontend/login.html`
   - 但服务器只挂载了 `/local_frontend` 路径
   - 导致页面可能无法正确加载，或脚本路径不正确

2. **脚本加载时序问题**：
   - 脚本使用 `DOMContentLoaded` 事件，可能在脚本完全加载前就执行
   - 如果脚本加载失败，没有明确的错误提示

## 修复方案

### 1. 添加 `/frontend` 路径映射

**文件**: `server/main.py`

添加 `/frontend` 作为 `/local_frontend` 的别名：

```python
# 同时挂载 /frontend 作为别名（兼容旧路径）
app.mount("/frontend", StaticFiles(directory=local_frontend_dir, html=True), name="frontend")
logger.info(f"✓ 前端目录别名已挂载: /frontend -> {local_frontend_dir}")
```

### 2. 改进脚本加载检查

**文件**: `local_frontend/login.html`

- ✅ 使用 `window.addEventListener('load')` 替代 `DOMContentLoaded`
  - 确保所有脚本（包括外部脚本）都已加载完成
- ✅ 添加脚本加载错误处理（`onerror` 属性）
- ✅ 添加详细的调试信息
- ✅ 检查所有必要的对象（`Auth`, `api`, `TOKEN_KEY`）

### 3. 改进错误提示

- ✅ 在页面上显示明确的错误信息
- ✅ 在浏览器控制台输出详细的调试信息
- ✅ 区分不同类型的错误（脚本加载失败、对象未定义等）

## 修复后的代码

### server/main.py

```python
# 挂载静态文件目录（本地前端文件）
local_frontend_dir = os.path.join(project_root, "local_frontend")
if os.path.exists(local_frontend_dir):
    app.mount("/local_frontend", StaticFiles(directory=local_frontend_dir, html=True), name="local_frontend")
    logger.info(f"✓ 本地前端目录已挂载: /local_frontend -> {local_frontend_dir}")
    # 同时挂载 /frontend 作为别名（兼容旧路径）
    app.mount("/frontend", StaticFiles(directory=local_frontend_dir, html=True), name="frontend")
    logger.info(f"✓ 前端目录别名已挂载: /frontend -> {local_frontend_dir}")
```

### local_frontend/login.html

```html
<script src="config.js" onerror="console.error('❌ config.js 加载失败'); document.getElementById('errorMsg').textContent = '页面加载错误：config.js 未找到'"></script>
<script src="js/api.js" onerror="console.error('❌ js/api.js 加载失败'); document.getElementById('errorMsg').textContent = '页面加载错误：api.js 未找到'"></script>
<script src="js/auth.js" onerror="console.error('❌ js/auth.js 加载失败'); document.getElementById('errorMsg').textContent = '页面加载错误：auth.js 未找到'"></script>
<script>
    // 等待所有脚本加载完成
    window.addEventListener('load', function() {
        console.log('📄 页面加载完成，检查脚本...');
        console.log('Auth:', typeof Auth !== 'undefined' ? '✅ 已定义' : '❌ 未定义');
        console.log('api:', typeof api !== 'undefined' ? '✅ 已定义' : '❌ 未定义');
        console.log('TOKEN_KEY:', typeof TOKEN_KEY !== 'undefined' ? '✅ 已定义' : '❌ 未定义');
        
        // 检查必要的对象是否已加载
        if (typeof Auth === 'undefined') {
            console.error('❌ Auth 对象未定义，请检查 js/auth.js 是否正确加载');
            const errorMsg = document.getElementById('errorMsg');
            if (errorMsg) {
                errorMsg.textContent = '页面加载错误：Auth 对象未定义。请检查浏览器控制台查看详细错误信息。';
                errorMsg.style.color = 'red';
            }
            return;
        }
        
        // ... 登录表单事件处理
    });
</script>
```

## 测试验证

### 1. 检查路径映射

访问以下路径，应该都能正常显示登录页面：
- `http://localhost:8001/local_frontend/login.html` ✅
- `http://localhost:8001/frontend/login.html` ✅

### 2. 检查脚本加载

打开浏览器开发者工具（F12），查看：
- **Console 标签**：应该看到 "✅ 所有脚本已正确加载"
- **Network 标签**：检查以下文件是否成功加载（状态码 200）：
  - `config.js`
  - `js/api.js`
  - `js/auth.js`

### 3. 测试登录功能

1. 输入用户名：`admin`
2. 输入密码：`admin123`
3. 点击登录按钮
4. 应该能成功登录并跳转到首页

## 问题排查

如果仍然出现 "Auth is not defined" 错误：

### 1. 检查脚本文件是否存在

```bash
ls -la local_frontend/js/auth.js
ls -la local_frontend/js/api.js
ls -la local_frontend/config.js
```

### 2. 检查浏览器控制台

打开浏览器开发者工具（F12），查看：
- **Console 标签**：查看是否有脚本加载错误
- **Network 标签**：查看脚本文件是否成功加载（状态码应该是 200）

### 3. 检查脚本路径

如果页面路径是 `/frontend/login.html`，脚本路径应该是：
- `config.js` → `/frontend/config.js`
- `js/api.js` → `/frontend/js/api.js`
- `js/auth.js` → `/frontend/js/auth.js`

### 4. 检查服务器日志

查看服务器启动日志，确认路径映射：
```
✓ 本地前端目录已挂载: /local_frontend -> /path/to/local_frontend
✓ 前端目录别名已挂载: /frontend -> /path/to/local_frontend
```

## 相关文件

- `server/main.py` - 服务器主文件（路径映射）
- `local_frontend/login.html` - 登录页面（脚本加载）
- `local_frontend/js/auth.js` - 认证逻辑
- `local_frontend/js/api.js` - API 客户端
- `local_frontend/config.js` - 配置文件

## 注意事项

1. **路径兼容性**：
   - 现在同时支持 `/local_frontend` 和 `/frontend` 路径
   - 建议统一使用 `/local_frontend`（符合项目规范）

2. **脚本加载顺序**：
   - `config.js` → `js/api.js` → `js/auth.js`
   - 必须按此顺序加载，因为后面的脚本依赖前面的

3. **错误处理**：
   - 现在有详细的错误提示和调试信息
   - 如果脚本加载失败，会在页面上显示明确的错误信息
