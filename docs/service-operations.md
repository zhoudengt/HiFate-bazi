# 微服务运行与维护指南

本项目采用“主站 + 微服务”架构。统一管理方式如下。

---

## 1. 启动 / 停止所有服务

### 1.1 启动

修改 `config/services.env`（如需调整端口、严格模式等），然后执行：

```bash
chmod +x start_all_services.sh stop_all_services.sh  # 初次使用需要
./start_all_services.sh
```

效果：依次启动

- `bazi_core`（排盘）：`http://127.0.0.1:9001`
- `bazi_fortune`（大运流年）：`http://127.0.0.1:9002`
- `bazi_analyzer`（日柱分析）：`http://127.0.0.1:9003`
- `bazi_rule`（规则匹配）：`http://127.0.0.1:9004`
- `server/start.py` 主站（统一出口）：`http://127.0.0.1:8001`

每个服务（含主站）都会将日志输出到 `logs/<name>.log`，PID 写入 `logs/<name>.pid`。

### 1.2 停止

```bash
./stop_all_services.sh
```

按顺序停止主站和所有微服务，并清理 PID 文件。

---

## 2. 热更新 / 热加载

### 2.1 源码热更新

- 主站启动时会输出 `✓ 热更新管理器已启动`，表示正在监控：
  - 代码版本（仓库中的散列或版本文件）
  - 规则 / 内容版本（数据库 `rule_version` 等）
  - 源码改动（通过自定义策略）
- 常用做法：
  1. 修改代码 → 保存；
  2. 清理相关 Python 缓存（如有）；
  3. 执行 `./stop_all_services.sh && ./start_all_services.sh` 以确保所有服务载入最新代码；
     - 若仅修改主站，可执行 `pkill -F logs/web_app.pid && ./start_all_services.sh` 中的主站部分；
     - 若仅微服务改动，可象征性重启对应的 uvicorn 进程（日志和 PID 文件都在 `logs/`）。

> 注意：虽然热更新管理器能检测到部分改动并自动刷新，但在开发阶段仍建议显式重启服务以避免缓存干扰。

### 2.2 规则热更新

1. 执行规则导入脚本（可追加/覆盖）：
   ```bash
   .venv/bin/python scripts/import_marriage_rules.py --append --json-path docs/婚姻规则合并.json --pending-json docs/rule_pending_confirmation.json
   ```
2. `bazi-rule-service` 内部默认每 300 秒轮询数据库版本号。如需立即生效，可：
   - 观察主站日志中 `✓ 版本号检查器注册成功`、`✓ 热更新管理器已启动` 的输出；
   - 手动重启规则微服务（参见上一节的重启流程）。

---

## 3. 版本管理与配置

### 3.1 服务配置

- `config/services.env` 用于集中管理微服务地址、严格模式开关等。
- `.env`（如存在）可用于主站其它敏感配置；在脚本中 `source` 时注意不要提交敏感内容。

### 3.2 版本检查

主站在启动时会输出：

```
✓ 热更新管理器已启动
✓ 版本号检查器注册成功（规则、内容、源代码）
```

说明已经启用了版本监控机制。手动触发刷新可执行：

```bash
curl http://127.0.0.1:9004/healthz    # 检查规则服务健康
curl http://127.0.0.1:9001/healthz    # 检查核心服务健康
```

---

## 4. 常用接口（开发联调）

### 4.1 主站（8001）

```bash
# 规则匹配 + 排盘数据
curl -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male",
        "rule_types": ["marriage_stem_pattern"],
        "include_bazi": true
      }'
```

### 4.2 微服务

- `bazi-core`: `POST http://127.0.0.1:9001/core/calc-bazi`
- `bazi-fortune`: `POST http://127.0.0.1:9002/fortune/dayun-liunian`
- `bazi-analyzer`: `POST http://127.0.0.1:9003/analyzer/run`
- `bazi-rule`: `POST http://127.0.0.1:9004/rule/match`

每个服务都有 `GET /docs`（Swagger）和 `GET /healthz`。

---

## 5. 日志与故障排查

- 服务日志：`logs/<service>.log`
- 主站日志：`logs/web_app.log`
- 首次请求耗时较长通常是因为规则或缓存初始化，第二次后会快很多。
- 如果配置了 `*_STRICT=1`，微服务错误会直接抛出，便于定位；未开启时则自动回退到本地实现。

---

## 6. 注意事项

- 每次修改配置后执行 `./stop_all_services.sh && ./start_all_services.sh` 以确保更新生效。
- 生产部署可将上述脚本改成 systemd 或容器化方式，保持启动顺序一致即可。
- 如需扩展热更新策略、接入 CI/CD，请统一修改 `config/services.env` 与脚本。

--- 






## 7. 新增规则开发指南

以下流程适用于从 Excel → JSON → 数据库的快速规则开发，结合微服务环境：

1. **准备规则数据**
   - 在 Excel 或原始资料中整理待新增规则。
   - 使用既有脚本（如之前的 `婚姻算法公式.xlsx` → `docs/婚姻规则合并.json`）把表格转换为 JSON；开发阶段可直接复制一条字段结构作为模板。
   - 将新增规则写入 `docs/婚姻规则合并.json`（或其他约定文件），注意：  
     - `ID` 唯一且按类目分配；  
     - `筛选条件1/2`、`结果` 等字段与 `scripts/import_marriage_rules.py` 中的解析逻辑对应。


2. **更新待确认清单**
   - 对于暂时不确定、需要后续确认的规则，追加到 `docs/rule_pending_confirmation.json` 的 `rules_requiring_confirmation` 中，并写好 `clarification` 说明；  
   - 对于已掌握条件的规则，不要放入此列表，以免被跳过。

3. **运行导入脚本**
   - 本地先 dry-run，确认解析无误：  
     ```bash
     .venv/bin/python scripts/import_marriage_rules.py --dry-run --json-path docs/婚姻规则合并.json
     ```
     如果有 pending 或解析失败，会打印原因提示。
   - 确定后正式写库（需连接 MySQL/Redis）：  
     ```bash
     .venv/bin/python scripts/import_marriage_rules.py --append --json-path docs/婚姻规则合并.json --pending-json docs/rule_pending_confirmation.json
     ```
     `--append` 表示追加模式，不会覆盖已存在规则；如需清空后重建，可改用 `--reset`。

4. **验证微服务加载**
   - 首次导入后，`bazi-rule-service` 应自动检测到新规则并输出类似 `✓ 从数据库加载规则: xxx 条`；  
   - 如需立即生效，可重启规则微服务（或执行 `./stop_all_services.sh && ./start_all_services.sh`）。

5. **接口自测**
   - 直接调用规则微服务（或主站 `/api/v1/bazi/rules/match`），用适当的出生数据验证是否命中新增规则；  
   - 查看 `logs/bazi_rule.log` 或主站 `httpx` 请求日志确认流程走通。

6. **部署注意**
   - 上线前建议把最终 JSON + pending 清单纳入版本管理；  
   - 线上执行导入脚本前做好数据库备份，以便回滚；  
   - 导入成功后观察规则服务日志以及业务接口表现。

通过以上步骤，就能快速把新规则从资料整理推进到服务可用。必要时可以把脚本封装到 CI/CD 管道里，自动完成 dry-run、导入、微服务重启和验证。

---

以上即当前的服务运维指南，可根据环境继续补充。***

