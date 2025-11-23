#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"

# 通过端口查找进程 PID
find_pid_by_port() {
  local port="$1"
  if command -v lsof > /dev/null 2>&1; then
    lsof -ti:"${port}" 2>/dev/null | head -1
  elif command -v netstat > /dev/null 2>&1; then
    netstat -anp 2>/dev/null | grep ":${port}.*LISTEN" | awk '{print $7}' | cut -d'/' -f1 | head -1
  elif command -v ss > /dev/null 2>&1; then
    ss -lnp 2>/dev/null | grep ":${port}" | grep -oP 'pid=\K\d+' | head -1
  else
    # 如果都没有，尝试通过进程名查找
    ps aux | grep -E "uvicorn.*port ${port}|server/start.py" | grep -v grep | awk '{print $2}' | head -1
  fi
}

# 通过进程名查找 PID
find_pid_by_name() {
  local name="$1"
  ps aux | grep -E "${name}" | grep -v grep | awk '{print $2}' | head -1
}

stop_service() {
  local name="$1"
  local port="$2"
  local pid_file="${LOG_DIR}/${name}_${port}.pid"
  local pid=""

  # 方法1: 从 PID 文件读取
  if [[ -f "${pid_file}" ]]; then
    pid="$(cat "${pid_file}")"
    if ! ps -p "${pid}" > /dev/null 2>&1; then
      # PID 文件存在但进程不存在，清理残留文件
      rm -f "${pid_file}"
      pid=""
    fi
  fi

  # 方法2: 如果 PID 文件不存在或无效，通过端口查找
  if [[ -z "${pid}" ]]; then
    pid="$(find_pid_by_port "${port}")"
  fi

  # 方法3: 如果通过端口找不到，尝试通过进程名查找
  if [[ -z "${pid}" ]]; then
    if [[ "${name}" == "web_app" ]]; then
      pid="$(find_pid_by_name "server/start.py")"
    elif [[ "${name}" == "fortune_analysis" ]]; then
      pid="$(find_pid_by_name "services/fortune_analysis/grpc_server.py")"
    elif [[ "${name}" == "fortune_rule" ]]; then
      pid="$(find_pid_by_name "services/fortune_rule/grpc_server.py")"
    elif [[ "${name}" == "payment_service" ]]; then
      pid="$(find_pid_by_name "services/payment_service/grpc_server.py")"
    else
      pid="$(find_pid_by_name "services.${name}.main")"
    fi
  fi

  # 如果还是找不到，说明服务未运行
  if [[ -z "${pid}" ]]; then
    return
  fi

  # 验证 PID 是否真的在运行
  if ! ps -p "${pid}" > /dev/null 2>&1; then
    return
  fi

  echo ">>> 停止 ${name}（端口 ${port}，PID=${pid}） …"
  
  # 先尝试优雅停止
  kill "${pid}" 2>/dev/null || true
  sleep 1
  
  # 检查进程是否还在运行
  if ps -p "${pid}" > /dev/null 2>&1; then
    # 如果还在运行，强制停止
    echo "    进程仍在运行，强制停止..."
    kill -9 "${pid}" 2>/dev/null || true
    sleep 0.5
  fi
  
  # 清理 PID 文件
  rm -f "${pid_file}"
  
  # 再次检查是否真的停止了
  if ps -p "${pid}" > /dev/null 2>&1; then
    echo "    ⚠️  进程可能仍在运行，请手动检查"
  else
    echo "    ✓ 已停止。"
  fi
}

stop_service "web_app" 8001
stop_service "fortune_analysis" 9005
stop_service "fortune_rule" 9007
stop_service "payment_service" 9006
stop_service "bazi_rule" 9004
stop_service "bazi_analyzer" 9003
stop_service "bazi_fortune" 9002
stop_service "bazi_core" 9001

echo "✅ 所有服务停止流程完成。"

