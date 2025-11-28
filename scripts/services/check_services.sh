#!/usr/bin/env bash

# 服务健康检查脚本
# 用于快速检查所有微服务的运行状态

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务列表 (name:port)
SERVICES=(
    "bazi_core:9001"
    "bazi_fortune:9002"
    "bazi_analyzer:9003"
    "bazi_rule:9004"
    "fortune_analysis:9005"
    "payment_service:9006"
    "fortune_rule:9007"
    "web_app:8001"
)

echo "======================================"
echo "  微服务健康检查"
echo "======================================"
echo ""

# 检查端口是否被监听
check_port() {
  local port="$1"
  if command -v lsof > /dev/null 2>&1; then
    if lsof -iTCP:"${port}" -sTCP:LISTEN > /dev/null 2>&1; then
      return 0  # 端口在监听
    else
      return 1  # 端口未监听
    fi
  else
    if command -v netstat > /dev/null 2>&1; then
      if netstat -an 2>/dev/null | grep -q ":${port}.*LISTEN"; then
        return 0
      else
        return 1
      fi
    elif command -v ss > /dev/null 2>&1; then
      if ss -ln 2>/dev/null | grep -q ":${port}.*LISTEN"; then
        return 0
      else
        return 1
      fi
    else
      return 1
    fi
  fi
}

# 获取端口的 PID
get_port_pid() {
  local port="$1"
  if command -v lsof > /dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null | head -1
  else
    ps aux | grep -E "port ${port}|:${port}" | grep -v grep | awk '{print $2}' | head -1
  fi
}

# 统计
total_services=${#SERVICES[@]}
running_services=0
stopped_services=0

# 检查每个服务
for service_info in "${SERVICES[@]}"; do
  IFS=':' read -r name port <<< "$service_info"
  
  printf "%-20s [端口 %-5s] " "$name" "$port"
  
  if check_port "$port"; then
    pid=$(get_port_pid "$port")
    if [[ -n "$pid" ]]; then
      echo -e "${GREEN}✓ 运行中${NC} (PID: $pid)"
      ((running_services++))
    else
      echo -e "${GREEN}✓ 运行中${NC}"
      ((running_services++))
    fi
  else
    echo -e "${RED}✗ 未运行${NC}"
    ((stopped_services++))
    
    # 检查是否有残留的 PID 文件
    pid_file="${LOG_DIR}/${name}_${port}.pid"
    if [[ -f "$pid_file" ]]; then
      echo -e "  ${YELLOW}⚠ 发现残留 PID 文件: $pid_file${NC}"
    fi
    
    # 检查日志中的最后错误
    log_file="${LOG_DIR}/${name}_${port}.log"
    if [[ -f "$log_file" ]]; then
      last_error=$(grep -i "error\|exception\|failed" "$log_file" 2>/dev/null | tail -1)
      if [[ -n "$last_error" ]]; then
        echo -e "  ${YELLOW}最后错误: ${last_error:0:80}...${NC}"
      fi
    fi
  fi
done

echo ""
echo "======================================"
echo "  统计"
echo "======================================"
echo "总服务数: $total_services"
echo -e "运行中:   ${GREEN}$running_services${NC}"
echo -e "已停止:   ${RED}$stopped_services${NC}"

# 退出码
if [[ $stopped_services -gt 0 ]]; then
  echo ""
  echo -e "${YELLOW}⚠ 有服务未运行，请检查并启动${NC}"
  echo ""
  echo "启动所有服务:"
  echo "  ./start_all_services.sh"
  echo ""
  echo "查看服务日志:"
  echo "  tail -f logs/<service_name>_<port>.log"
  exit 1
else
  echo ""
  echo -e "${GREEN}✓ 所有服务运行正常${NC}"
  exit 0
fi

