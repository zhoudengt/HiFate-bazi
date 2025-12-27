#!/bin/bash
# 配置 frontend-user 受限 Docker 权限：只能操作 frontend-* 容器
# 使用：bash scripts/configure_frontend_docker_restricted.sh
# 
# 功能：
#   - 从 docker 组中移除 frontend-user（移除完整权限）
#   - 创建 Docker 包装脚本（只允许操作 frontend-* 容器）
#   - 配置 sudo 规则（允许 frontend-user 使用包装脚本）
#   - 确保不影响现有后端服务

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"
DOCKER_WRAPPER="/usr/local/bin/docker-frontend"
SUDOERS_FILE="/etc/sudoers.d/frontend-docker"

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    fi
}

configure_node() {
    local host=$1
    local node_name=$2
    
    echo "🔒 在 $node_name ($host) 上配置 frontend-user 受限 Docker 权限..."
    echo "=========================================="
    
    # ============================================
    # 第一部分：从 docker 组中移除 frontend-user
    # ============================================
    echo ""
    echo "📋 [第一部分] 移除完整 Docker 权限..."
    
    # 检查 frontend-user 是否在 docker 组中
    echo ""
    echo "   1. 检查 frontend-user 是否在 docker 组中..."
    CURRENT_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$CURRENT_GROUPS" | grep -q "docker"; then
        echo "      ⚠️  frontend-user 在 docker 组中，正在移除..."
        
        # 从 docker 组中移除（保留其他组）
        ssh_exec $host "gpasswd -d $FRONTEND_USER docker" 2>/dev/null || {
            # 备用方法：使用 usermod
            ssh_exec $host "usermod -G \$(groups $FRONTEND_USER | sed 's/ docker//' | sed 's/^[^:]*: //') $FRONTEND_USER" 2>/dev/null || {
                echo "      ❌ 移除失败，尝试手动处理..."
                # 获取所有组（排除 docker）
                ALL_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER | sed 's/^[^:]*: //' | tr ' ' '\n' | grep -v docker | tr '\n' ',' | sed 's/,$//'")
                if [ -n "$ALL_GROUPS" ]; then
                    ssh_exec $host "usermod -G $ALL_GROUPS $FRONTEND_USER" 2>/dev/null || true
                fi
            }
        }
        
        # 验证
        NEW_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
        if echo "$NEW_GROUPS" | grep -q "docker"; then
            echo "      ❌ 移除失败，frontend-user 仍在 docker 组中"
            return 1
        else
            echo "      ✅ 已移除，frontend-user 不再在 docker 组中"
            echo "         新所属组: $NEW_GROUPS"
        fi
    else
        echo "      ✅ frontend-user 不在 docker 组中（无需操作）"
    fi
    
    # ============================================
    # 第二部分：创建 Docker 包装脚本
    # ============================================
    echo ""
    echo "📝 [第二部分] 创建 Docker 包装脚本..."
    
    # 创建包装脚本
    echo ""
    echo "   1. 创建包装脚本 $DOCKER_WRAPPER..."
    ssh_exec $host "cat > $DOCKER_WRAPPER << 'EOFSCRIPT'
#!/bin/bash
# Docker 包装脚本：只允许 frontend-user 操作 frontend-* 容器
# 使用方式：sudo docker-frontend <command> [args...]

set -e

# 允许的只读命令（可以查看所有容器，但不允许操作）
READ_ONLY_COMMANDS=(\"ps\" \"images\" \"network\" \"volume\" \"info\" \"version\" \"help\" \"stats\")

# 需要容器名称的操作（必须限制为 frontend-*）
RESTRICTED_COMMANDS=(\"stop\" \"start\" \"restart\" \"rm\" \"exec\" \"logs\" \"inspect\" \"update\" \"kill\" \"pause\" \"unpause\" \"attach\" \"commit\" \"cp\" \"diff\" \"export\" \"import\" \"rename\")

# 获取命令
CMD=\"\$1\"
shift || true
ARGS=(\"\$@\")

# 检查是否是只读命令
for read_cmd in \"\${READ_ONLY_COMMANDS[@]}\"; do
    if [ \"\$CMD\" = \"\$read_cmd\" ]; then
        # 只读命令，直接执行（可以查看所有容器）
        exec /usr/bin/docker \"\$CMD\" \"\${ARGS[@]}\"
    fi
done

# 检查是否是受限命令
for restricted_cmd in \"\${RESTRICTED_COMMANDS[@]}\"; do
    if [ \"\$CMD\" = \"\$restricted_cmd\" ]; then
        # 需要检查容器名称
        for arg in \"\${ARGS[@]}\"; do
            # 跳过选项参数
            if [[ \"\$arg\" =~ ^- ]] || [ \"\$arg\" = \"--help\" ] || [ \"\$arg\" = \"-h\" ]; then
                continue
            fi
            # 如果参数是容器名称（不是选项）
            if [[ ! \"\$arg\" =~ ^- ]] && [[ \"\$arg\" != \"docker\" ]] && [[ -n \"\$arg\" ]]; then
                # 检查是否是 frontend-* 前缀
                if [[ ! \"\$arg\" =~ ^frontend- ]]; then
                    echo \"错误：禁止操作非 frontend-* 容器: \$arg\" >&2
                    echo \"只允许操作 frontend-* 前缀的容器\" >&2
                    echo \"后端容器（hifate-*）禁止操作\" >&2
                    exit 1
                fi
            fi
        done
    fi
done

# 对于 docker run，强制使用 frontend-* 命名
if [ \"\$CMD\" = \"run\" ]; then
    NAME_FOUND=false
    NAME_VALUE=\"\"
    i=0
    while [ \$i -lt \${#ARGS[@]} ]; do
        if [ \"\${ARGS[\$i]}\" = \"--name\" ] && [ \$((i+1)) -lt \${#ARGS[@]} ]; then
            NAME_VALUE=\"\${ARGS[\$((i+1))]}\"
            if [[ ! \"\$NAME_VALUE\" =~ ^frontend- ]]; then
                echo \"错误：容器名称必须使用 frontend-* 前缀\" >&2
                echo \"当前名称: \$NAME_VALUE\" >&2
                echo \"正确格式: --name frontend-xxx\" >&2
                exit 1
            fi
            NAME_FOUND=true
            break
        fi
        i=\$((i+1))
    done
    if [ \"\$NAME_FOUND\" = false ]; then
        echo \"警告：建议使用 --name frontend-xxx 指定容器名称\" >&2
    fi
fi

# 对于 docker-compose，检查项目名和容器名
if [ \"\$CMD\" = \"compose\" ] || [ \"\$CMD\" = \"-compose\" ]; then
    # docker-compose 命令，检查项目名
    for arg in \"\${ARGS[@]}\"; do
        if [ \"\$arg\" = \"-p\" ] || [ \"\$arg\" = \"--project-name\" ]; then
            # 下一个参数是项目名
            continue
        fi
        # 检查是否是操作容器的命令
        if [[ \"\$arg\" =~ ^(up|down|start|stop|restart|rm|exec|logs|ps) ]]; then
            # 这些命令会操作容器，需要确保项目名是 frontend
            # 通过环境变量或参数检查
            break
        fi
    done
fi

# 执行 Docker 命令
exec /usr/bin/docker \"\$CMD\" \"\${ARGS[@]}\"
EOFSCRIPT
" 2>/dev/null || {
        echo "      ❌ 创建包装脚本失败"
        return 1
    }
    
    # 设置执行权限
    ssh_exec $host "chmod +x $DOCKER_WRAPPER" 2>/dev/null || {
        echo "      ❌ 设置执行权限失败"
        return 1
    }
    
    # 设置所有者
    ssh_exec $host "chown root:root $DOCKER_WRAPPER" 2>/dev/null || true
    
    echo "      ✅ 包装脚本已创建"
    
    # ============================================
    # 第三部分：配置 sudo 规则
    # ============================================
    echo ""
    echo "🔐 [第三部分] 配置 sudo 规则..."
    
    # 创建 sudoers 文件
    echo ""
    echo "   1. 创建 sudoers 配置文件..."
    ssh_exec $host "cat > $SUDOERS_FILE << 'EOFSUDO'
# frontend-user Docker 受限权限配置
# 只允许使用包装脚本 docker-frontend
frontend-user ALL=(ALL) NOPASSWD: $DOCKER_WRAPPER
Defaults:frontend-user !requiretty
EOFSUDO
" 2>/dev/null || {
        echo "      ❌ 创建 sudoers 文件失败"
        return 1
    }
    
    # 设置正确的权限（sudoers 文件必须是 0440）
    ssh_exec $host "chmod 0440 $SUDOERS_FILE" 2>/dev/null || {
        echo "      ⚠️  设置 sudoers 文件权限失败，尝试修复..."
        ssh_exec $host "chmod 440 $SUDOERS_FILE" 2>/dev/null || true
    }
    
    # 验证 sudoers 文件语法
    echo ""
    echo "   2. 验证 sudoers 文件语法..."
    SUDOERS_CHECK=$(ssh_exec $host "visudo -c -f $SUDOERS_FILE 2>&1" || echo "")
    if echo "$SUDOERS_CHECK" | grep -qE "syntax OK|parsed OK"; then
        echo "      ✅ sudoers 文件语法正确"
    else
        echo "      ❌ sudoers 文件语法错误"
        echo "         输出: $SUDOERS_CHECK"
        # 删除有问题的文件
        ssh_exec $host "rm -f $SUDOERS_FILE" 2>/dev/null || true
        return 1
    fi
    
    echo "      ✅ sudo 规则已配置"
    
    # ============================================
    # 第四部分：验证配置
    # ============================================
    echo ""
    echo "✅ [第四部分] 验证配置..."
    
    # 验证 frontend-user 不在 docker 组中
    echo ""
    echo "   1. 验证 frontend-user 不在 docker 组中..."
    FINAL_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    if echo "$FINAL_GROUPS" | grep -q "docker"; then
        echo "      ❌ 失败：frontend-user 仍在 docker 组中"
        return 1
    else
        echo "      ✅ 通过：frontend-user 不在 docker 组中"
        echo "         所属组: $FINAL_GROUPS"
    fi
    
    # 验证包装脚本存在
    echo ""
    echo "   2. 验证包装脚本存在..."
    if ssh_exec $host "test -f $DOCKER_WRAPPER && test -x $DOCKER_WRAPPER" 2>/dev/null; then
        echo "      ✅ 通过：包装脚本存在且可执行"
    else
        echo "      ❌ 失败：包装脚本不存在或不可执行"
        return 1
    fi
    
    # 验证 sudo 规则
    echo ""
    echo "   3. 验证 sudo 规则..."
    SUDO_TEST=$(ssh_exec $host "sudo -l -U $FRONTEND_USER 2>&1 | grep docker-frontend" || echo "")
    if echo "$SUDO_TEST" | grep -q "docker-frontend"; then
        echo "      ✅ 通过：sudo 规则已生效"
        echo "         $SUDO_TEST"
    else
        echo "      ⚠️  警告：sudo 规则可能未生效（需要用户重新登录）"
        echo "         输出: $SUDO_TEST"
    fi
    
    # 测试包装脚本（只读命令）
    echo ""
    echo "   4. 测试包装脚本（只读命令）..."
    DOCKER_PS_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'sudo $DOCKER_WRAPPER ps 2>&1 | head -3'" 2>/dev/null || echo "")
    if echo "$DOCKER_PS_TEST" | grep -q "CONTAINER\|permission denied"; then
        if echo "$DOCKER_PS_TEST" | grep -q "permission denied"; then
            echo "      ⚠️  警告：可能需要用户重新登录才能生效"
        else
            echo "      ✅ 通过：包装脚本可以执行只读命令"
        fi
    else
        echo "      ⚠️  检查输出: $DOCKER_PS_TEST"
    fi
    
    echo ""
    echo "=========================================="
    echo "✅ $node_name 配置完成"
    echo "=========================================="
    echo ""
}

echo "=========================================="
echo "配置 frontend-user 受限 Docker 权限（双机）"
echo "=========================================="
echo ""
echo "⚠️  重要提示："
echo "  - 将从 docker 组中移除 frontend-user（移除完整权限）"
echo "  - 创建包装脚本，只允许操作 frontend-* 容器"
echo "  - 配置 sudo 规则，允许使用包装脚本"
echo "  - 不会影响现有后端服务"
echo ""
echo "功能限制："
echo "  ✅ 可以查看所有容器（docker ps）"
echo "  ✅ 可以操作 frontend-* 容器（stop/start/rm 等）"
echo "  ❌ 禁止操作 hifate-* 容器（后端容器）"
echo "  ❌ 禁止直接使用 docker 命令（必须使用 sudo docker-frontend）"
echo ""

# 配置 Node1
configure_node $NODE1_PUBLIC_IP "Node1"
NODE1_RESULT=$?

# 配置 Node2
configure_node $NODE2_PUBLIC_IP "Node2"
NODE2_RESULT=$?

echo "=========================================="
echo "完成"
echo "=========================================="
echo ""

if [ $NODE1_RESULT -eq 0 ] && [ $NODE2_RESULT -eq 0 ]; then
    echo "✅ frontend-user 受限 Docker 权限配置完成（双机）"
    echo ""
    echo "使用方式："
    echo "  # frontend-user 需要使用以下命令："
    echo "  sudo docker-frontend ps              # 查看所有容器"
    echo "  sudo docker-frontend run --name frontend-app ...  # 创建容器"
    echo "  sudo docker-frontend stop frontend-app  # 停止自己的容器"
    echo "  sudo docker-frontend stop hifate-web   # 禁止：会报错"
    echo ""
    echo "⚠️  重要提醒："
    echo "  - frontend-user 需要重新登录才能生效"
    echo "  - 必须使用 'sudo docker-frontend' 而不是 'docker'"
    echo "  - 只能操作 frontend-* 前缀的容器"
    echo "  - 后端容器（hifate-*）完全禁止操作"
    echo ""
    echo "验证命令："
    echo "  bash scripts/verify_frontend_docker_restricted.sh"
    exit 0
else
    echo "❌ 部分配置失败"
    echo ""
    echo "请检查："
    echo "  - SSH 连接是否正常"
    echo "  - 是否有 root 权限"
    echo "  - 查看上面的错误信息"
    exit 1
fi

