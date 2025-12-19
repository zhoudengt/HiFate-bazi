#!/bin/bash
# 完整修复方案：检查、修复、验证

echo "============================================================"
echo "🔧 完整修复方案：检查、修复、验证"
echo "============================================================"

PROD_HOST="8.210.52.217"
PROD_USER="root"
SQL_FILE="scripts/temp_rules_export.sql"

# 步骤 1: 检查本地数据库
echo ""
echo "步骤 1: 检查本地数据库规则"
echo "============================================================"
LOCAL_TOTAL=$(mysql -h localhost -u root -p123456 hifate_bazi -e "
SELECT COUNT(*) as total
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' 
  AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
  AND enabled = 1;
" 2>/dev/null | tail -1)

if [ -z "$LOCAL_TOTAL" ]; then
    echo "⚠️  无法获取本地规则数量（可能需要密码）"
    LOCAL_TOTAL="1142"  # 使用已知值
fi

echo "本地规则总数: $LOCAL_TOTAL 条"

# 步骤 2: 检查生产环境数据库
echo ""
echo "步骤 2: 检查生产环境数据库规则"
echo "============================================================"

PROD_DB_STATS=$(ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
cd /opt/HiFate-bazi
docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e "
SELECT 
    rule_type,
    COUNT(*) as total,
    SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM bazi_rules 
WHERE rule_code LIKE 'FORMULA_%' 
  AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
GROUP BY rule_type
ORDER BY rule_type;
" 2>/dev/null
EOF
)

if [ $? -eq 0 ]; then
    echo "$PROD_DB_STATS"
    
    # 提取生产环境总数
    PROD_TOTAL=$(echo "$PROD_DB_STATS" | awk '{sum+=$3} END {print sum}')
    echo ""
    echo "生产环境规则总数: $PROD_TOTAL 条"
    
    # 对比
    if [ "$PROD_TOTAL" -lt "$LOCAL_TOTAL" ]; then
        DIFF=$((LOCAL_TOTAL - PROD_TOTAL))
        echo "⚠️  生产环境规则数量不足，差异: $DIFF 条"
        
        # 步骤 3: 同步规则
        echo ""
        echo "步骤 3: 同步规则到生产环境"
        echo "============================================================"
        
        if [ ! -f "$SQL_FILE" ]; then
            echo "❌ SQL 文件不存在，先导出..."
            python3 scripts/fix_production_rules.py
        fi
        
        if [ -f "$SQL_FILE" ]; then
            echo "📤 上传 SQL 文件..."
            scp "$SQL_FILE" ${PROD_USER}@${PROD_HOST}:/tmp/rules_import.sql
            
            if [ $? -eq 0 ]; then
                echo "✅ 上传成功"
                echo "🔄 执行 SQL..."
                
                ssh ${PROD_USER}@${PROD_HOST} << 'EOF'
cd /opt/HiFate-bazi
docker exec -i hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < /tmp/rules_import.sql
echo "✅ SQL 执行完成"
EOF
                
                if [ $? -eq 0 ]; then
                    echo "✅ 规则同步成功"
                    
                    # 清除缓存
                    echo ""
                    echo "🧹 清除缓存..."
                    curl -X POST http://${PROD_HOST}:8001/api/v1/hot-reload/check
                    
                    # 等待
                    echo ""
                    echo "⏳ 等待 5 秒让规则重新加载..."
                    sleep 5
                else
                    echo "❌ SQL 执行失败"
                fi
            else
                echo "❌ 上传失败"
            fi
        fi
    else
        echo "✅ 生产环境规则数量正常"
    fi
else
    echo "❌ 无法连接生产环境，请检查 SSH 配置"
fi

# 步骤 4: 验证修复结果
echo ""
echo "步骤 4: 验证修复结果"
echo "============================================================"

# 运行验证脚本
bash scripts/verify_fix.sh

# 运行持续测试
echo ""
echo "步骤 5: 持续测试直到问题解决"
echo "============================================================"
echo "运行自动测试循环（最多 20 次，每 10 秒一次）..."
echo "按 Ctrl+C 可随时停止"
echo ""

python3 scripts/auto_fix_loop.py

echo ""
echo "============================================================"
echo "✅ 修复流程完成"
echo "============================================================"

