#!/bin/bash
# 系统资源占用检查脚本
# 用途：快速检查系统资源占用情况
# 使用：bash scripts/check_system_resources.sh

echo "========================================"
echo "系统资源占用分析"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 1. 磁盘空间
echo "【1】磁盘空间使用情况："
df -h | grep -E "^/dev|Filesystem"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "  ⚠️  磁盘使用率: ${DISK_USAGE}% (超过90%，严重)"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo "  ⚠️  磁盘使用率: ${DISK_USAGE}% (超过80%，警告)"
else
    echo "  ✅ 磁盘使用率: ${DISK_USAGE}%"
fi
echo ""

# 2. 目录占用 TOP 10
echo "【2】目录占用 TOP 10："
du -sh /* 2>/dev/null | sort -rh | head -10
echo ""

# 3. 项目目录占用
echo "【3】项目目录占用："
if [ -d "/opt/HiFate-bazi" ]; then
    echo "  /opt/HiFate-bazi:"
    du -sh /opt/HiFate-bazi
    echo "  子目录占用："
    du -sh /opt/HiFate-bazi/* 2>/dev/null | sort -rh | head -10
fi
if [ -d "/opt/hifate-frontend" ]; then
    echo "  /opt/hifate-frontend:"
    du -sh /opt/hifate-frontend
    echo "  子目录占用："
    du -sh /opt/hifate-frontend/* 2>/dev/null | sort -rh | head -10
fi
echo ""

# 4. 内存使用
echo "【4】内存使用情况："
free -h
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "  ⚠️  内存使用率: ${MEM_USAGE}% (超过90%，可能 OOM)"
elif [ "$MEM_USAGE" -gt 80 ]; then
    echo "  ⚠️  内存使用率: ${MEM_USAGE}% (超过80%，警告)"
else
    echo "  ✅ 内存使用率: ${MEM_USAGE}%"
fi
echo ""

# 5. CPU 使用
echo "【5】CPU 使用情况："
if command -v top &> /dev/null; then
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    echo "  CPU 使用率: ${CPU_USAGE}%"
fi
echo "  系统负载："
uptime
echo ""

# 6. Docker 资源
echo "【6】Docker 资源占用："
if command -v docker &> /dev/null; then
    docker system df 2>/dev/null || echo "  ⚠️  无法获取 Docker 资源信息"
else
    echo "  ⚠️  Docker 未安装"
fi
echo ""

# 7. 容器资源占用
echo "【7】容器资源占用："
if command -v docker &> /dev/null; then
    if docker ps -q | grep -q .; then
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null || echo "  无法获取容器信息"
    else
        echo "  无运行中的容器"
    fi
else
    echo "  Docker 未安装"
fi
echo ""

# 8. Docker 镜像占用
echo "【8】Docker 镜像占用 TOP 10："
if command -v docker &> /dev/null; then
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null | sort -k3 -h -r | head -10 || echo "  无法获取镜像信息"
else
    echo "  Docker 未安装"
fi
echo ""

# 9. 大文件查找（>100MB）
echo "【9】大文件（>100MB）："
find / -type f -size +100M 2>/dev/null | head -10 || echo "  未找到大文件或权限不足"
echo ""

# 10. 日志文件占用
echo "【10】日志文件占用："
echo "  系统日志："
du -sh /var/log/* 2>/dev/null | sort -rh | head -5 || echo "    无法访问"
echo "  应用日志："
if [ -d "/opt/HiFate-bazi/logs" ]; then
    du -sh /opt/HiFate-bazi/logs/* 2>/dev/null | sort -rh | head -5 || echo "    无日志文件"
else
    echo "    日志目录不存在"
fi
echo ""

# 11. Python 缓存占用
echo "【11】Python 缓存占用："
if [ -d "/opt/HiFate-bazi" ]; then
    CACHE_SIZE=$(find /opt/HiFate-bazi -name "__pycache__" -type d -exec du -sh {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")
    if [ "$CACHE_SIZE" != "0" ]; then
        echo "  Python 缓存: ${CACHE_SIZE}"
        echo "  缓存目录 TOP 5："
        find /opt/HiFate-bazi -name "__pycache__" -type d -exec du -sh {} \; 2>/dev/null | sort -rh | head -5
    else
        echo "  无 Python 缓存或无法计算"
    fi
fi
echo ""

# 12. 模型文件占用
echo "【12】模型文件占用："
if [ -d "/opt/HiFate-bazi/models_cache" ]; then
    du -sh /opt/HiFate-bazi/models_cache 2>/dev/null
    du -sh /opt/HiFate-bazi/models_cache/* 2>/dev/null | sort -rh | head -5
fi
if [ -d "/opt/HiFate-bazi/tuned_models" ]; then
    du -sh /opt/HiFate-bazi/tuned_models 2>/dev/null
fi
if [ -f "/opt/HiFate-bazi/yolov8n.pt" ]; then
    ls -lh /opt/HiFate-bazi/yolov8n.pt 2>/dev/null
fi
echo ""

echo "========================================"
echo "分析完成"
echo "========================================"
echo ""
echo "清理建议："
echo "  1. 清理 Docker 资源: docker system prune -a"
echo "  2. 清理旧日志: find /var/log -name '*.log' -mtime +30 -delete"
echo "  3. 清理 Python 缓存: find /opt/HiFate-bazi -name '__pycache__' -type d -exec rm -r {} +"
echo "  4. 清理构建缓存: docker builder prune -a"
echo ""






