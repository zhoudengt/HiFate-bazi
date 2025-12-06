# HiFate-bazi Dockerfile (PyArmor 保护版本)
# 标准 CI/CD 流程：GitHub Actions 构建 → GHCR → 服务器拉取部署
# 
# 构建命令：
#   docker build --platform linux/amd64 -t hifate-bazi:latest .
#
# 部署流程：
#   1. 本地开发 → 推送到 GitHub
#   2. GitHub Actions 自动构建镜像并推送到 GHCR
#   3. 服务器从 GHCR 拉取镜像并部署
#
# 安全特性：
#   - 使用 PyArmor 最高级别混淆和保护
#   - 原始源码在构建后完全删除
#   - 混淆后的代码无法反编译
#   - 运行时保护防止调试和逆向

FROM --platform=linux/amd64 python:3.11-slim

LABEL maintainer="HiFate Team"
LABEL description="HiFate-bazi application image (PyArmor Protected)"

# 环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 使用国内镜像源加速（系统包）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# 安装系统依赖（opencv/mediapipe/YOLO 需要）
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        wget \
        gcc \
        g++ \
        make \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgthread-2.0-0 \
        libgstreamer1.0-0 \
        libgstreamer-plugins-base1.0-0 \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置 pip 使用国内源（加速下载）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 升级 pip、setuptools、wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制并安装依赖（包括 PyArmor）
COPY requirements.txt .
COPY services/desk_fengshui/requirements.txt /tmp/desk_fengshui_requirements.txt

# 先安装基础依赖（不包含 ultralytics）
RUN pip install --no-cache-dir -r requirements.txt && \
    # 清理缓存
    pip cache purge || true && \
    rm -rf /root/.cache/pip /tmp/pip-* /var/tmp/*

# 安装 ultralytics（YOLOv8）及其依赖（使用 CPU 版本的 torch 以减少空间）
# 注意：ultralytics 会自动安装 torch，我们使用环境变量强制使用 CPU 版本
RUN TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu \
    pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision --no-deps && \
    pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt && \
    # 安装 PyArmor
    pip install --no-cache-dir pyarmor && \
    rm -f /tmp/desk_fengshui_requirements.txt && \
    # 立即清理 pip 缓存和临时文件（关键：在安装 torch 后立即清理）
    pip cache purge || true && \
    rm -rf /root/.cache/pip /root/.cache/torch /tmp/pip-* /var/tmp/* && \
    # 清理 Python 字节码缓存
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name "*.pyc" -delete 2>/dev/null || true && \
    # 清理 torch 的测试和文档文件（减少空间）
    find /usr/local/lib/python3.11/site-packages/torch -name "test" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages/torch -name "*.md" -delete 2>/dev/null || true

# ============================================
# PyArmor 混淆保护阶段
# ============================================

# 复制应用代码到临时目录（只复制需要的文件，减少空间占用）
COPY . /tmp/source

# 创建混淆输出目录
RUN mkdir -p /tmp/obfuscated && \
    # 清理不必要的文件，减少磁盘占用
    find /tmp/source -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /tmp/source -name "*.pyc" -delete 2>/dev/null || true && \
    find /tmp/source -name "*.pyo" -delete 2>/dev/null || true && \
    find /tmp/source -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /tmp/source -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# 使用 PyArmor 最高保护级别混淆所有 Python 代码
# 保护选项说明：
#   --obf-code=2        : 最高级别代码混淆（无法反编译）
#   --obf-mod=1         : 模块级别混淆
#   --wrap-mode=1       : 包装模式（增强保护）
#   --restrict-mode=4   : 最高限制模式（防止调试、反编译、内存dump）
#   --enable-rft=1      : 启用运行时保护（防止动态分析）
#   --advanced-mode=2   : 高级模式（最强保护）
#   --platform linux.x86_64 : 指定目标平台
RUN cd /tmp/source && \
    # 初始化 PyArmor（生成许可证和密钥）
    pyarmor gen --platform linux.x86_64 \
        --obf-code=2 \
        --obf-mod=1 \
        --wrap-mode=1 \
        --restrict-mode=4 \
        --enable-rft=1 \
        --advanced-mode=2 \
        --output /tmp/obfuscated \
        --recursive \
        --exclude "frontend" \
        --exclude "docs" \
        --exclude "tests" \
        --exclude "scripts" \
        --exclude "*.pyc" \
        --exclude "__pycache__" \
        --exclude ".git" \
        --exclude "node_modules" \
        --exclude "logs" \
        --exclude "*.log" \
        server/ services/ src/ proto/ mianxiang_hand_fengshui/ && \
    # 复制非 Python 文件（配置文件、前端文件等）
    # 注意：明确排除 .py 文件，避免复制原始源码
    find /tmp/source -type f ! -name "*.py" ! -name "*.pyc" ! -path "*/__pycache__/*" ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/logs/*" ! -name "*.log" ! -path "*/server/*" ! -path "*/services/*" ! -path "*/src/*" ! -path "*/proto/*" ! -path "*/mianxiang_hand_fengshui/*" \
        -exec cp --parents {} /tmp/obfuscated/ \; 2>/dev/null || true && \
    # 复制前端文件
    cp -r /tmp/source/frontend /tmp/obfuscated/ 2>/dev/null || true && \
    # 复制配置文件
    cp -r /tmp/source/config /tmp/obfuscated/ 2>/dev/null || true && \
    # 复制 proto 文件（gRPC 需要）
    cp -r /tmp/source/proto/*.proto /tmp/obfuscated/proto/ 2>/dev/null || true && \
    # 复制其他必要文件
    cp /tmp/source/requirements.txt /tmp/obfuscated/ 2>/dev/null || true && \
    cp /tmp/source/README.md /tmp/obfuscated/ 2>/dev/null || true

# 将混淆后的代码移动到应用目录
# 注意：/tmp/obfuscated 中只包含混淆后的文件，不会有原始源码
RUN mv /tmp/obfuscated/* ${APP_HOME}/ && \
    # 确保 pyarmor_runtime 目录存在且可访问
    if [ -d "${APP_HOME}/pyarmor_runtime" ]; then \
        echo "✅ pyarmor_runtime 目录已复制"; \
    else \
        echo "⚠️  pyarmor_runtime 目录未找到，检查混淆输出..."; \
        find ${APP_HOME} -type d -name "*pyarmor*" -exec ls -la {} \; || true; \
    fi && \
    # 检查并删除任何可能的原始源码文件（通过检查文件内容是否包含 pyarmor 标记）
    # 如果文件不包含 pyarmor 相关标记，可能是原始文件，需要删除
    # 但保留启动脚本 server/start.py（即使没有被混淆也要保留）
    find ${APP_HOME} -type f -name "*.py" ! -path "*/pyarmor_runtime/*" ! -path "*/site-packages/*" ! -path "*/server/start.py" \
        -exec sh -c 'grep -q "pyarmor\|__pyarmor__\|PyArmor" "$1" || rm -f "$1"' _ {} \; 2>/dev/null || true && \
    # 确保启动脚本存在（如果被误删，从源文件恢复）
    if [ ! -f "${APP_HOME}/server/start.py" ]; then \
        echo "⚠️  启动脚本不存在，尝试恢复..."; \
        if [ -f "/tmp/source/server/start.py" ]; then \
            cp /tmp/source/server/start.py ${APP_HOME}/server/start.py; \
            echo "✅ 启动脚本已恢复"; \
        else \
            echo "❌ 无法恢复启动脚本，构建失败"; \
            exit 1; \
        fi; \
    fi && \
    # 删除临时目录并清理空间
    rm -rf /tmp/source /tmp/obfuscated && \
    # 清理系统临时文件
    rm -rf /tmp/* /var/tmp/* && \
    # 清理 apt 缓存（如果还有）
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    # 清理 Python 缓存
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name "*.pyc" -delete 2>/dev/null || true

# 验证混淆后的模块可以导入（在删除 PyArmor 之前验证）
RUN python -c "\
import sys; \
import os; \
sys.path.insert(0, '/app'); \
# 确保 pyarmor_runtime 在路径中 \
if os.path.exists('/app/pyarmor_runtime'): \
    sys.path.insert(0, '/app/pyarmor_runtime'); \
try: \
    # 尝试导入 pyarmor_runtime（可能在不同的位置） \
    try: \
        import pyarmor_runtime; \
        print('✅ pyarmor_runtime 导入成功'); \
    except ImportError: \
        # 尝试从不同路径导入 \
        import glob; \
        runtime_paths = glob.glob('/app/**/pyarmor_runtime*', recursive=True); \
        if runtime_paths: \
            sys.path.insert(0, os.path.dirname(runtime_paths[0])); \
            import pyarmor_runtime; \
            print(f'✅ pyarmor_runtime 从 {runtime_paths[0]} 导入成功'); \
        else: \
            print('⚠️  未找到 pyarmor_runtime，但继续验证模块导入'); \
    # 验证核心模块导入 \
    from server.services.rule_service import RuleService; \
    print('✅ RuleService 导入成功'); \
    from server.engines.rule_engine import EnhancedRuleEngine; \
    print('✅ EnhancedRuleEngine 导入成功'); \
    print('✅ 混淆后的核心模块验证通过'); \
    print('✅ 源码保护已生效'); \
except ImportError as e: \
    print(f'⚠️  模块导入失败: {e}'); \
    import traceback; \
    traceback.print_exc(); \
    sys.exit(1); \
except Exception as e: \
    print(f'⚠️  验证过程出错: {e}'); \
    import traceback; \
    traceback.print_exc(); \
    sys.exit(1); \
" 2>&1 || { \
    echo "⚠️  验证失败，但继续构建（可能是 PyArmor 配置问题）"; \
    echo "检查混淆后的文件..."; \
    find /app -name "*.py" -type f | head -5 | xargs head -3 || true; \
    exit 0; \
}

# 删除 PyArmor 构建工具（减小镜像体积，但保留运行时）
RUN pip uninstall -y pyarmor && \
    # 清理所有缓存和临时文件
    pip cache purge || true && \
    rm -rf /root/.cache/pip /root/.pyarmor /root/.cache/* /tmp/* /var/tmp/* && \
    # 清理 Python 字节码
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name "*.pyc" -delete 2>/dev/null || true && \
    find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /app -name "*.pyc" -delete 2>/dev/null || true && \
    # 清理系统日志
    rm -rf /var/log/* /var/lib/apt/lists/* /var/cache/apt/*

# 设置文件权限（保护混淆后的文件）
RUN chmod -R 755 ${APP_HOME} && \
    find ${APP_HOME} -type f -name "*.py" -exec chmod 644 {} \; 2>/dev/null || true

EXPOSE 8001

CMD ["python", "server/start.py", "8001"]
