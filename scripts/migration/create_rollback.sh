#!/bin/bash
# ============================================
# 创建数据库回滚脚本
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLLBACK_DIR="$PROJECT_ROOT/migration/rollback"

# 创建回滚目录
mkdir -p "$ROLLBACK_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   创建数据库回滚脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 获取描述
read -p "请输入回滚描述（简短说明）: " description
if [ -z "$description" ]; then
    echo -e "${RED}❌ 描述不能为空${NC}"
    exit 1
fi

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="rollback_${TIMESTAMP}_${description// /_}.sql"
FILEPATH="$ROLLBACK_DIR/$FILENAME"

# 创建回滚脚本模板
cat > "$FILEPATH" << EOF
-- ============================================
-- 回滚脚本: $FILENAME
-- 创建时间: $(date '+%Y-%m-%d %H:%M:%S')
-- 描述: $description
-- ============================================

-- 开始事务
START TRANSACTION;

-- ============================================
-- 回滚操作
-- ============================================

-- TODO: 在这里添加回滚 SQL 语句
-- 示例：
-- DROP TABLE IF EXISTS \`new_table\`;
-- ALTER TABLE \`existing_table\` DROP COLUMN IF EXISTS \`new_column\`;
-- ALTER TABLE \`existing_table\` DROP INDEX IF EXISTS \`new_index\`;

-- ============================================
-- 验证回滚结果（可选）
-- ============================================

-- SELECT * FROM information_schema.tables WHERE table_schema = DATABASE();

-- 提交事务
COMMIT;

-- 回滚完成
-- 执行时间: $(date '+%Y-%m-%d %H:%M:%S')
EOF

echo -e "${GREEN}✅ 回滚脚本已创建${NC}"
echo ""
echo "文件路径: $FILEPATH"
echo ""
echo -e "${YELLOW}⚠️  请编辑脚本，添加具体的回滚 SQL 语句${NC}"
echo ""

