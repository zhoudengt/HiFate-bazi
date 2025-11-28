#!/bin/bash
# ============================================
# HiFate-bazi 服务器端部署脚本
# 放置在服务器 /opt/HiFate-bazi/scripts/deploy/
# 使用：./server_deploy.sh
# ============================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_DIR="/opt/HiFate-bazi"
BACKUP_DIR="/opt/HiFate-bazi-backups"
LOG_FILE="/var/log/hifate-deploy.log"
HEALTH_URL="http://localhost:8001/api/v1/health"
HEALTH_TIMEOUT=120

# 日志函数
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$msg"
    echo "$msg" >> "$LOG_FILE"
}

log_success() { log "${GREEN}✅ $1${NC}"; }
log_warning() { log "${YELLOW}⚠️  $1${NC}"; }
log_error() { log "${RED}❌ $1${NC}"; }
log_info() { log "${BLUE}ℹ️  $1${NC}"; }

# 检查是否在项目目录
check_directory() {
    if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
        log_error "未找到 docker-compose.yml，请确保在正确的项目目录"
        exit 1
    fi
}

# 备份当前版本
backup_current() {
    log_info "备份当前版本..."
    
    mkdir -p "$BACKUP_DIR"
    
    if [ -d "$PROJECT_DIR/.git" ]; then
        CURRENT_COMMIT=$(cd "$PROJECT_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        BACKUP_NAME="backup_${CURRENT_COMMIT}_$(date +%Y%m%d_%H%M%S)"
        
        # 只备份关键文件
        tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" \
            -C "$PROJECT_DIR" \
            .env \
            docker-compose.yml \
            docker-compose.prod.yml \
            --ignore-failed-read 2>/dev/null || true
        
        log_success "备份完成: $BACKUP_NAME"
    fi
}

# 拉取最新代码
pull_latest() {
    log_info "拉取最新代码..."
    
    cd "$PROJECT_DIR"
    
    # 保存本地修改
    git stash --include-untracked 2>/dev/null || true
    
    # 拉取
    if git pull origin master; then
        NEW_COMMIT=$(git rev-parse --short HEAD)
        log_success "代码已更新到: $NEW_COMMIT"
    else
        log_error "拉取代码失败！"
        git stash pop 2>/dev/null || true
        exit 1
    fi
    
    # 恢复本地修改（如 .env）
    git stash pop 2>/dev/null || true
}

# 构建并重启
build_and_restart() {
    log_info "构建并重启服务（零停机）..."
    
    cd "$PROJECT_DIR"
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 零停机更新
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    
    # 计算耗时
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    log_success "构建完成，耗时: ${DURATION} 秒"
}

# 健康检查
health_check() {
    log_info "健康检查（最多等待 ${HEALTH_TIMEOUT} 秒）..."
    
    local count=0
    while [ $count -lt $HEALTH_TIMEOUT ]; do
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            log_success "服务健康！"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        
        # 每 10 秒显示进度
        if [ $((count % 10)) -eq 0 ]; then
            log_info "等待服务就绪... ${count}/${HEALTH_TIMEOUT}"
        fi
    done
    
    log_error "健康检查失败！"
    return 1
}

# 显示状态
show_status() {
    log_info "当前容器状态："
    echo ""
    docker compose ps
    echo ""
    
    log_info "资源使用："
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || true
}

# 回滚
rollback() {
    log_warning "正在回滚到上一版本..."
    
    cd "$PROJECT_DIR"
    
    # 回退 Git
    git reset --hard HEAD~1
    
    # 重建
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
    
    log_warning "已回滚！请检查服务状态。"
}

# 主流程
main() {
    echo ""
    echo "============================================"
    echo "   HiFate-bazi 生产部署"
    echo "============================================"
    echo ""
    
    check_directory
    
    log_info "开始部署..."
    echo ""
    
    # 1. 备份
    backup_current
    
    # 2. 拉取代码
    pull_latest
    
    # 3. 构建重启
    build_and_restart
    
    # 4. 健康检查
    if health_check; then
        echo ""
        show_status
        echo ""
        log_success "🎉 部署成功！"
        log_info "访问地址: http://123.57.216.15:8001"
    else
        log_error "部署可能失败，尝试回滚..."
        rollback
        exit 1
    fi
}

# 命令行参数
case "${1:-}" in
    "pull")
        check_directory
        pull_latest
        ;;
    "build")
        check_directory
        build_and_restart
        ;;
    "status")
        check_directory
        show_status
        ;;
    "rollback")
        check_directory
        rollback
        ;;
    "health")
        health_check
        ;;
    *)
        main
        ;;
esac

