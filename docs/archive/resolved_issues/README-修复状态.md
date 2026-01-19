# 🔧 修复状态和快速检查

## 📊 当前状态

运行以下命令快速检查：

```bash
python3 scripts/check_status.py
```

## 🔄 持续测试（自动）

运行以下命令持续测试直到问题解决：

```bash
python3 scripts/test_until_fixed.py
```

脚本会：
- 每 10 秒自动测试一次
- 每 5 次自动清除缓存
- 自动对比本地和生产环境
- 检测到问题解决后自动停止

## 🚀 立即修复

如果问题未解决，执行以下命令：

```bash
scp scripts/temp_rules_export.sql root@8.210.52.217:/tmp/rules_import.sql && \
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -p${SSH_PASSWORD} hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check"
```

然后等待 5 秒后验证：

```bash
sleep 5 && python3 scripts/check_status.py
```

## ✅ 问题解决标准

- 生产环境匹配数 ≥ 50 条（本地 63 条，允许 10% 差异）
- 事业规则 ≥ 9 条（当前 0 条）
- 身体规则 ≥ 15 条（当前 5 条）
- 总评规则 ≥ 6 条（当前 1 条）

