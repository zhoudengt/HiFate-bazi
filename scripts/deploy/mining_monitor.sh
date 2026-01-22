#!/bin/bash
# 挖矿程序监控和自动清理脚本
# 用途：检测挖矿程序并自动清理，不影响 hifate 和 frontend 容器
# 使用：bash scripts/deploy/mining_monitor.sh
# 定时任务：*/5 * * * * /opt/HiFate-bazi/scripts/deploy/mining_monitor.sh >> /var/log/mining-monitor.log 2>&1

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="/var/log/mining-monitor.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 受保护的容器名称（不清理）
PROTECTED_CONTAINERS=("hifate" "frontend")

# 日志函数
log_info() {
    echo "[$TIMESTAMP] [INFO] $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo "[$TIMESTAMP] [WARN] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$TIMESTAMP] [ERROR] $1" | tee -a "$LOG_FILE"
}

# 检查是否为受保护的容器
is_protected_container() {
    local container_name="$1"
    for protected in "${PROTECTED_CONTAINERS[@]}"; do
        if [[ "$container_name" == *"$protected"* ]]; then
            return 0
        fi
    done
    return 1
}

# 检测挖矿进程
detect_mining_processes() {
    local found=false
    
    # 检测 xmrig 相关进程（排除系统 kworker）
    if ps aux | grep -E 'xmrig|systemp|systemd-bench' | grep -v grep | grep -v 'kworker/' > /dev/null; then
        log_warn "发现挖矿进程"
        ps aux | grep -E 'xmrig|systemp|systemd-bench' | grep -v grep | grep -v 'kworker/' | while read line; do
            log_warn "  进程: $line"
        done
        found=true
    fi
    
    # 检测循环启动脚本
    if ps aux | grep -E '/data.*while.*xmrig|restore\.sh' | grep -v grep > /dev/null; then
        log_warn "发现循环启动脚本"
        ps aux | grep -E '/data.*while.*xmrig|restore\.sh' | grep -v grep | while read line; do
            log_warn "  脚本: $line"
        done
        found=true
    fi
    
    if [ "$found" = true ]; then
        return 0
    fi
    return 1
}

# 检测定时任务
detect_crontab_tasks() {
    if crontab -l 2>/dev/null | grep -E 'xmrig|restore|miner' > /dev/null; then
        log_warn "发现挖矿相关定时任务"
        crontab -l 2>/dev/null | grep -E 'xmrig|restore|miner' | while read line; do
            log_warn "  任务: $line"
        done
        return 0
    fi
    return 1
}

# 检测挖矿文件和目录
detect_mining_files() {
    local found=false
    
    # 检查常见挖矿文件位置
    local files_to_check=(
        "/etc/xmrig-restore"
        "/root/.system-cache"
        "/usr/local/bin/systemp"
        "/usr/local/bin/.config.json"
        "/tmp/.kw.pid"
        "/var/log/xmrig-restore.log"
        "/tmp/xmrig_install_error.log"
    )
    
    for file in "${files_to_check[@]}"; do
        if [ -e "$file" ]; then
            log_warn "发现挖矿文件/目录: $file"
            found=true
        fi
    done
    
    if [ "$found" = true ]; then
        return 0
    fi
    return 1
}

# 检测挖矿 Docker 容器和卷
detect_mining_docker() {
    local found=false
    
    # 检测挖矿容器（排除受保护的容器）
    docker ps -a --format '{{.Names}}' 2>/dev/null | while read container_name; do
        if [[ "$container_name" == *"miner"* ]] || [[ "$container_name" == *"xmrig"* ]]; then
            if ! is_protected_container "$container_name"; then
                log_warn "发现挖矿容器: $container_name"
                found=true
            fi
        fi
    done
    
    # 检测挖矿 Docker 卷
    if docker volume ls 2>/dev/null | grep -E 'miner|xmrig' > /dev/null; then
        log_warn "发现挖矿 Docker 卷"
        docker volume ls 2>/dev/null | grep -E 'miner|xmrig' | while read line; do
            log_warn "  卷: $line"
        done
        found=true
    fi
    
    if [ "$found" = true ]; then
        return 0
    fi
    return 1
}

# 清理挖矿进程
cleanup_processes() {
    log_info "开始清理挖矿进程..."
    
    # 终止 xmrig 相关进程
    pkill -9 -f xmrig 2>/dev/null && log_info "已终止 xmrig 进程" || true
    pkill -9 -f systemp 2>/dev/null && log_info "已终止 systemp 进程" || true
    pkill -9 -f systemd-bench 2>/dev/null && log_info "已终止 systemd-bench 进程" || true
    
    # 终止循环启动脚本
    pkill -9 -f '/data.*while.*xmrig' 2>/dev/null && log_info "已终止循环启动脚本" || true
    pkill -9 -f 'restore.sh' 2>/dev/null && log_info "已终止恢复脚本" || true
    
    sleep 2
    
    # 验证清理结果
    if detect_mining_processes; then
        log_error "清理进程失败，仍有挖矿进程运行"
        return 1
    else
        log_info "挖矿进程清理完成"
        return 0
    fi
}

# 清理定时任务
cleanup_crontab() {
    log_info "开始清理定时任务..."
    
    # 备份 crontab
    if crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null; then
        log_info "crontab 已备份"
    fi
    
    # 清理挖矿相关任务
    if crontab -l 2>/dev/null | grep -vE 'xmrig|restore|miner' | crontab - 2>/dev/null; then
        log_info "定时任务清理完成"
        return 0
    else
        log_warn "定时任务清理失败或无需清理"
        return 1
    fi
}

# 清理文件和目录
cleanup_files() {
    log_info "开始清理挖矿文件..."
    
    local cleaned=false
    
    # 删除恢复脚本目录
    if [ -d "/etc/xmrig-restore" ]; then
        rm -rf /etc/xmrig-restore && log_info "已删除 /etc/xmrig-restore" && cleaned=true
    fi
    
    # 删除挖矿程序目录
    if [ -d "/root/.system-cache" ]; then
        rm -rf /root/.system-cache && log_info "已删除 /root/.system-cache" && cleaned=true
    fi
    
    # 删除单个文件
    local files_to_remove=(
        "/usr/local/bin/systemp"
        "/usr/local/bin/.config.json"
        "/tmp/.kw.pid"
        "/var/log/xmrig-restore.log"
        "/tmp/xmrig_install_error.log"
    )
    
    for file in "${files_to_remove[@]}"; do
        if [ -e "$file" ]; then
            rm -f "$file" && log_info "已删除 $file" && cleaned=true
        fi
    done
    
    if [ "$cleaned" = true ]; then
        log_info "挖矿文件清理完成"
        return 0
    else
        log_info "无需清理文件"
        return 1
    fi
}

# 清理 Docker 容器和卷
cleanup_docker() {
    log_info "开始清理 Docker 容器和卷..."
    
    local cleaned=false
    
    # 停止并删除挖矿容器（排除受保护的容器）
    docker ps -a --format '{{.Names}}' 2>/dev/null | while read container_name; do
        if [[ "$container_name" == *"miner"* ]] || [[ "$container_name" == *"xmrig"* ]]; then
            if ! is_protected_container "$container_name"; then
                docker stop "$container_name" 2>/dev/null && log_info "已停止容器: $container_name"
                docker rm "$container_name" 2>/dev/null && log_info "已删除容器: $container_name" && cleaned=true
            fi
        fi
    done
    
    # 删除 Docker 卷中的 xmrig 文件
    if docker volume ls 2>/dev/null | grep -E 'miner|xmrig' > /dev/null; then
        docker volume ls 2>/dev/null | grep -E 'miner|xmrig' | awk '{print $2}' | while read volume_name; do
            # 先删除卷中的文件
            if [ -d "/var/lib/docker/volumes/$volume_name/_data" ]; then
                rm -f /var/lib/docker/volumes/$volume_name/_data/xmrig 2>/dev/null && log_info "已删除卷中的 xmrig 文件: $volume_name"
            fi
            # 尝试删除卷（如果无容器使用）
            docker volume rm "$volume_name" 2>/dev/null && log_info "已删除 Docker 卷: $volume_name" && cleaned=true || log_warn "无法删除卷 $volume_name（可能正在使用）"
        done
    fi
    
    if [ "$cleaned" = true ]; then
        log_info "Docker 清理完成"
        return 0
    else
        log_info "无需清理 Docker"
        return 1
    fi
}

# 验证项目服务
verify_services() {
    log_info "验证项目服务状态..."
    
    # 检查 hifate 和 frontend 容器
    local hifate_count=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c hifate || echo "0")
    local frontend_count=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c frontend || echo "0")
    
    if [ "$hifate_count" -gt 0 ] && [ "$frontend_count" -gt 0 ]; then
        log_info "项目容器运行正常 (hifate: $hifate_count, frontend: $frontend_count)"
        
        # 检查健康检查端点
        if curl -sf --connect-timeout 5 http://localhost:8001/health > /dev/null 2>&1; then
            log_info "项目服务健康检查通过"
            return 0
        else
            log_warn "项目服务健康检查失败（可能暂时不可用）"
            return 1
        fi
    else
        log_warn "项目容器数量异常"
        return 1
    fi
}

# 主函数
main() {
    log_info "========================================="
    log_info "挖矿程序监控和清理脚本启动"
    log_info "========================================="
    
    local threat_detected=false
    local cleanup_performed=false
    
    # 检测威胁
    if detect_mining_processes; then
        threat_detected=true
    fi
    
    if detect_crontab_tasks; then
        threat_detected=true
    fi
    
    if detect_mining_files; then
        threat_detected=true
    fi
    
    if detect_mining_docker; then
        threat_detected=true
    fi
    
    # 如果检测到威胁，执行清理
    if [ "$threat_detected" = true ]; then
        log_warn "检测到挖矿程序威胁，开始清理..."
        
        cleanup_processes && cleanup_performed=true
        cleanup_crontab && cleanup_performed=true
        cleanup_files && cleanup_performed=true
        cleanup_docker && cleanup_performed=true
        
        if [ "$cleanup_performed" = true ]; then
            log_info "清理操作已完成"
            
            # 等待后再次验证
            sleep 5
            if detect_mining_processes || detect_mining_files || detect_mining_docker; then
                log_error "清理后仍有威胁，请手动检查"
            else
                log_info "清理验证通过，威胁已清除"
            fi
        fi
        
        # 验证项目服务
        verify_services
    else
        log_info "未检测到挖矿程序威胁，系统正常"
    fi
    
    log_info "========================================="
    log_info "监控脚本执行完成"
    log_info "========================================="
    echo ""
}

# 执行主函数
main "$@"
