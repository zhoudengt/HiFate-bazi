# 支付环境切换

## 原理

通过 `is_active` 字段控制环境切换。每个支付方式可以同时配置多个环境（sandbox/production），通过设置 `is_active=1` 来激活对应环境。

## 切换命令

### 查看当前激活环境

```bash
python3 scripts/db/manage_payment_configs.py get-active-environment linepay
```

### 切换环境

```bash
# 切换到 sandbox
python3 scripts/db/manage_payment_configs.py set-active-environment linepay sandbox

# 切换到 production
python3 scripts/db/manage_payment_configs.py set-active-environment linepay production
```

## 注意事项

1. 切换环境前确保目标环境的所有配置已设置
2. 同一支付方式的同一配置键只能有一条 `is_active=1` 的记录
3. 切换后会自动清除缓存并触发热更新
