# Docker 代码保护方案 - PyArmor 深度混淆

## 📋 概述

本项目使用 **PyArmor** 对 Python 源代码进行深度混淆和保护，确保：
- ✅ 原始源码在构建后完全删除
- ✅ 混淆后的代码无法反编译
- ✅ 运行时保护防止调试和逆向
- ✅ 代码完全不可见

## 🔒 保护级别

### PyArmor 配置

| 保护选项 | 值 | 说明 |
|---------|-----|------|
| `--obf-code=2` | 最高级别 | 代码逻辑完全混淆，无法直接阅读 |
| `--obf-mod=1` | 模块级别 | 模块结构混淆 |
| `--wrap-mode=1` | 包装模式 | 增强保护，包装函数调用 |
| `--restrict-mode=4` | 最高限制 | 防止调试、反编译、内存 dump |
| `--enable-rft=1` | 运行时保护 | 防止动态分析和调试 |
| `--advanced-mode=2` | 高级模式 | 最强保护级别 |

### 保护效果

- **原始源码**：构建后完全删除，镜像中不存在
- **混淆代码**：所有 Python 代码都被混淆，无法直接阅读
- **反编译**：无法使用 `uncompyle6` 等工具反编译
- **调试**：运行时保护防止调试器附加
- **内存 dump**：限制模式防止内存转储

## 🚀 使用方法

### 1. 构建保护后的镜像

```bash
# 构建镜像（自动进行 PyArmor 混淆）
docker build --platform linux/amd64 -t hifate-bazi:protected .

# 构建过程会显示：
# - PyArmor 混淆进度
# - 模块验证结果
# - 保护确认信息
```

### 2. 验证保护效果

```bash
# 使用验证脚本
chmod +x scripts/docker/verify_protection.sh
./scripts/docker/verify_protection.sh hifate-bazi:protected

# 验证脚本会检查：
# ✅ 原始 .py 文件是否已删除
# ✅ 混淆后的文件是否存在
# ✅ 混淆后的代码是否包含保护标记
# ✅ 模块是否可以正常导入
```

### 3. 测试运行

```bash
# 运行保护后的容器
docker run -d --name test -p 8001:8001 hifate-bazi:protected

# 验证服务是否正常
curl http://localhost:8001/health

# 尝试查看源码（应该看不到原始代码）
docker exec test find /app -name "*.py" ! -path "*/pyarmor_runtime/*"
# 应该返回空（没有原始 .py 文件）
```

### 4. 本地测试混淆（可选）

```bash
# 使用本地混淆脚本测试
chmod +x scripts/docker/obfuscate.sh
./scripts/docker/obfuscate.sh

# 混淆后的代码在 ./obfuscated 目录
cd obfuscated
python server/start.py
```

## 📊 验证保护效果

### 手动验证

```bash
# 1. 进入容器
docker exec -it <container_id> /bin/bash

# 2. 尝试查看源码（应该看不到）
cat /app/server/start.py
# 输出应该是混淆后的代码（包含 pyarmor 标记）

# 3. 检查原始文件（应该不存在）
find /app -name "*.py" ! -path "*/pyarmor_runtime/*" ! -path "*/site-packages/*"
# 应该返回空

# 4. 尝试反编译（应该失败）
python -c "import uncompyle6; ..."
# 应该无法反编译混淆后的代码
```

### 自动验证

```bash
# 使用验证脚本
./scripts/docker/verify_protection.sh <image_name>

# 输出示例：
# ✅ 原始 .py 文件已完全删除
# ✅ 发现 150 个混淆后的文件（pyarmor_runtime）
# ✅ 代码已混淆（包含 pyarmor 保护标记）
# ✅ 混淆后的模块可以正常导入
# ✅ 代码保护已成功应用！
```

## ⚠️ 注意事项

### 1. 原始代码备份

**重要**：混淆后原始代码会被删除，请确保：
- ✅ 代码已提交到 Git 仓库
- ✅ 有完整的版本控制
- ✅ 保留未混淆的开发版本

### 2. 性能影响

- **性能开销**：PyArmor 可能有 5-10% 的性能开销
- **启动时间**：首次导入混淆模块时可能稍慢（加载保护机制）
- **内存占用**：运行时保护会增加少量内存占用

### 3. 调试困难

- **无法直接调试**：混淆后的代码无法使用标准调试器
- **错误信息**：错误堆栈可能不够清晰
- **建议**：保留未混淆的开发版本用于调试

### 4. 平台限制

- **目标平台**：混淆后的代码只能在 `linux.x86_64` 平台运行
- **跨平台**：如需支持其他平台，需要重新混淆

### 5. 依赖问题

- **动态导入**：某些动态导入可能在混淆后失效
- **反射调用**：使用反射的代码可能需要特殊处理
- **第三方库**：第三方库不会被混淆（只混淆项目代码）

## 🔧 故障排查

### 问题1：模块导入失败

**症状**：
```
ImportError: cannot import name 'RuleService'
```

**原因**：
- PyArmor 混淆时可能遗漏了某些模块
- 动态导入路径不正确

**解决**：
1. 检查 Dockerfile 中的混淆目录列表
2. 确保所有需要混淆的目录都已包含
3. 检查 `--exclude` 选项是否正确

### 问题2：运行时错误

**症状**：
```
RuntimeError: PyArmor protection error
```

**原因**：
- 运行时保护检测到异常行为
- 可能被调试器或分析工具触发

**解决**：
1. 检查是否在调试环境中运行
2. 降低保护级别（不推荐）
3. 联系 PyArmor 技术支持

### 问题3：性能下降

**症状**：
- 响应时间明显增加
- CPU 使用率上升

**原因**：
- PyArmor 运行时保护的开销
- 混淆后的代码执行效率降低

**解决**：
1. 这是正常现象（5-10% 开销）
2. 如果影响过大，考虑降低保护级别
3. 优化代码逻辑，减少保护开销

## 📝 CI/CD 集成

### GitHub Actions

当前 CI/CD 流程已自动使用保护方案：

```yaml
# .github/workflows/build-and-push.yml
# 构建时会自动应用 PyArmor 保护
```

### 构建流程

1. **检出代码** → GitHub Actions
2. **安装依赖** → 包括 PyArmor
3. **混淆代码** → PyArmor 最高保护级别
4. **删除源码** → 确保没有原始文件
5. **构建镜像** → 推送到 ACR/GHCR
6. **部署** → 服务器拉取保护后的镜像

## 🔍 保护效果对比

### 混淆前（原始代码）

```python
def calculate_bazi(solar_date, solar_time, gender):
    """计算八字"""
    # 业务逻辑
    result = process_data(solar_date)
    return result
```

### 混淆后（保护代码）

```python
# 代码已被混淆，无法直接阅读
# 包含 pyarmor 保护标记和运行时检查
# 无法使用标准工具反编译
```

## 📚 相关文档

- [PyArmor 官方文档](https://pyarmor.readthedocs.io/)
- [Docker 构建文档](./Docker生产部署完整指南.md)
- [CI/CD 流程文档](../.github/workflows/build-and-push.yml)

## 🎯 最佳实践

1. **开发环境**：使用未混淆的代码，便于调试
2. **测试环境**：可以使用混淆后的代码，验证保护效果
3. **生产环境**：必须使用混淆后的代码，确保安全
4. **版本控制**：始终保留原始代码在 Git 仓库
5. **定期验证**：定期验证保护效果，确保没有源码泄露

---

**最后更新**：2025-01-15  
**维护者**：HiFate Team

