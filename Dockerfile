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

# 配置 pip 使用国内源（加速下载，失败时使用官方源）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn || \
    (pip config unset global.index-url && pip config unset global.trusted-host && echo "⚠️ 使用官方PyPI源")

# 升级 pip、setuptools、wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制并安装依赖
COPY requirements.txt .

# 安装核心依赖（分步执行，确保每步成功）
# 优先使用国内源，失败时自动回退到官方源
RUN echo "=== 安装核心依赖 ===" && \
    (pip install --no-cache-dir -r requirements.txt || \
     pip install --no-cache-dir -i https://pypi.org/simple -r requirements.txt) && \
    echo "✅ requirements.txt 安装完成"

# 验证核心包安装成功
RUN echo "=== 验证核心包 ===" && \
    python -c "import uvicorn; print('✅ uvicorn:', uvicorn.__version__)" && \
    python -c "import fastapi; print('✅ fastapi:', fastapi.__version__)" && \
    python -c "import starlette; print('✅ starlette:', starlette.__version__)" && \
    python -c "import pydantic; print('✅ pydantic:', pydantic.__version__)" && \
    python -c "import grpc; print('✅ grpc:', grpc.__version__)" && \
    python -c "import redis; print('✅ redis:', redis.__version__)" && \
    python -c "import pymysql; print('✅ pymysql:', pymysql.__version__)" && \
    python -c "import pytz; print('✅ pytz:', pytz.__version__)" && \
    echo "✅ 核心包验证完成"

# 安装 PyTorch CPU 版本（可选，用于 YOLO）
RUN echo "=== 安装 PyTorch CPU 版本 ===" && \
    pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision --no-deps || echo "⚠️ PyTorch 安装跳过（可选依赖）"

# 安装风水分析依赖
COPY services/desk_fengshui/requirements.txt /tmp/desk_fengshui_requirements.txt
RUN echo "=== 安装风水分析依赖 ===" && \
    pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt && \
    rm -f /tmp/desk_fengshui_requirements.txt && \
    echo "✅ 风水分析依赖安装完成"

# 清理缓存（保守清理，不删除可能影响包的文件）
RUN echo "=== 清理缓存 ===" && \
    pip cache purge 2>/dev/null || true && \
    rm -rf /root/.cache/pip /root/.cache/torch /root/.cache/huggingface /tmp/pip-* /var/tmp/* && \
    # 只清理 __pycache__ 目录（安全）
    find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    # 只清理测试目录（安全）
    find /usr/local/lib/python3.11/site-packages -name "test" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true && \
    echo "✅ 缓存清理完成"

# 再次验证核心包（确保清理后仍可用）
RUN echo "=== 最终验证 ===" && \
    python -c "import uvicorn; import fastapi; import grpc; print('✅ 所有核心包验证通过')"

# ============================================
# 复制应用代码
# ============================================

# 复制所有应用代码（排除不必要的文件由 .dockerignore 控制）
COPY . ${APP_HOME}

# 清理应用代码中的缓存文件
RUN echo "=== 清理应用代码缓存 ===" && \
    find ${APP_HOME} -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find ${APP_HOME} -name "*.pyc" -delete 2>/dev/null || true && \
    find ${APP_HOME} -name "*.pyo" -delete 2>/dev/null || true && \
    find ${APP_HOME} -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf ${APP_HOME}/.git ${APP_HOME}/node_modules ${APP_HOME}/logs 2>/dev/null || true && \
    # 清理系统临时文件
    rm -rf /tmp/* /var/tmp/* && \
    # 清理 apt 缓存
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    # 清理构建工具（减少镜像大小）
    apt-get purge -y gcc g++ make 2>/dev/null || true && \
    apt-get autoremove -y 2>/dev/null || true && \
    apt-get clean && \
    echo "✅ 清理完成"

# 验证关键文件存在
RUN echo "验证关键文件..." && \
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
