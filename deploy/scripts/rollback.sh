#!/bin/bash
# ============================================
# HiFate 回滚脚本（增强版）
# ============================================
# 用途：回滚到指定版本（支持镜像回滚和 Git 回滚）
# 
# 使用方法：
#   镜像回滚: bash rollback.sh --image <image_tag> --node <node1|node2>
#   Git回滚:  bash rollback.sh --git <commit_hash> --node <node1|node2>
#   查看历史: bash rollback.sh --list
# ============================================

set -e

# 加载公共函数库
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ -f "${SCRIPT_DIR}/lib/common.sh" ]; then
    source "${SCRIPT_DIR}/lib/common.sh"
else
    # 最小化的日志函数（如果公共库不存在）
    log_info() { echo "[INFO] $*"; }
    log_error() { echo "[ERROR] $*" >&2; }
    log_success() { echo "✓ $*"; }
    error_exit() { log_error "$1"; exit 1; }
fi

# ==================== 配置 ====================

PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"
DEPLOY_DIR="${PROJECT_DIR}/deploy"
BACKUP_DIR="${PROJECT_DIR}/.rollback_backups"
HISTORY_FILE="${BACKUP_DIR}/rollback_history.log"

# 默认值
ROLLBACK_TYPE=""
TARGET_VERSION=""
NODE_TYPE=""

# ==================== 帮助信息 ====================

show_help() {
    echo "HiFate 回滚脚本"
    echo ""
    echo "用法:"
    echo "  $0 --image <tag> --node <node1|node2>  镜像回滚"
    echo "  $0 --git <commit> --node <node1|node2> Git版本回滚"
    echo "  $0 --list                              查看回滚历史"
    echo "  $0 --available                         查看可用版本"
    echo "  $0 --help                              显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 --image abc1234 --node node1"
    echo "  $0 --git 7d3e5f2 --node node1"
    echo ""
    echo "选项:"
    echo "  --image <tag>      回滚到指定镜像标签"
    echo "  --git <commit>     回滚到指定 Git 提交"
    echo "  --node <type>      节点类型 (node1 或 node2)"
    echo "  --force            跳过确认直接执行"
    echo "  --no-backup        不备份当前版本"
}

# ==================== 查看可用版本 ====================

show_available_versions() {
    echo "========================================" 
    echo "可用的镜像版本:"
    echo "========================================" 
    docker images | grep -E "hifate-bazi|hifate" | head -15 || echo "无可用镜像"
    
    echo ""
    echo "========================================" 
    echo "最近的 Git 提交:"
    echo "========================================"
    cd "${PROJECT_DIR}" 2>/dev/null && git log --oneline -10 || echo "无法获取 Git 历史"
}

# ==================== 查看回滚历史 ====================

show_rollback_history() {
    echo "========================================"
    echo "回滚历史:"
    echo "========================================"
    
    if [ -f "$HISTORY_FILE" ]; then
        tail -20 "$HISTORY_FILE"
    else
        echo "暂无回滚记录"
    fi
}

# ==================== 备份当前版本 ====================

backup_current_version() {
    local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    
    mkdir -p "$backup_path"
    
    log_info "备份当前版本到: $backup_path"
    
    # 记录 Git 版本
    cd "${PROJECT_DIR}"
    {
        echo "Backup Time: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Git Commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
        echo "Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    } > "${backup_path}/git_info.txt"
    
    # 记录 Docker 镜像信息
    docker inspect --format='{{.Config.Image}}' hifate-web 2>/dev/null > "${backup_path}/docker_image.txt" || echo "unknown" > "${backup_path}/docker_image.txt"
    
    # 备份 .env 文件
    cp "${PROJECT_DIR}/.env" "${backup_path}/.env.backup" 2>/dev/null || true
    
    log_success "备份完成: $backup_path"
    
    # 返回备份路径
    echo "$backup_path"
}

# ==================== 记录回滚历史 ====================

record_rollback() {
    local type="$1"
    local target="$2"
    local result="$3"
    
    mkdir -p "$(dirname "$HISTORY_FILE")"
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $type | $target | $NODE_TYPE | $result" >> "$HISTORY_FILE"
}

# ==================== 镜像回滚 ====================

rollback_image() {
    local image_tag="$1"
    
    log_info "开始镜像回滚: $image_tag"
    
    # 检查 .env 文件
    if [ ! -f "${PROJECT_DIR}/.env" ]; then
        error_exit ".env 文件不存在"
    fi
    
    cd "${PROJECT_DIR}"
    source .env
    
    # 构建完整镜像名
    local registry="${ACR_REGISTRY:-registry.cn-hangzhou.aliyuncs.com}"
    local namespace="${ACR_NAMESPACE:-hifate}"
    local rollback_image="${registry}/${namespace}/hifate-bazi:${image_tag}"
    
    log_info "目标镜像: $rollback_image"
    
    # 拉取镜像
    log_info "拉取镜像..."
    if ! docker pull "$rollback_image"; then
        error_exit "拉取镜像失败: $rollback_image"
    fi
    
    # 执行回滚
    log_info "执行回滚..."
    cd "${DEPLOY_DIR}/docker"
    export IMAGE_TAG="$image_tag"
    
    if ! docker-compose -f docker-compose.prod.yml -f "docker-compose.${NODE_TYPE}.yml" --env-file "${PROJECT_DIR}/.env" up -d --no-deps web; then
        error_exit "Docker Compose 执行失败"
    fi
    
    log_success "镜像回滚命令执行完成"
}

# ==================== Git 回滚 ====================

rollback_git() {
    local commit_hash="$1"
    
    log_info "开始 Git 回滚: $commit_hash"
    
    cd "${PROJECT_DIR}"
    
    # 验证提交是否存在
    if ! git cat-file -e "$commit_hash^{commit}" 2>/dev/null; then
        error_exit "Git 提交不存在: $commit_hash"
    fi
    
    # 检查是否有未提交的更改
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "检测到未提交的更改"
        if [ "$FORCE" != "true" ]; then
            error_exit "请先提交或暂存更改，或使用 --force 强制执行"
        fi
        log_info "强制模式：暂存当前更改"
        git stash
    fi
    
    # 执行回滚
    log_info "切换到目标提交..."
    git checkout "$commit_hash"
    
    # 触发热更新
    log_info "触发热更新..."
    if [ -f "${PROJECT_DIR}/scripts/ai/auto_hot_reload.py" ]; then
        python3 "${PROJECT_DIR}/scripts/ai/auto_hot_reload.py" --trigger || log_warn "热更新触发失败，请手动执行"
    fi
    
    log_success "Git 回滚完成"
}

# ==================== 健康检查 ====================

verify_rollback() {
    log_info "验证回滚结果..."
    
    local max_wait=60
    local interval=5
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
            log_success "健康检查通过"
            return 0
        fi
        
        sleep $interval
        ((elapsed += interval))
        echo -n "."
    done
    
    echo ""
    log_error "健康检查超时"
    return 1
}

# ==================== 解析参数 ====================

FORCE="false"
NO_BACKUP="false"

while [ $# -gt 0 ]; do
    case "$1" in
        --image)
            ROLLBACK_TYPE="image"
            TARGET_VERSION="$2"
            shift 2
            ;;
        --git)
            ROLLBACK_TYPE="git"
            TARGET_VERSION="$2"
            shift 2
            ;;
        --node)
            NODE_TYPE="$2"
            shift 2
            ;;
        --force)
            FORCE="true"
            shift
            ;;
        --no-backup)
            NO_BACKUP="true"
            shift
            ;;
        --list)
            show_rollback_history
            exit 0
            ;;
        --available)
            show_available_versions
            exit 0
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            # 向后兼容旧格式: rollback.sh <image_tag> <node_type>
            if [ -z "$TARGET_VERSION" ]; then
                ROLLBACK_TYPE="image"
                TARGET_VERSION="$1"
            elif [ -z "$NODE_TYPE" ]; then
                NODE_TYPE="$1"
            fi
            shift
            ;;
    esac
done

# ==================== 验证参数 ====================

if [ -z "$ROLLBACK_TYPE" ] || [ -z "$TARGET_VERSION" ]; then
    show_help
    exit 1
fi

if [ -z "$NODE_TYPE" ] || ([ "$NODE_TYPE" != "node1" ] && [ "$NODE_TYPE" != "node2" ]); then
    log_error "必须指定有效的节点类型: node1 或 node2"
    exit 1
fi

# ==================== 执行回滚 ====================

echo "========================================"
echo "HiFate 回滚"
echo "========================================"
echo "回滚类型: $ROLLBACK_TYPE"
echo "目标版本: $TARGET_VERSION"
echo "节点:     $NODE_TYPE"
echo "========================================"

# 确认操作
if [ "$FORCE" != "true" ]; then
    read -p "确认执行回滚? (y/N) " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "已取消"
        exit 0
    fi
fi

# 备份当前版本
if [ "$NO_BACKUP" != "true" ]; then
    BACKUP_PATH=$(backup_current_version)
fi

# 执行回滚
case "$ROLLBACK_TYPE" in
    image)
        rollback_image "$TARGET_VERSION"
        ;;
    git)
        rollback_git "$TARGET_VERSION"
        ;;
esac

# 验证回滚
if verify_rollback; then
    record_rollback "$ROLLBACK_TYPE" "$TARGET_VERSION" "SUCCESS"
    echo ""
    echo "========================================"
    log_success "回滚成功！"
    echo "========================================"
else
    record_rollback "$ROLLBACK_TYPE" "$TARGET_VERSION" "FAILED"
    echo ""
    echo "========================================"
    log_error "回滚后健康检查失败"
    echo "备份位置: ${BACKUP_PATH:-无备份}"
    echo "请检查日志: docker logs hifate-web"
    echo "========================================"
    exit 1
fi
