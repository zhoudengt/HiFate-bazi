#!/bin/bash
# 同步配置表数据到生产环境并触发热更新
# 支持两种模式：
# 1. 在本地运行：从本地数据库导出，上传到生产环境执行
# 2. 在生产环境运行：从生产数据库导出，直接执行（用于同步本地配置到生产）

set -e

# 检测运行环境
if [ -f "/opt/HiFate-bazi/.env" ] || [ -d "/opt/HiFate-bazi/services" ]; then
    # 在生产环境运行
    RUNNING_ON_PRODUCTION=true
    PROD_DIR="/opt/HiFate-bazi"
    SQL_FILE="$PROD_DIR/scripts/db/sync_config_tables_temp.sql"
    MYSQL_PASSWORD="HiFate_Prod_2024!"
else
    # 在本地运行
    RUNNING_ON_PRODUCTION=false
    PROD_SERVER="root@123.57.216.15"
    PROD_DIR="/opt/HiFate-bazi"
    SQL_FILE="scripts/db/sync_config_tables_temp.sql"
    MYSQL_PASSWORD="HiFate_Prod_2024!"
fi

echo "=========================================="
echo "  同步配置表数据到生产环境"
echo "=========================================="
echo "运行环境: $([ "$RUNNING_ON_PRODUCTION" = true ] && echo "生产环境" || echo "本地环境")"
echo ""

# 检查 SQL 文件是否存在，如果不存在则自动生成
if [ ! -f "$SQL_FILE" ]; then
    echo "📝 SQL 文件不存在，正在自动生成..."
    if [ "$RUNNING_ON_PRODUCTION" = true ]; then
        cd "$PROD_DIR"
    fi
    python3 scripts/db/sync_config_tables_to_production.py --dry-run > /dev/null 2>&1
    if [ ! -f "$SQL_FILE" ]; then
        echo "❌ SQL 文件生成失败: $SQL_FILE"
        echo "   请手动运行: python3 scripts/db/sync_config_tables_to_production.py"
        exit 1
    fi
    echo "✅ SQL 文件已生成"
fi

if [ "$RUNNING_ON_PRODUCTION" = true ]; then
    # 在生产环境直接执行
    echo ""
    echo "🔄 执行 SQL 脚本..."
    cd "$PROD_DIR"
    docker exec -i $(docker ps --format '{{.Names}}' | grep -i mysql | head -1) \
        mysql -uroot -p$MYSQL_PASSWORD hifate_bazi < "$SQL_FILE" || {
        echo "❌ SQL 执行失败"
        exit 1
    }
    echo "✅ SQL 执行成功"
    
    echo ""
    echo "🔄 触发热更新..."
    HOT_RELOAD_RESULT=$(curl -s -X POST http://localhost:8001/api/v1/hot-reload/check || echo "failed")
else
    # 在本地运行，上传到生产环境
    echo "📤 上传 SQL 文件到生产服务器..."
    scp "$SQL_FILE" "$PROD_SERVER:/tmp/sync_config_tables_temp.sql" || {
        echo "❌ 上传失败"
        exit 1
    }
    echo "✅ 上传成功"
    
    echo ""
    echo "🔄 执行 SQL 脚本..."
    ssh "$PROD_SERVER" "cd $PROD_DIR && \
        docker exec -i \$(docker ps --format '{{.Names}}' | grep -i mysql | head -1) \
        mysql -uroot -p$MYSQL_PASSWORD hifate_bazi < /tmp/sync_config_tables_temp.sql && \
        rm /tmp/sync_config_tables_temp.sql" || {
        echo "❌ SQL 执行失败"
        exit 1
    }
    echo "✅ SQL 执行成功"
    
    echo ""
    echo "🔄 触发热更新..."
    HOT_RELOAD_RESULT=$(ssh "$PROD_SERVER" "curl -s -X POST http://localhost:8001/api/v1/hot-reload/check" || echo "failed")
fi

if echo "$HOT_RELOAD_RESULT" | grep -q "failed\|error\|Error"; then
    echo "⚠️  热更新可能失败，请手动检查"
    echo "   结果: $HOT_RELOAD_RESULT"
else
    echo "✅ 热更新已触发"
    echo "   结果: $HOT_RELOAD_RESULT"
fi

echo ""
echo "=========================================="
echo "✅ 部署完成"
echo "=========================================="
