#!/bin/bash
# 测试 smart-analyze-stream 接口的快速脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
PROD_URL="http://8.210.52.217:8001"
LOCAL_URL="http://localhost:8001"

# 选择环境
echo "选择测试环境："
echo "1) 生产环境 ($PROD_URL)"
echo "2) 本地环境 ($LOCAL_URL)"
read -p "请选择 (1/2): " env_choice

if [ "$env_choice" = "1" ]; then
    BASE_URL=$PROD_URL
    ENV_NAME="生产环境"
else
    BASE_URL=$LOCAL_URL
    ENV_NAME="本地环境"
fi

echo -e "${GREEN}使用环境: $ENV_NAME ($BASE_URL)${NC}\n"

# 检查服务器状态
echo "1. 检查服务器状态..."
if curl -s -f "${BASE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ 服务器运行正常${NC}"
else
    echo -e "${RED}❌ 服务器无法访问，请检查服务器是否运行${NC}"
    exit 1
fi

# 选择场景
echo ""
echo "选择测试场景："
echo "1) 场景1：点击选择项（需要生辰信息）"
echo "2) 场景2：点击预设问题（从会话缓存获取生辰信息）"
echo "3) 默认场景（兼容旧接口）"
read -p "请选择 (1/2/3): " scenario_choice

# 生成参数
case $scenario_choice in
    1)
        # 场景1
        echo ""
        echo "场景1：点击选择项"
        read -p "分类 (默认: 事业财富): " category
        category=${category:-事业财富}
        read -p "出生年份 (默认: 1990): " year
        year=${year:-1990}
        read -p "出生月份 (默认: 5): " month
        month=${month:-5}
        read -p "出生日期 (默认: 15): " day
        day=${day:-15}
        read -p "出生时辰 (默认: 14): " hour
        hour=${hour:-14}
        read -p "性别 (默认: male): " gender
        gender=${gender:-male}
        read -p "用户ID (默认: test_user_001): " user_id
        user_id=${user_id:-test_user_001}
        
        # 使用 Python 生成正确编码的 URL
        URL=$(python3 -c "
import urllib.parse
params = {
    'category': '$category',
    'year': $year,
    'month': $month,
    'day': $day,
    'hour': $hour,
    'gender': '$gender',
    'user_id': '$user_id'
}
print('${BASE_URL}/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))
")
        ;;
    2)
        # 场景2
        echo ""
        echo "场景2：点击预设问题"
        read -p "分类 (默认: 事业财富): " category
        category=${category:-事业财富}
        read -p "问题 (默认: 我今年的事业运势如何？): " question
        question=${question:-我今年的事业运势如何？}
        read -p "用户ID (默认: test_user_001): " user_id
        user_id=${user_id:-test_user_001}
        
        URL=$(python3 -c "
import urllib.parse
params = {
    'category': '$category',
    'question': '$question',
    'user_id': '$user_id'
}
print('${BASE_URL}/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))
")
        ;;
    3)
        # 默认场景
        echo ""
        echo "默认场景：兼容旧接口"
        read -p "问题 (默认: 我今年的事业运势如何？): " question
        question=${question:-我今年的事业运势如何？}
        read -p "出生年份 (默认: 1990): " year
        year=${year:-1990}
        read -p "出生月份 (默认: 5): " month
        month=${month:-5}
        read -p "出生日期 (默认: 15): " day
        day=${day:-15}
        read -p "出生时辰 (默认: 14): " hour
        hour=${hour:-14}
        read -p "性别 (默认: male): " gender
        gender=${gender:-male}
        read -p "用户ID (可选，默认: test_user_001): " user_id
        user_id=${user_id:-test_user_001}
        
        URL=$(python3 -c "
import urllib.parse
params = {
    'question': '$question',
    'year': $year,
    'month': $month,
    'day': $day,
    'hour': $hour,
    'gender': '$gender',
    'user_id': '$user_id'
}
print('${BASE_URL}/api/v1/smart-fortune/smart-analyze-stream?' + urllib.parse.urlencode(params, encoding='utf-8'))
")
        ;;
    *)
        echo -e "${RED}无效的选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}生成的 URL:${NC}"
echo "$URL"
echo ""

# 执行请求
echo -e "${GREEN}开始发送请求...${NC}"
echo -e "${YELLOW}（按 Ctrl+C 停止）${NC}\n"

curl -N -v "$URL" 2>&1 | while IFS= read -r line; do
    if [[ $line == *"event:"* ]]; then
        echo -e "${GREEN}$line${NC}"
    elif [[ $line == *"data:"* ]]; then
        echo -e "${YELLOW}$line${NC}"
    else
        echo "$line"
    fi
done
