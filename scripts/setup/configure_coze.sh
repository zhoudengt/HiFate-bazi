#!/bin/bash
# Coze Bot 配置脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=========================================="
echo "Coze Bot 配置助手"
echo "=========================================="
echo ""

# 检查 .env 文件是否存在
ENV_FILE="${PROJECT_ROOT}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    echo "创建 .env 文件..."
    touch "${ENV_FILE}"
fi

# 读取现有配置
if [ -f "${ENV_FILE}" ]; then
    source "${ENV_FILE}" 2>/dev/null || true
fi

# 获取 Access Token
echo "步骤 1: 配置 Coze Access Token"
echo "----------------------------------------"
echo "请在 Coze 平台获取 Access Token："
echo "1. 访问 https://www.coze.cn"
echo "2. 登录账号"
echo "3. 个人设置 → API 密钥 → 创建新的 Token"
echo "4. 复制 Token（格式：pat_xxxxxxxxxxxxx）"
echo ""
read -p "请输入 Coze Access Token（留空使用现有值）: " input_token

if [ -n "${input_token}" ]; then
    COZE_ACCESS_TOKEN="${input_token}"
    # 更新 .env 文件
    if grep -q "COZE_ACCESS_TOKEN" "${ENV_FILE}" 2>/dev/null; then
        # 使用 sed 更新（macOS 和 Linux 兼容）
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^COZE_ACCESS_TOKEN=.*|COZE_ACCESS_TOKEN=${COZE_ACCESS_TOKEN}|" "${ENV_FILE}"
        else
            sed -i "s|^COZE_ACCESS_TOKEN=.*|COZE_ACCESS_TOKEN=${COZE_ACCESS_TOKEN}|" "${ENV_FILE}"
        fi
    else
        echo "COZE_ACCESS_TOKEN=${COZE_ACCESS_TOKEN}" >> "${ENV_FILE}"
    fi
    echo "✅ Access Token 已更新"
else
    if [ -n "${COZE_ACCESS_TOKEN}" ]; then
        echo "✅ 使用现有 Access Token: ${COZE_ACCESS_TOKEN:0:20}..."
    else
        echo "⚠️  未设置 Access Token"
    fi
fi

echo ""

# 获取 Bot ID
echo "步骤 2: 配置 Coze Bot ID"
echo "----------------------------------------"
echo "请在 Coze 平台获取 Bot ID："
echo "1. 在 Coze 平台创建 Bot（如果没有）"
echo "2. 在 Bot 详情页面查看 Bot ID（数字格式）"
echo "3. 复制 Bot ID"
echo ""
read -p "请输入 Coze Bot ID（留空使用现有值）: " input_bot_id

if [ -n "${input_bot_id}" ]; then
    COZE_BOT_ID="${input_bot_id}"
    # 更新 .env 文件
    if grep -q "COZE_BOT_ID" "${ENV_FILE}" 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^COZE_BOT_ID=.*|COZE_BOT_ID=${COZE_BOT_ID}|" "${ENV_FILE}"
        else
            sed -i "s|^COZE_BOT_ID=.*|COZE_BOT_ID=${COZE_BOT_ID}|" "${ENV_FILE}"
        fi
    else
        echo "COZE_BOT_ID=${COZE_BOT_ID}" >> "${ENV_FILE}"
    fi
    echo "✅ Bot ID 已更新"
else
    if [ -n "${COZE_BOT_ID}" ]; then
        echo "✅ 使用现有 Bot ID: ${COZE_BOT_ID}"
    else
        echo "⚠️  未设置 Bot ID"
    fi
fi

echo ""

# 同时更新 config/services.env
SERVICES_ENV="${PROJECT_ROOT}/config/services.env"
if [ -f "${SERVICES_ENV}" ]; then
    echo "步骤 3: 更新 config/services.env"
    echo "----------------------------------------"
    
    if [ -n "${COZE_ACCESS_TOKEN}" ]; then
        if grep -q "COZE_ACCESS_TOKEN" "${SERVICES_ENV}" 2>/dev/null; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^export COZE_ACCESS_TOKEN=.*|export COZE_ACCESS_TOKEN=\"${COZE_ACCESS_TOKEN}\"|" "${SERVICES_ENV}"
            else
                sed -i "s|^export COZE_ACCESS_TOKEN=.*|export COZE_ACCESS_TOKEN=\"${COZE_ACCESS_TOKEN}\"|" "${SERVICES_ENV}"
            fi
        else
            echo "export COZE_ACCESS_TOKEN=\"${COZE_ACCESS_TOKEN}\"" >> "${SERVICES_ENV}"
        fi
    fi
    
    if [ -n "${COZE_BOT_ID}" ]; then
        if grep -q "COZE_BOT_ID" "${SERVICES_ENV}" 2>/dev/null; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|^export COZE_BOT_ID=.*|export COZE_BOT_ID=\"${COZE_BOT_ID}\"|" "${SERVICES_ENV}"
            else
                sed -i "s|^export COZE_BOT_ID=.*|export COZE_BOT_ID=\"${COZE_BOT_ID}\"|" "${SERVICES_ENV}"
            fi
        else
            echo "export COZE_BOT_ID=\"${COZE_BOT_ID}\"" >> "${SERVICES_ENV}"
        fi
    fi
    
    echo "✅ config/services.env 已更新"
fi

echo ""
echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "当前配置："
echo "  COZE_ACCESS_TOKEN: ${COZE_ACCESS_TOKEN:0:20}..."
echo "  COZE_BOT_ID: ${COZE_BOT_ID}"
echo ""
echo "下一步："
echo "1. 确保在 Coze 平台已创建 Bot 并配置提示词"
echo "2. 重启服务：bash stop_all_services.sh && bash start_all_services.sh"
echo "3. 运行测试：python scripts/test_coze_config.py"
echo ""

