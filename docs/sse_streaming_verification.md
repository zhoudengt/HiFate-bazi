# SSE 流式接口验证指南

## 问题背景

生产环境的 SSE 流式接口在浏览器直接访问 FastAPI 端口（8001）时，连接会在 30-60 秒后被 NAT/防火墙关闭，导致 `ERR_INCOMPLETE_CHUNKED_ENCODING` 错误。

## 解决方案

### 方案一：通过 Nginx 代理访问（已实现）

前端代码已修改为通过 Nginx 代理访问，而不是直接访问 FastAPI 端口：

**修改前**：
```javascript
const PRODUCTION_API = 'http://8.210.52.217:8001';  // 直接访问 FastAPI
```

**修改后**：
```javascript
const PRODUCTION_API = window.location.hostname === 'localhost' 
    ? 'http://8.210.52.217'  // 通过 Nginx 80 端口
    : (window.location.protocol + '//' + window.location.host);
```

### 方案二：心跳包机制（已实现）

后端代码已添加心跳包机制，每 10 秒发送一次心跳包，保持连接活跃：

- 文件：`server/api/v1/xishen_jishen.py`
- 心跳间隔：10 秒
- 心跳类型：`heartbeat`

## 验证步骤

### 1. 检查 Nginx 配置

确认生产环境的 Nginx 配置包含 SSE 流式接口配置：

```nginx
location /api/v1/bazi/xishen-jishen/stream {
    proxy_pass http://web_backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;  # 5分钟超时
    chunked_transfer_encoding on;
}
```

### 2. 浏览器测试

1. 打开浏览器开发者工具（F12）
2. 访问页面：`http://yuanqistation.com/frontend/xishen-jishen.html` 或 `http://8.210.52.217/frontend/xishen-jishen.html`
3. 观察网络请求：
   - 应该看到请求发送到 `/api/v1/bazi/xishen-jishen/stream`
   - 请求应该通过 Nginx（80 端口），而不是直接访问 8001 端口
4. 观察控制台日志：
   - 应该看到 `📡 开始连接生产接口: http://.../api/v1/bazi/xishen-jishen/stream`
   - 应该看到心跳包日志：`💓 收到心跳: 正在生成AI分析...`
5. 观察页面显示：
   - 应该看到内容逐步显示（流式效果）
   - 不应该出现 `ERR_INCOMPLETE_CHUNKED_ENCODING` 错误

### 3. 命令行测试

```bash
# 测试通过 Nginx 访问（如果域名已配置）
curl -s -N -X POST "http://yuanqistation.com/api/v1/bazi/xishen-jishen/stream" \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1987-01-07","solar_time":"09:30","gender":"male"}' \
  --max-time 60

# 应该看到：
# 1. data: {"type": "data", ...}  (基础数据)
# 2. data: {"type": "heartbeat", "content": "正在生成AI分析，请稍候..."}  (初始心跳)
# 3. data: {"type": "heartbeat", "content": "正在生成AI分析... (10秒)"}  (后续心跳)
# 4. data: {"type": "progress", "content": "..."}  (AI 分析内容)
```

## 故障排查

### 问题：仍然出现 ERR_INCOMPLETE_CHUNKED_ENCODING

**可能原因**：
1. 前端代码未更新（浏览器缓存）
2. Nginx 未运行或配置未生效
3. 仍然直接访问 8001 端口

**解决方法**：
1. 强制刷新浏览器（Ctrl+Shift+R 或 Cmd+Shift+R）
2. 检查浏览器网络请求，确认请求发送到 80 端口而不是 8001
3. 检查 Nginx 配置和运行状态

### 问题：心跳包未收到

**可能原因**：
1. 后端代码未部署
2. 心跳任务未启动

**解决方法**：
1. 检查后端日志，确认心跳包已发送
2. 确认后端代码已通过热更新或重启生效

## 部署检查清单

- [ ] 后端心跳包代码已部署
- [ ] 前端代码已更新（通过 Nginx 代理）
- [ ] Nginx 配置包含 SSE 流式接口配置
- [ ] Nginx 服务正常运行
- [ ] 浏览器测试通过
- [ ] 控制台无错误日志

