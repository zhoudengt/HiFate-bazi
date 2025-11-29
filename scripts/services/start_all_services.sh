#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_BIN="${PROJECT_ROOT}/.venv/bin"
LOG_DIR="${PROJECT_ROOT}/logs"

mkdir -p "${LOG_DIR}"

if [[ -f "${PROJECT_ROOT}/config/services.env" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/config/services.env"
fi

# 使用 gRPC 协议（格式: host:port，不带 http://）
export BAZI_CORE_SERVICE_URL="${BAZI_CORE_SERVICE_URL:-127.0.0.1:9001}"
export BAZI_FORTUNE_SERVICE_URL="${BAZI_FORTUNE_SERVICE_URL:-127.0.0.1:9002}"
export BAZI_ANALYZER_SERVICE_URL="${BAZI_ANALYZER_SERVICE_URL:-127.0.0.1:9003}"
export BAZI_RULE_SERVICE_URL="${BAZI_RULE_SERVICE_URL:-127.0.0.1:9004}"
export FORTUNE_RULE_SERVICE_URL="${FORTUNE_RULE_SERVICE_URL:-127.0.0.1:9007}"

# 检查端口是否被占用（只检查LISTEN状态）
check_port() {
  local port="$1"
  if command -v lsof > /dev/null 2>&1; then
    # 只检查LISTEN状态的端口
    if lsof -iTCP:"${port}" -sTCP:LISTEN > /dev/null 2>&1; then
      return 0  # 端口被占用
    else
      return 1  # 端口空闲
    fi
  else
    # 如果没有 lsof，使用 netstat 或 ss
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
      # 如果都没有，返回端口空闲（假设可以启动）
      return 1
    fi
  fi
}

start_uvicorn_service() {
  local name="$1"
  local module="$2"
  local port="$3"
  local log_file="${LOG_DIR}/${name}_${port}.log"
  local pid_file="${LOG_DIR}/${name}_${port}.pid"

  # 检查是否已在运行
  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}")"
    if ps -p "${existing_pid}" > /dev/null 2>&1; then
      echo "⚠️  ${name} 已在运行，跳过启动（PID: ${existing_pid}）"
      return
    else
      # PID文件存在但进程不存在，清理残留文件
      echo "ℹ️  清理残留的 PID 文件: ${pid_file}"
      rm -f "${pid_file}"
    fi
  fi

  # 检查端口是否被占用
  if check_port "${port}"; then
    echo "⚠️  端口 ${port} 已被占用，跳过启动 ${name}"
    return
  fi

  echo ">>> 启动 ${name}（端口 ${port}） …"
  "${VENV_BIN}/uvicorn" "${module}:app" \
    --host 0.0.0.0 \
    --port "${port}" \
    --access-log \
    > "${log_file}" 2>&1 &

  local pid=$!
  echo "${pid}" > "${pid_file}"
  
  # 等待一小段时间，检查进程是否还在运行
  sleep 1
  
  if ! ps -p "${pid}" > /dev/null 2>&1; then
    # 进程已退出，启动失败
    rm -f "${pid_file}"
    echo "✗ ${name} 启动失败，进程已退出。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
    return 1
  fi
  
  # 再次等待，检查端口是否真的在监听
  sleep 1
  if ! check_port "${port}"; then
    # 端口没有监听，可能启动失败
    echo "⚠️  ${name} 可能启动失败，端口 ${port} 未在监听。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
  fi
  
  echo "    ✓ 已启动 PID=${pid}，日志: ${log_file}"
}

start_python_service() {
  local name="$1"
  local script_path="$2"
  local port="$3"
  local log_file="${LOG_DIR}/${name}_${port}.log"
  local pid_file="${LOG_DIR}/${name}_${port}.pid"

  # 检查是否已在运行
  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}")"
    if ps -p "${existing_pid}" > /dev/null 2>&1; then
      echo "⚠️  ${name} 已在运行，跳过启动（PID: ${existing_pid}）"
      return
    else
      # PID文件存在但进程不存在，清理残留文件
      echo "ℹ️  清理残留的 PID 文件: ${pid_file}"
      rm -f "${pid_file}"
    fi
  fi

  # 检查端口是否被占用
  if check_port "${port}"; then
    echo "⚠️  端口 ${port} 已被占用，跳过启动 ${name}"
    return
  fi

  echo ">>> 启动 ${name}（端口 ${port}） …"
  "${VENV_BIN}/python" "${script_path}" > "${log_file}" 2>&1 &

  local pid=$!
  echo "${pid}" > "${pid_file}"
  
  # 等待一小段时间，检查进程是否还在运行
  sleep 1
  
  if ! ps -p "${pid}" > /dev/null 2>&1; then
    # 进程已退出，启动失败
    rm -f "${pid_file}"
    echo "✗ ${name} 启动失败，进程已退出。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
    return 1
  fi
  
  # 再次等待，检查端口是否真的在监听
  sleep 1
  if ! check_port "${port}"; then
    # 端口没有监听，可能启动失败
    echo "⚠️  ${name} 可能启动失败，端口 ${port} 未在监听。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
  fi
  
  echo "    ✓ 已启动 PID=${pid}，日志: ${log_file}"
}

start_grpc_service() {
  local name="$1"
  local script_path="$2"
  local port="$3"
  local log_file="${LOG_DIR}/${name}_${port}.log"
  local pid_file="${LOG_DIR}/${name}_${port}.pid"

  # 检查是否已在运行
  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}")"
    if ps -p "${existing_pid}" > /dev/null 2>&1; then
      echo "⚠️  ${name} 已在运行，跳过启动（PID: ${existing_pid}）"
      return
    else
      # PID文件存在但进程不存在，清理残留文件
      echo "ℹ️  清理残留的 PID 文件: ${pid_file}"
      rm -f "${pid_file}"
    fi
  fi

  # 检查端口是否被占用
  if check_port "${port}"; then
    echo "⚠️  端口 ${port} 已被占用，跳过启动 ${name}"
    return
  fi

  echo ">>> 启动 ${name}（gRPC，端口 ${port}） …"
  "${VENV_BIN}/python" "${script_path}" --port "${port}" > "${log_file}" 2>&1 &

  local pid=$!
  echo "${pid}" > "${pid_file}"
  
  # 等待一小段时间，检查进程是否还在运行
  sleep 1
  
  if ! ps -p "${pid}" > /dev/null 2>&1; then
    # 进程已退出，启动失败
    rm -f "${pid_file}"
    echo "✗ ${name} 启动失败，进程已退出。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
    return 1
  fi
  
  # 再次等待，检查端口是否真的在监听
  sleep 1
  if ! check_port "${port}"; then
    # 端口没有监听，可能启动失败
    echo "⚠️  ${name} 可能启动失败，端口 ${port} 未在监听。请查看日志: ${log_file}"
    echo "   最近10行日志:"
    tail -n 10 "${log_file}" 2>/dev/null || echo "   日志文件为空或不存在"
  fi
  
  echo "    ✓ 已启动 PID=${pid}，日志: ${log_file}"
}

cd "${PROJECT_ROOT}"

# 使用 gRPC 协议启动微服务
echo ">>> 使用 gRPC 协议启动微服务"
start_grpc_service "bazi_core"     "services/bazi_core/grpc_server.py"     9001
start_grpc_service "bazi_fortune"  "services/bazi_fortune/grpc_server.py"  9002
start_grpc_service "bazi_analyzer" "services/bazi_analyzer/grpc_server.py" 9003
start_grpc_service "bazi_rule"     "services/bazi_rule/grpc_server.py"     9004
start_grpc_service "fortune_analysis" "services/fortune_analysis/grpc_server.py" 9005
start_grpc_service "payment_service" "services/payment_service/grpc_server.py" 9006
start_grpc_service "fortune_rule" "services/fortune_rule/grpc_server.py" 9007
start_python_service "intent_service" "services/intent_service/grpc_server.py" 9008
start_python_service "prompt_optimizer" "services/prompt_optimizer/grpc_server.py" 9009

start_python_service "web_app" "server/start.py" 8001

echo "✅ 所有服务启动流程完成。"

