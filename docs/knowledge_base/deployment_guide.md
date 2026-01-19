# HiFate-bazi 增量部署指南

> **目的**：标准化双机生产环境的增量部署流程，确保部署稳定可靠
> **适用范围**：所有代码更新的生产环境部署
> **最后更新**：2026-01-07

---

## 📋 目录

1. [生产环境信息](#生产环境信息)
2. [标准部署流程](#标准部署流程)
3. [部署前检查清单](#部署前检查清单)
4. [部署后验证清单](#部署后验证清单)
5. [常见问题排查](#常见问题排查)
6. [快速命令参考](#快速命令参考)

---

## 🖥️ 生产环境信息

### 双机部署架构

| 节点 | 公网 IP | 内网 IP | 角色 |
|------|---------|---------|------|
| Node1 | 8.210.52.217 | 172.18.121.222 | 主节点 |
| Node2 | 47.243.160.43 | 172.18.121.223 | 备节点 |

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Web 服务 | 8001 | FastAPI 主服务 |
| gRPC-Web | 8001 | 通过 `/api/grpc-web/` 路径访问 |
| Nginx | 80/443 | 前端代理 |
| MySQL | 3306 | 数据库（主从） |
| Redis | 6379 | 缓存（主从） |

### SSH 连接信息

```bash
# 连接配置
用户名: root
密码: ${SSH_PASSWORD}  # 从环境变量读取，禁止硬编码
项目目录: /opt/HiFate-bazi

# 连接命令（使用 sshpass）
sshpass -p "${SSH_PASSWORD}" ssh -o StrictHostKeyChecking=no root@8.210.52.217  # Node1
sshpass -p "${SSH_PASSWORD}" ssh -o StrictHostKeyChecking=no root@47.243.160.43  # Node2
```

### Git 仓库

| 仓库 | 地址 | 用途 |
|------|------|------|
| GitHub (origin) | github.com:zhoudengt/HiFate-bazi.git | 主仓库 |
| Gitee (gitee) | https://gitee.com/zhoudengtang/hifate-prod.git | 国内镜像 |

---

## 🚀 标准部署流程

### 完整流程图

```
本地开发 → Git 提交 → 推送远程 → 增量部署 → 验证
    │           │           │           │        │
    ▼           ▼           ▼           ▼        ▼
  编码/测试   commit    push to     执行脚本   健康检查
                       origin/gitee          热更新验证
```

### 步骤详解

#### 1️⃣ 本地开发完成

```bash
# 确保代码在本地测试通过
cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 检查修改的文件
git status

# 语法检查
python3 -m py_compile <修改的文件>
```

#### 2️⃣ Git 提交

```bash
# 添加修改
git add <文件>

# 提交（遵循提交规范）
git commit -m "feat/fix/docs(模块): 简要描述"

# 提交规范示例：
# feat(grpc): 添加流式端点注册
# fix(api): 修复空响应问题
# docs(readme): 更新部署文档
```

#### 3️⃣ 推送远程仓库

```bash
# 推送到 GitHub（主仓库）
git push origin master

# 推送到 Gitee（国内镜像，生产服务器使用）
git push gitee master
```

#### 4️⃣ 执行增量部署

```bash
# 执行增量部署脚本
cd /Users/zhoudt/Downloads/project/HiFate-bazi
bash deploy/scripts/incremental_deploy_production.sh
```

**部署脚本执行内容**：
1. 拉取最新代码到 Node1 和 Node2
2. 验证双机代码一致性
3. 触发热更新
4. 执行健康检查
5. 验证关键功能

#### 5️⃣ 部署验证

```bash
# 检查健康状态
curl http://8.210.52.217:8001/health
curl http://47.243.160.43:8001/health

# 检查热更新状态
curl http://8.210.52.217:8001/api/v1/hot-reload/status
curl http://47.243.160.43:8001/api/v1/hot-reload/status

# 测试关键接口
curl -X POST http://8.210.52.217:8001/api/v1/bazi/interface \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
```

---

## ✅ 部署前检查清单

在执行部署前，请确认以下事项：

### 代码检查
- [ ] 代码已在本地测试通过
- [ ] 语法检查无错误
- [ ] 无未提交的更改

### API 端点检查
- [ ] 新增 API 是否注册到路由？
- [ ] 新增 API 是否需要注册到 gRPC 网关？
- [ ] 流式接口是否在 gRPC 网关中注册？

### 数据库检查
- [ ] 是否有数据库迁移需要执行？
- [ ] 数据库连接配置是否正确？

### 配置检查
- [ ] 环境变量是否配置正确？
- [ ] 是否有敏感信息泄露？

### 错误预防检查
- [ ] 是否阅读了[错误记录本](./error_records.md)？
- [ ] 是否避免了已知问题？

---

## ✅ 部署后验证清单

部署完成后，请验证以下事项：

### 基础验证
- [ ] Node1 健康检查通过
- [ ] Node2 健康检查通过
- [ ] 双机代码版本一致

### 热更新验证
- [ ] Node1 热更新状态正常
- [ ] Node2 热更新状态正常

### 功能验证
- [ ] 关键 API 接口响应正常
- [ ] 新功能测试通过
- [ ] gRPC-Web 调用正常

### 日志检查
- [ ] 无异常错误日志
- [ ] 无性能告警

---

## 🔧 常见问题排查

### 问题 1：SSH 连接超时

**现象**：
```
ssh: connect to host 8.210.52.217 port 22: Connection timed out
```

**排查步骤**：
```bash
# 1. 检查网络连通性
ping 8.210.52.217

# 2. 检查 SSH 端口
nc -zv 8.210.52.217 22

# 3. 增加连接超时时间
sshpass -p "${SSH_PASSWORD}" ssh -o ConnectTimeout=60 root@8.210.52.217

# 4. 检查本地网络（尝试使用手机热点）
```

**解决方案**：
- 网络不稳定：切换网络或稍后重试
- 端口被封：联系运维检查防火墙
- 服务器问题：通过阿里云控制台检查

---

### 问题 2：Git 推送失败

**现象**：
```
error: failed to push some refs to 'origin'
```

**排查步骤**：
```bash
# 1. 检查远程仓库状态
git fetch origin

# 2. 查看是否有冲突
git status

# 3. 如果有新提交，先拉取
git pull origin master --rebase

# 4. 再次推送
git push origin master
```

---

### 问题 3：热更新未生效

**现象**：
代码部署后，接口行为未改变。

**排查步骤**：
```bash
# 1. 检查热更新状态
curl http://8.210.52.217:8001/api/v1/hot-reload/status

# 2. 手动触发热更新
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/trigger

# 3. 验证热更新
curl http://8.210.52.217:8001/api/v1/hot-reload/verify

# 4. 检查服务日志
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "docker logs --tail 50 hifate-web 2>&1 | grep -i reload"
```

**解决方案**：
- 如果热更新失败，检查是否修改了不支持热更新的模块
- 必要时重启服务（最后手段）

---

### 问题 4：双机代码不一致

**现象**：
```
❌ Node1 与 Node2 Git 版本不一致
```

**排查步骤**：
```bash
# 1. 检查两台服务器的 Git 版本
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "cd /opt/HiFate-bazi && git rev-parse --short HEAD"

sshpass -p "${SSH_PASSWORD}" ssh root@47.243.160.43 \
  "cd /opt/HiFate-bazi && git rev-parse --short HEAD"

# 2. 手动拉取代码
sshpass -p "${SSH_PASSWORD}" ssh root@<IP> \
  "cd /opt/HiFate-bazi && git pull gitee master"
```

---

### 问题 5：接口返回 502

**现象**：
```
HTTP/1.1 502 Bad Gateway
```

**排查步骤**：
```bash
# 1. 检查 Web 服务是否运行
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "docker ps | grep hifate-web"

# 2. 检查服务日志
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "docker logs --tail 100 hifate-web 2>&1 | tail -30"

# 3. 检查 Nginx 配置
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "docker logs --tail 50 hifate-nginx 2>&1"
```

---

## 📝 快速命令参考

### 一键部署

```bash
# 完整部署流程（从提交到部署）
cd /Users/zhoudt/Downloads/project/HiFate-bazi && \
git push origin master && \
git push gitee master && \
bash deploy/scripts/incremental_deploy_production.sh
```

### 快速健康检查

```bash
# 检查双机健康状态
echo "Node1:" && curl -s http://8.210.52.217:8001/health | head -1
echo "Node2:" && curl -s http://47.243.160.43:8001/health | head -1
```

### 查看服务日志

```bash
# Node1 Web 服务日志
sshpass -p "${SSH_PASSWORD}" ssh root@8.210.52.217 \
  "docker logs --tail 100 hifate-web 2>&1"

# Node2 Web 服务日志
sshpass -p "${SSH_PASSWORD}" ssh root@47.243.160.43 \
  "docker logs --tail 100 hifate-web 2>&1"
```

### 手动热更新

```bash
# 触发热更新
curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/trigger
curl -X POST http://47.243.160.43:8001/api/v1/hot-reload/trigger

# 验证热更新
curl http://8.210.52.217:8001/api/v1/hot-reload/verify
curl http://47.243.160.43:8001/api/v1/hot-reload/verify
```

---

## 📊 部署历史记录

| 日期 | 版本 | 内容 | 结果 |
|------|------|------|------|
| 2026-01-06 | 68fb76e | 注册流式端点到 gRPC 网关 | ✅ 成功 |

---

> **维护说明**：
> - 部署失败时，记录问题到[错误记录本](./error_records.md)
> - 定期更新本文档中的常见问题排查
> - 新增部署步骤时同步更新检查清单



