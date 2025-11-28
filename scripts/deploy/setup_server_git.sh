#!/bin/bash
# ============================================
# HiFate-bazi 服务器 Git 仓库初始化脚本
# 包含：健康检查 + 自动回滚 + 部署日志
# ============================================

set -e

# === 配置（可修改）===
REPO_PATH="/opt/git/hifate-bazi.git"    # Git 裸仓库路径
DEPLOY_PATH="/opt/HiFate-bazi"           # 生产代码路径
BACKUP_PATH="/opt/HiFate-bazi.backup"    # 备份路径
LOG_FILE="/var/log/hifate-deploy.log"    # 部署日志
HEALTH_URL="http://localhost:8001/api/v1/health"  # 健康检查地址
HEALTH_TIMEOUT=60                         # 健康检查超时（秒）

echo "=========================================="
echo "   HiFate-bazi 服务器 Git 仓库初始化"
echo "   （带健康检查 + 自动回滚）"
echo "=========================================="

# 1. 创建目录
echo ""
echo "📁 创建目录..."
mkdir -p $(dirname $REPO_PATH)
mkdir -p $DEPLOY_PATH
touch $LOG_FILE

# 2. 创建 Git 裸仓库
echo "📁 创建 Git 裸仓库: $REPO_PATH"
if [ -d "$REPO_PATH" ]; then
    echo "   仓库已存在，跳过"
else
    mkdir -p $REPO_PATH
    cd $REPO_PATH
    git init --bare
fi

# 3. 创建 post-receive hook（自动部署 + 健康检查 + 回滚）
echo ""
echo "🔧 创建自动部署 hook（带健康检查和回滚）"

cat > $REPO_PATH/hooks/post-receive << 'HOOK'
#!/bin/bash
# ============================================
# HiFate-bazi 零停机自动部署
# 功能：健康检查 + 自动回滚 + 部署日志
# ============================================

set -e

# 配置
DEPLOY_PATH="/opt/HiFate-bazi"
BACKUP_PATH="/opt/HiFate-bazi.backup"
GIT_REPO="/opt/git/hifate-bazi.git"
LOG_FILE="/var/log/hifate-deploy.log"
HEALTH_URL="http://localhost:8001/api/v1/health"
HEALTH_TIMEOUT=60

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=========================================="
log "收到推送，开始部署..."

while read oldrev newrev ref; do
    if [[ $ref == refs/heads/master ]]; then
        
        # 1. 备份当前版本
        log "📦 备份当前版本..."
        if [ -d "$DEPLOY_PATH/.git" ]; then
            CURRENT_COMMIT=$(cd $DEPLOY_PATH && git rev-parse HEAD 2>/dev/null || echo "none")
            log "当前版本: $CURRENT_COMMIT"
            rm -rf $BACKUP_PATH
            cp -r $DEPLOY_PATH $BACKUP_PATH
        fi
        
        # 2. 更新代码
        log "📂 更新代码..."
        cd $DEPLOY_PATH
        
        if [ ! -d ".git" ]; then
            git clone $GIT_REPO .
        else
            git fetch origin
            git reset --hard origin/master
        fi
        
        NEW_COMMIT=$(git rev-parse HEAD)
        log "新版本: $NEW_COMMIT"
        
        # 3. 零停机重启
        log "🐳 零停机重启服务..."
        docker-compose up -d --build --force-recreate 2>&1 | tee -a $LOG_FILE
        
        # 4. 健康检查
        log "🏥 健康检查（最多等待 ${HEALTH_TIMEOUT} 秒）..."
        HEALTHY=false
        for i in $(seq 1 $HEALTH_TIMEOUT); do
            if curl -sf $HEALTH_URL > /dev/null 2>&1; then
                HEALTHY=true
                log "✅ 服务健康！耗时 ${i} 秒"
                break
            fi
            sleep 1
            # 每10秒输出一次等待信息
            if [ $((i % 10)) -eq 0 ]; then
                log "   等待中... ${i}/${HEALTH_TIMEOUT} 秒"
            fi
        done
        
        # 5. 检查结果
        if [ "$HEALTHY" = true ]; then
            log "🎉 部署成功！"
            log "   版本: $NEW_COMMIT"
            log "=========================================="
            
            # 清理旧备份（保留最近一个）
            rm -rf ${BACKUP_PATH}.old 2>/dev/null || true
            
        else
            # 自动回滚
            log "❌ 健康检查失败！"
            log "⚠️ 开始自动回滚..."
            
            if [ -d "$BACKUP_PATH" ]; then
                rm -rf $DEPLOY_PATH
                mv $BACKUP_PATH $DEPLOY_PATH
                cd $DEPLOY_PATH
                docker-compose up -d --build --force-recreate 2>&1 | tee -a $LOG_FILE
                
                ROLLBACK_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
                log "✅ 已回滚到版本: $ROLLBACK_COMMIT"
            else
                log "❌ 无备份可回滚！请手动处理"
            fi
            
            log "=========================================="
            exit 1
        fi
    fi
done
HOOK

chmod +x $REPO_PATH/hooks/post-receive

# 4. 初始化生产目录（如果是空的）
echo ""
echo "🔄 检查生产目录..."
if [ ! -d "$DEPLOY_PATH/.git" ]; then
    echo "   首次初始化，等待首次推送..."
else
    echo "   生产目录已初始化"
fi

echo ""
echo "=========================================="
echo "✅ 服务器初始化完成！"
echo "=========================================="
echo ""
echo "📋 配置信息："
echo "   Git 仓库:    $REPO_PATH"
echo "   生产目录:    $DEPLOY_PATH"
echo "   备份目录:    $BACKUP_PATH"
echo "   部署日志:    $LOG_FILE"
echo "   健康检查:    $HEALTH_URL"
echo ""
echo "📌 本地执行以下命令添加远程仓库："
echo ""
echo "   git remote add server ssh://root@YOUR_SERVER_IP$REPO_PATH"
echo ""
echo "📌 日常部署只需："
echo ""
echo "   git push server master"
echo ""
echo "📌 查看部署日志："
echo ""
echo "   tail -f $LOG_FILE"
echo ""
echo "=========================================="
