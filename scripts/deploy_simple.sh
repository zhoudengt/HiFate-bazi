#!/bin/bash
# ============================================
# 简化部署脚本 - 一键部署所有服务
# ============================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志文件
LOG_FILE="logs/deploy_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    
    # 必需的环境变量
    required_vars=(
        "MYSQL_PASSWORD"
        "COZE_ACCESS_TOKEN"
        "COZE_BOT_ID"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "缺少必需的环境变量: ${missing_vars[*]}"
        log_info "请创建 .env 文件或设置环境变量"
        exit 1
    fi
    
    log_info "环境变量检查通过"
}

# 备份数据库
backup_database() {
    log_info "备份数据库..."
    
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker ps | grep -q mysql; then
        docker exec mysql mysqldump -uroot -p"${MYSQL_PASSWORD}" hifate_bazi > "$BACKUP_FILE" 2>/dev/null || {
            log_warn "数据库备份失败（可能数据库未运行）"
            return
        }
        log_info "数据库备份完成: $BACKUP_FILE"
    else
        log_warn "MySQL 容器未运行，跳过数据库备份"
    fi
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."
    
    services=(
        "web:8001"
        "bazi-core:9001"
        "bazi-fortune:9002"
        "bazi-analyzer:9003"
        "bazi-rule:9004"
    )
    
    all_running=true
    for service in "${services[@]}"; do
        name=${service%%:*}
        port=${service##:*}
        
        if lsof -i :$port >/dev/null 2>&1; then
            log_info "✓ $name (端口 $port) 运行中"
        else
            log_warn "✗ $name (端口 $port) 未运行"
            all_running=false
        fi
    done
    
    if [ "$all_running" = true ]; then
        log_info "所有服务运行正常"
        return 0
    else
        log_warn "部分服务未运行"
        return 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止现有服务..."
    
    if [ -f "stop.sh" ]; then
        ./stop.sh
    elif [ -f "stop_all_services.sh" ]; then
        ./stop_all_services.sh
    else
        log_warn "未找到停止脚本，手动停止服务..."
        pkill -f "python.*server/start.py" || true
        pkill -f "python.*services/.*/grpc_server.py" || true
    fi
    
    sleep 2
    log_info "服务已停止"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    if [ -f "start.sh" ]; then
        ./start.sh
    elif [ -f "start_all_services.sh" ]; then
        ./start_all_services.sh
    else
        log_error "未找到启动脚本"
        exit 1
    fi
    
    log_info "等待服务启动..."
    sleep 5
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查服务状态
    if ! check_services; then
        log_error "服务验证失败"
        return 1
    fi
    
    # 检查健康接口
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        log_info "✓ Web 服务健康检查通过"
    else
        log_warn "✗ Web 服务健康检查失败"
        return 1
    fi
    
    log_info "部署验证通过"
    return 0
}

# 主函数
main() {
    log_info "============================================"
    log_info "开始部署 HiFate-bazi 系统"
    log_info "============================================"
    log_info "部署时间: $(date)"
    log_info "项目目录: $PROJECT_ROOT"
    log_info "日志文件: $LOG_FILE"
    
    # 检查必需命令
    log_info "检查必需命令..."
    check_command "python3"
    check_command "docker"
    check_command "lsof"
    
    # 检查环境变量
    check_env
    
    # 备份数据库
    backup_database
    
    # 停止现有服务
    stop_services
    
    # 启动服务
    start_services
    
    # 验证部署
    if verify_deployment; then
        log_info "============================================"
        log_info "部署成功！"
        log_info "============================================"
        log_info "Web 服务: http://localhost:8001"
        log_info "API 文档: http://localhost:8001/docs"
        log_info "日志目录: logs/"
        log_info "部署日志: $LOG_FILE"
        exit 0
    else
        log_error "============================================"
        log_error "部署验证失败，请检查日志"
        log_error "============================================"
        log_error "部署日志: $LOG_FILE"
        exit 1
    fi
}

# 执行主函数
main "$@"

