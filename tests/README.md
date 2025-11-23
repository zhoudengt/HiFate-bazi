# 测试文件说明

本目录包含项目的所有测试脚本，按功能分类组织。

## 📁 目录结构

```
tests/
├── api/              # API 接口测试
├── features/         # 功能测试
├── scripts/          # Shell 测试脚本
└── automation/       # 自动化测试（Selenium等）
```

## 📋 文件说明

### API 测试 (`api/`)

| 文件 | 说明 |
|------|------|
| `test_curated_api.py` | 测试精选接口和限流功能 |
| `test_fortune_display.py` | 测试大运流年流月显示接口 |

**使用方法：**
```bash
# 确保服务已启动
./start_all_services.sh

# 运行测试
python tests/api/test_curated_api.py
python tests/api/test_fortune_display.py
```

### 功能测试 (`features/`)

| 文件 | 说明 |
|------|------|
| `test_payment.py` | 支付功能测试（Stripe等） |
| `test_wangshuai.py` | 旺衰分析功能测试 |

**使用方法：**
```bash
# 运行支付测试
python tests/features/test_payment.py

# 运行旺衰分析测试
python tests/features/test_wangshuai.py
```

### Shell 脚本 (`scripts/`)

| 文件 | 说明 |
|------|------|
| `test_payment_simple.sh` | 简单支付测试脚本 |
| `test_payment_complete.sh` | 完整支付测试脚本 |
| `test_stripe_complete.sh` | Stripe 支付测试 |
| `test_microservice_logs.sh` | 微服务日志检查 |

**使用方法：**
```bash
# 添加执行权限
chmod +x tests/scripts/*.sh

# 运行测试
./tests/scripts/test_payment_simple.sh
./tests/scripts/test_microservice_logs.sh
```

### 自动化测试 (`automation/`)

| 文件 | 说明 |
|------|------|
| `auto_browser_test.py` | 浏览器自动化测试（Selenium） |
| `auto_test_fortune.py` | 运势自动化测试 |
| `interactive_browser_test.py` | 交互式浏览器测试 |

**前置要求：**
- 安装 Chrome 浏览器
- 安装 ChromeDriver: `brew install chromedriver` (macOS)
- 安装 Selenium: `pip install selenium`

**使用方法：**
```bash
python tests/automation/auto_browser_test.py
```

## 🔧 运行所有测试

```bash
# 运行所有 Python 测试
find tests -name "test_*.py" -exec python {} \;

# 运行所有 Shell 测试
find tests/scripts -name "*.sh" -exec bash {} \;
```

## 📝 注意事项

1. **路径引用**：所有测试文件已配置正确的项目根目录路径，可以从 `tests/` 子目录直接运行
2. **服务依赖**：大部分测试需要服务已启动（`./start_all_services.sh`）
3. **环境变量**：某些测试需要配置环境变量（如 `STRIPE_SECRET_KEY`）
4. **Token 文件**：部分测试会读取 `.token` 文件（如果存在）

## 🗑️ 已删除的临时文件

以下临时调试脚本已删除（问题已解决）：
- `test_wangshuai_fix.py`
- `test_fix_verification.py`
- `test_filter.py`
- `test_frontend_filter.py`
- `test_frontend_display.py`
- `test_fortune_debug.py`
- `test_fortune_click.py`
- `test_xiaoyun_click.py`
- `test_xiaoyun.py`
- `test_dayun_liunian_match.py`
- `test_dayun_with_year.py`
- `test_new_features.py`

---

**最后更新：** 2025-01-21

