# 代码规范

## 数据库配置默认值
```python
# ✅ 正确：使用实际的数据库名
'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),

# ❌ 错误：使用过时的数据库名
'database': os.getenv('MYSQL_DATABASE', 'bazi_system'),
```
**相关错误**：见"问题1：数据库名配置错误"

## JSON 序列化
```python
# ✅ 正确：支持中文
json.dumps(data, ensure_ascii=False)

# ❌ 错误：中文被转义
json.dumps(data)  # 输出 \u4e2d\u6587
```

## 规则类型命名
```python
# ✅ 正确：使用英文小写（参考上方"类型映射"表格）
rule_type = 'career'
rule_type = 'children'

# ❌ 错误：使用中文或带前缀
rule_type = '事业'
rule_type = 'formula_career'  # 不要使用 formula_ 前缀
```
**相关错误**：见"问题3：规则类型不一致"、"问题4：前端类型标签缺失"

## 🚀 服务管理

### 启动服务
```bash
# 启动主服务
python3 server/start.py

# 或使用脚本
./start.sh
```

### 测试 API
```bash
# 测试 gRPC-Web 网关
curl -s -X POST 'http://127.0.0.1:8001/api/v1/bazi/formula-analysis' \
  -H 'Content-Type: application/json' \
  -d '{"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"}'
```

### 查看日志
```bash
tail -f logs/server_8001.log
```

## 📦 Git 提交规范

### Commit Message 格式
```
[类型] 简短描述

- 修改文件：列出文件
- 功能说明：详细说明
- 测试情况：测试结果
```

### 类型标签
- `[新增]` - 新功能/新规则
- `[修复]` - Bug修复
- `[优化]` - 性能优化
- `[重构]` - 代码重构
- `[规则]` - 规则相关变更
- `[配置]` - 配置修改

## 📖 Gitee 仓库

| 项目 | 值 |
|------|-----|
| **仓库地址** | https://gitee.com/zhoudengtang/hifate-prod.git |
| **本地 remote** | gitee |
| **默认分支** | master |

### 提交流程
```bash
git add .
git commit -m "[类型] 描述"
git push gitee master
```

### 部署到生产
```bash
./deploy.sh  # 选择 1) 完整部署
```

**📖 详细部署文档**：`docs/Docker生产部署完整指南.md`

## 🐳 Docker 基础镜像优化

### 📋 原理

使用预构建的基础镜像（包含所有 Python 依赖包和框架），大幅加速部署：

```
传统方式：每次部署都安装依赖（5-10分钟）
优化方式：基础镜像已含所有包和框架，只需复制代码（10-20秒）
```

**核心优化**：
- ✅ 所有 Python 包和框架预装在基础镜像中
- ✅ 部署时只需复制代码，无需安装依赖
- ✅ 基础镜像包含：FastAPI、gRPC、数据库驱动、图像处理库等

### 🚀 使用流程

**1. 首次构建基础镜像**（仅需一次，约 5-10 分钟）

```bash
./scripts/docker/build_base.sh
```

**2. 检查基础镜像状态**

```bash
./scripts/docker/check_base.sh
```

**3. 正常部署**（快速，10-20秒）

```bash
docker compose up -d --build web
```

### ⚠️ 何时需要重建基础镜像

| 场景 | 是否需要重建 | 说明 |
|------|------------|------|
| 修改代码 | ❌ 不需要 | 直接部署即可 |
| 修改 requirements.txt | ✅ **必须重建** | 依赖变更 |
| 修改 Dockerfile.base | ✅ 需要重建 | 基础镜像配置变更 |

### 🔒 安全机制

1. **跨平台兼容**：使用 `--platform linux/amd64` 确保 Mac M1/Intel 都能构建
2. **保险层**：应用 Dockerfile 会再次执行 `pip install`，确保依赖完整
3. **自动检查**：`check_base.sh` 会检测 requirements.txt 是否变更
4. **依赖验证**：基础镜像构建时验证核心框架（FastAPI、gRPC、数据库驱动等）
5. **健康检查**：基础镜像包含健康检查，确保可用性

### 📊 性能对比

| 场景 | 传统方式 | 基础镜像 | 提升 |
|------|---------|---------|------|
| 首次部署 | 10-15分钟 | 5-10分钟（构建基础镜像） | 1次性 |
| 代码更新 | 1-2分钟 | **10-20秒** | **6-12倍** |
| 依赖更新 | 10-15分钟 | 5-10分钟（重建基础镜像） | 1次性 |

### 🛠️ 维护命令

```bash
# 构建基础镜像
./scripts/docker/build_base.sh

# 检查是否需要更新
./scripts/docker/check_base.sh

# 查看基础镜像信息
docker images hifate-base

# 删除旧版本（可选）
docker rmi hifate-base:20241128
```

