# HiFate-bazi Dockerfile
# 标准 CI/CD 流程：GitHub Actions 构建 → ACR → 服务器拉取部署
# 
# 构建命令：
#   docker build --platform linux/amd64 -t hifate-bazi:latest .
#
# 部署流程：
#   1. 本地开发 → 推送到 GitHub
#   2. GitHub Actions 自动构建镜像并推送到 ACR
#   3. 服务器从 ACR 拉取镜像并部署

FROM --platform=linux/amd64 python:3.11-slim

LABEL maintainer="HiFate Team"
LABEL description="HiFate-bazi application image"

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

# 复制并安装依赖
COPY requirements.txt .
COPY services/desk_fengshui/requirements.txt /tmp/desk_fengshui_requirements.txt

# 合并安装步骤，减少层数并立即清理
RUN pip install --no-cache-dir -r requirements.txt && \
    TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu \
    pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision --no-deps && \
    pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt && \
    rm -f /tmp/desk_fengshui_requirements.txt && \
    # 验证关键依赖是否正确安装
    echo "🔍 验证关键依赖..." && \
    python -c "import uvicorn; print('✅ uvicorn:', uvicorn.__version__)" && \
    python -c "import fastapi; print('✅ fastapi:', fastapi.__version__)" && \
    python -c "import pymysql; print('✅ pymysql:', pymysql.__version__)" && \
    python -c "import redis; print('✅ redis:', redis.__version__)" && \
    python -c "import grpc; print('✅ grpc:', grpc.__version__)" && \
    echo "✅ 关键依赖验证通过" && \
    # 立即清理所有缓存和临时文件
    pip cache purge || true && \
    rm -rf /root/.cache/pip /root/.cache/torch /root/.cache/huggingface /tmp/pip-* /var/tmp/* && \
    # 清理 Python 字节码缓存（不影响包功能）
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name "*.pyc" -delete 2>/dev/null || true && \
    # 清理大型库的测试、文档和示例文件（减少空间，但不删除包元数据）
    find /usr/local/lib/python3.11/site-packages -name "test" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.md" -not -path "*/dist-info/*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.rst" -not -path "*/dist-info/*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.html" -not -path "*/dist-info/*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.css" -not -path "*/dist-info/*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.js" -not -path "*/dist-info/*" -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "examples" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "example" -type d -exec rm -rf {} + 2>/dev/null || true && \
    # 注意：不删除 .txt 文件，因为可能包含包的重要元数据
    # 不删除 dist-info 目录中的任何文件（包元数据）
    echo "✅ 依赖安装和清理完成"

# ============================================
# 复制应用代码
# ============================================

# 复制所有应用代码
COPY . /tmp/source

# 清理不必要的文件，减少磁盘占用
RUN find /tmp/source -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /tmp/source -name "*.pyc" -delete 2>/dev/null || true && \
    find /tmp/source -name "*.pyo" -delete 2>/dev/null || true && \
    find /tmp/source -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /tmp/source -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /tmp/source/.git /tmp/source/node_modules /tmp/source/logs /tmp/source/tests /tmp/source/docs

# 复制代码到应用目录并最终清理
RUN cp -r /tmp/source/* ${APP_HOME}/ && \
    rm -rf /tmp/source && \
    # 清理系统临时文件
    rm -rf /tmp/* /var/tmp/* && \
    # 清理 apt 缓存（如果还有）
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/cache/debconf/* && \
    # 清理 Python 缓存（最终清理）
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11 -name "*.pyc" -delete 2>/dev/null || true && \
    find ${APP_HOME} -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find ${APP_HOME} -name "*.pyc" -delete 2>/dev/null || true && \
    # 注意：不删除构建工具（gcc、g++、make），因为某些包在运行时可能需要
    # 只清理 apt 缓存
    apt-get clean && \
    # 显示最终镜像大小
    du -sh /usr/local/lib/python3.11/site-packages 2>/dev/null || true && \
    # 列出已安装的关键包
    pip list | grep -E "uvicorn|fastapi|pymysql|redis|grpc" || true

# 验证关键文件存在
RUN echo "🔍 验证关键文件..." && \
    if [ ! -f "${APP_HOME}/server/start.py" ]; then \
        echo "❌ 错误: server/start.py 不存在"; \
        ls -la ${APP_HOME}/ || true; \
        ls -la ${APP_HOME}/server/ || true; \
        exit 1; \
    fi && \
    if [ ! -f "${APP_HOME}/server/main.py" ]; then \
        echo "❌ 错误: server/main.py 不存在"; \
        exit 1; \
    fi && \
    echo "✅ 关键文件验证通过"

# 验证依赖模块可以导入（最终验证）
RUN echo "🔍 最终验证依赖模块..." && \
    python -c "import uvicorn; import fastapi; import pymysql; import redis; import grpc; print('✅ 所有关键模块可以正常导入')" && \
    echo "✅ 依赖模块验证通过"

# 注意：不在此处验证模块导入，因为：
# 1. 模块导入问题会在运行时暴露
# 2. 构建时可能缺少运行时环境（数据库、Redis等）
# 3. 健康检查已经可以验证应用是否正常

# 设置文件权限
RUN chmod -R 755 ${APP_HOME}

EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "server/start.py", "8001"]
