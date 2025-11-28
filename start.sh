#!/bin/bash
# HiFate-bazi 服务启动脚本（快捷入口）
# 实际脚本位于 scripts/services/

cd "$(dirname "$0")"
./scripts/services/start_all_services.sh "$@"

