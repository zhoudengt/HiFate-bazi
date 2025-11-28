#!/bin/bash
# 数据库同步脚本
# 将本地数据库数据同步到生产环境

set -e

# 配置
LOCAL_MYSQL_HOST="127.0.0.1"
LOCAL_MYSQL_PORT="3306"
LOCAL_MYSQL_USER="root"
LOCAL_MYSQL_PASS="123456"
LOCAL_DB="hifate_bazi"

REMOTE_SERVER="root@123.57.216.15"
REMOTE_MYSQL_HOST="mysql"  # Docker 容器名
REMOTE_MYSQL_PORT="3306"
REMOTE_MYSQL_USER="root"
REMOTE_MYSQL_PASS="HiFate_Prod_2024!"
REMOTE_DB="hifate_bazi"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP_FILE="$SCRIPT_DIR/init_data.sql"

echo "=========================================="
echo "   HiFate 数据库同步工具"
echo "=========================================="
echo ""

# 选择操作
echo "请选择操作："
echo ""
echo "  1) 导出本地数据库（更新 init_data.sql）"
echo "  2) 同步到生产环境（上传并导入）"
echo "  3) 完整同步（导出 + 同步）"
echo "  4) 仅上传 SQL 文件（不导入）"
echo ""
read -p "选择 [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "📤 导出本地数据库..."
        mysqldump -h $LOCAL_MYSQL_HOST -P $LOCAL_MYSQL_PORT -u $LOCAL_MYSQL_USER -p$LOCAL_MYSQL_PASS \
            --default-character-set=utf8mb4 \
            --single-transaction \
            --routines \
            --triggers \
            $LOCAL_DB > "$DUMP_FILE"
        echo "✅ 导出完成: $DUMP_FILE"
        ls -lh "$DUMP_FILE"
        ;;
    2)
        echo ""
        echo "📤 上传 SQL 文件到服务器..."
        scp "$DUMP_FILE" $REMOTE_SERVER:/tmp/init_data.sql
        
        echo "📥 导入数据到 Docker MySQL..."
        ssh $REMOTE_SERVER "docker exec -i hifate-mysql mysql -u$REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PASS $REMOTE_DB < /tmp/init_data.sql"
        
        echo "🧹 清理临时文件..."
        ssh $REMOTE_SERVER "rm -f /tmp/init_data.sql"
        
        echo "✅ 同步完成！"
        ;;
    3)
        echo ""
        echo "📤 [1/3] 导出本地数据库..."
        mysqldump -h $LOCAL_MYSQL_HOST -P $LOCAL_MYSQL_PORT -u $LOCAL_MYSQL_USER -p$LOCAL_MYSQL_PASS \
            --default-character-set=utf8mb4 \
            --single-transaction \
            --routines \
            --triggers \
            $LOCAL_DB > "$DUMP_FILE"
        echo "✅ 导出完成"
        
        echo ""
        echo "📤 [2/3] 上传到服务器..."
        scp "$DUMP_FILE" $REMOTE_SERVER:/tmp/init_data.sql
        
        echo ""
        echo "📥 [3/3] 导入到 Docker MySQL..."
        ssh $REMOTE_SERVER "docker exec -i hifate-mysql mysql -u$REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PASS $REMOTE_DB < /tmp/init_data.sql"
        ssh $REMOTE_SERVER "rm -f /tmp/init_data.sql"
        
        echo ""
        echo "✅ 完整同步完成！"
        ;;
    4)
        echo ""
        echo "📤 上传 SQL 文件..."
        scp "$DUMP_FILE" $REMOTE_SERVER:/opt/HiFate-bazi/scripts/db/init_data.sql
        echo "✅ 上传完成"
        echo "手动导入命令："
        echo "  ssh $REMOTE_SERVER"
        echo "  docker exec -i hifate-mysql mysql -u$REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PASS $REMOTE_DB < /opt/HiFate-bazi/scripts/db/init_data.sql"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

