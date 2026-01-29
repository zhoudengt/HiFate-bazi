# ELK 流式日志栈

## 资源设计原则

ELK 使用**低优先级资源**，不与主应用竞争：

| 服务 | CPU 限制 | 内存限制 | 说明 |
|------|----------|----------|------|
| Elasticsearch | 1.0 | 3G | JVM 堆 1G，避免竞争 |
| Logstash | 0.5 | 512M | JVM 堆 256M |
| Kibana | 0.5 | 512M | Node.js 限制 256M |
| Filebeat | 0.2 | 128M | 极低资源，增量读取 |

## 部署

与主应用一起启动（推荐）：

```bash
docker-compose -f docker-compose.yml -f docker-compose.elk.yml up -d
```

仅启动 ELK（需先创建网络）：

```bash
docker network create hifate-network 2>/dev/null || true
docker-compose -f docker-compose.elk.yml up -d
```

## 服务与端口

| 服务 | 端口 | 访问方式 |
|------|------|----------|
| Elasticsearch | 127.0.0.1:9200 | 仅本地访问 |
| Kibana | 127.0.0.1:5601 | 仅本地访问，生产通过 nginx 代理 + 认证 |
| Logstash | 5044 (内部) | Filebeat 连接 |

## 日志索引

- 索引名：`stream-flow-YYYY.MM.dd`（按天滚动）
- 按 `trace_id` 可关联同一请求的 request / input_data / prompt / llm_response / complete

## 安全配置

### 生产环境建议

1. **启用 Elasticsearch 安全认证**：
   ```yaml
   environment:
     - xpack.security.enabled=true
     - ELASTIC_PASSWORD=your_password
   ```

2. **通过 nginx 反向代理 Kibana**：
   ```nginx
   location /kibana/ {
       auth_basic "Kibana";
       auth_basic_user_file /etc/nginx/.htpasswd;
       proxy_pass http://127.0.0.1:5601/;
   }
   ```

3. **敏感字段脱敏**（可选）：
   ```bash
   export STREAM_FLOW_MASK_SENSITIVE=true
   ```

## 可选：90 天保留（ILM）

在 Kibana Dev Tools 或 curl 中执行：

```json
PUT _ilm/policy/stream-flow-policy
{
  "policy": {
    "phases": {
      "hot": { "min_age": "0ms", "actions": { "rollover": { "max_size": "5gb", "max_age": "1d" } } },
      "delete": { "min_age": "90d", "actions": { "delete": {} } }
    }
  }
}
```

## 关闭流式日志

应用侧关闭（不写 stream_flow.log）：

```bash
export STREAM_FLOW_LOGGING_ENABLED=false
# 触发热更新
```

## 性能监控

如果发现日志丢弃，检查应用日志中的警告：
```
stream_flow 队列已满，已丢弃 N 条日志
```

可通过增大队列或降低日志频率解决。
