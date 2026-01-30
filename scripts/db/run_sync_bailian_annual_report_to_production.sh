#!/bin/bash
# 将 service_configs 的 BAILIAN_ANNUAL_REPORT_APP_ID 同步到生产 MySQL
# 生产 MySQL 在 Node1 Docker 内，需通过 SSH + docker exec 执行。
# 详见 docs/knowledge_base/deployment_guide.md

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SSH_HOST="${PROD_SSH_HOST:-8.210.52.217}"
SSH_USER="${PROD_SSH_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-Yuanqizhan@163}"
MYSQL_CONTAINER="hifate-mysql-master"
DB_NAME="hifate_bazi"

echo "同步 BAILIAN_ANNUAL_REPORT_APP_ID 到生产 ($SSH_HOST) ..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${SSH_USER}@${SSH_HOST}" \
  "docker exec -i $MYSQL_CONTAINER mysql -uroot -p'$MYSQL_PASSWORD' $DB_NAME" \
  < "$SCRIPT_DIR/sync_bailian_annual_report_app_id_to_production.sql"
echo "完成。请检查上方 SELECT 输出确认 config_value 正确。"
