## Rules Update Workflow

### 1. Prepare Source Data
- Convert new Excel sheets under `docs/` to JSON.  
  `docs/副本婚姻算法公式11,13.xlsx` → `docs/副本婚姻算法公式11,13.json` (use the conversion script we created).
- Decide priority order when multiple JSON files exist (later files override earlier ones on duplicate `ID`/`rule_code`).

### 2. Extend the Parser (if needed)
- Main parser: `scripts/import_marriage_rules.py`.
- Check `CONDITION_HANDLERS` mapping for `筛选条件1` → handler function.  
  Add/extend handlers such as `handle_ten_gods`, `handle_element_total`, `handle_day_pillar`, etc.
- Common utilities:
  - `parse_chinese_numeral`, `parse_quantity_spec`
  - `make_pillar_relation`, `make_any_pillar_equals`, etc.
- If new condition keys are introduced (e.g. `element_total`, `liunian_relation`), ensure corresponding matchers exist in `server/engines/rule_condition.py`.

### 3. Dry-Run Validation
- Command example:
  ```
  .venv/bin/python scripts/import_marriage_rules.py \
    --dry-run \
    --json-path docs/婚姻规则合并.json \
    --json-path docs/副本婚姻算法公式11,13.json
  ```
- Inspect output:
  - `parsed` count → rules ready to import.
  - `skipped` list → rules needing clarification or new logic.

### 4. Maintain Pending List
- Dry-run regenerates `docs/副本婚姻规则待确认.json` automatically.
- Each entry includes `reason`; use it to schedule future parser extensions.
- Keep legacy `docs/rule_pending_confirmation.json` only for reference; main list is the new file.

### 5. Import into Database
- Make sure MySQL/Redis config works (`server/config/mysql_config.py`, Redis host).
- Append-mode import:
  ```
  .venv/bin/python scripts/import_marriage_rules.py \
    --append \
    --json-path docs/婚姻规则合并.json \
    --json-path docs/副本婚姻算法公式11,13.json \
    --pending-json docs/副本婚姻规则待确认.json
  ```
- Later files override earlier duplicates (same `ID` or `rule_code`).
- Tables touched: `bazi_rules`, `bazi_rule_matches`, `cache_stats`.

### 6. Verify Import
- SQL sample:
  ```
  SELECT COUNT(*) FROM bazi_rules
  WHERE source = '副本婚姻算法公式11,13.json';
  ```
- Or run in Python:
  ```
  from server.config.mysql_config import get_mysql_connection
  conn = get_mysql_connection()
  with conn.cursor() as cur:
      cur.execute("SELECT COUNT(*) FROM bazi_rules WHERE source=%s",
                  ('副本婚姻算法公式11,13.json',))
      print(cur.fetchone()[0])
  ```
- Cross-check `docs/副本婚姻规则待确认.json` to ensure only unresolved rules remain.

### 7. Regression & Documentation
- Optionally run examples (`src/bazi_calculator.py`) to confirm rule hit output.
- Update docs when new condition types or workflows are introduced.

