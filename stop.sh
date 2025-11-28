#!/bin/bash
# HiFate-bazi 服务停止脚本（快捷入口）
# 实际脚本位于 scripts/services/

cd "$(dirname "$0")"
./scripts/services/stop_all_services.sh "$@"

