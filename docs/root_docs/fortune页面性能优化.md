# Fortune 页面性能优化指南

## 🔍 问题诊断

### 当前状态
- ✅ 前端服务器运行正常（端口 8080）
- ✅ 后端API响应正常（~0.09秒）
- ⚠️ 用户反馈页面加载慢

### 可能原因

1. **首次加载计算量大**
   - 需要计算大运、流年、流月
   - 首次请求没有缓存

2. **前端超时设置**
   - 当前超时：30秒
   - 如果计算超过30秒会超时

3. **浏览器缓存问题**
   - 静态资源未缓存
   - 重复请求相同数据

## 🚀 优化方案

### 1. 添加加载提示（已优化）

前端已显示"加载中..."，但可以改进：

```javascript
// 在 fortune.js 中添加更详细的加载提示
resultDiv.innerHTML = '<div class="loading">正在计算大运流年流月，请稍候...</div>';
```

### 2. 优化API超时设置

**当前配置** (`config.js`):
```javascript
timeout: 30000  // 30秒
```

**建议**:
- 轻量级请求：10秒
- 重量级请求（fortune）：60秒

### 3. 添加请求重试机制

```javascript
async function loadFortuneDataWithRetry(maxRetries = 2) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await loadFortuneData();
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
        }
    }
}
```

### 4. 使用缓存优化

**前端缓存**:
```javascript
// 缓存计算结果
const cacheKey = `${solar_date}_${solar_time}_${gender}`;
const cached = sessionStorage.getItem(cacheKey);
if (cached) {
    return JSON.parse(cached);
}
```

### 5. 分步加载（渐进式加载）

```javascript
// 先加载大运（快速）
await loadDayun();

// 再加载流年（中等）
await loadLiunian();

// 最后加载流月（较慢）
await loadLiuyue();
```

## 📊 性能监控

### 添加性能日志

```javascript
const startTime = performance.now();
await loadFortuneData();
const endTime = performance.now();
console.log(`加载耗时: ${(endTime - startTime).toFixed(2)}ms`);
```

### 检查网络请求

1. 打开浏览器开发者工具（F12）
2. 查看 Network 标签
3. 检查 `/api/v1/bazi/fortune/display` 请求：
   - **Status**: 应该是 200
   - **Time**: 应该 < 1秒（有缓存）或 < 5秒（无缓存）
   - **Size**: 检查响应大小

## 🔧 快速修复

### 方案1: 增加超时时间（最简单）

修改 `frontend/config.js`:
```javascript
timeout: 60000  // 改为60秒
```

### 方案2: 添加错误提示

修改 `frontend/js/fortune.js`:
```javascript
catch (error) {
    console.error('加载数据失败:', error);
    const errorMsg = error.message || '加载失败';
    resultDiv.innerHTML = `
        <div class="error">
            <p>${errorMsg}</p>
            <button onclick="loadFortuneData()" class="btn btn-primary">重试</button>
        </div>
    `;
}
```

### 方案3: 检查后端服务

```bash
# 检查后端是否运行
curl http://127.0.0.1:8001/api/v1/bazi/fortune/display \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1990-05-15","solar_time":"14:30","gender":"male","current_time":"2024-11-17 14:00"}'
```

## 📝 常见问题

### Q1: 页面一直显示"加载中..."

**可能原因**:
1. 后端服务未启动
2. 网络连接问题
3. API超时

**解决方法**:
1. 检查后端服务：`ps aux | grep "python.*start.py"`
2. 检查浏览器控制台错误
3. 检查网络请求状态

### Q2: 请求超时

**可能原因**:
1. 计算量太大
2. 数据库查询慢
3. gRPC服务响应慢

**解决方法**:
1. 增加超时时间
2. 检查数据库性能
3. 检查gRPC服务状态

### Q3: 首次加载慢，后续快

**原因**: 缓存生效

**解决方法**: 这是正常的，首次计算需要时间

## 🎯 预期性能

| 场景 | 响应时间 | 说明 |
|------|---------|------|
| 有缓存 | < 0.1秒 | 从缓存读取 |
| 首次计算 | 0.5-2秒 | 需要计算大运流年流月 |
| 超时 | > 30秒 | 需要检查后端服务 |

## ✅ 检查清单

- [ ] 后端服务运行正常（端口 8001）
- [ ] 前端服务器运行正常（端口 8080）
- [ ] 浏览器控制台无错误
- [ ] 网络请求状态正常（200）
- [ ] 响应时间合理（< 5秒）
- [ ] 超时设置合理（30-60秒）

