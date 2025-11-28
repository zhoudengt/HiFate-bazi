#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# 生成 gRPC Python 代码的脚本

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${PROJECT_ROOT}/proto"
OUTPUT_DIR="${PROJECT_ROOT}/proto/generated"

# 查找 Python 解释器（优先使用虚拟环境）
if [[ -f "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python3 > /dev/null 2>&1; then
    PYTHON="python3"
else
    echo "❌ 错误: 未找到 Python 解释器"
    exit 1
fi

# 创建输出目录
mkdir -p "${OUTPUT_DIR}"

# 生成 Python gRPC 代码
echo ">>> 生成 gRPC Python 代码..."
echo "   使用 Python: ${PYTHON}"

for proto_file in "${PROTO_DIR}"/*.proto; do
    if [[ -f "${proto_file}" ]]; then
        filename=$(basename "${proto_file}" .proto)
        echo "  处理: ${filename}.proto"
        
        "${PYTHON}" -m grpc_tools.protoc \
            --proto_path="${PROTO_DIR}" \
            --python_out="${OUTPUT_DIR}" \
            --grpc_python_out="${OUTPUT_DIR}" \
            "${proto_file}"
    fi
done

echo "✅ gRPC 代码生成完成！"
echo "   输出目录: ${OUTPUT_DIR}"

