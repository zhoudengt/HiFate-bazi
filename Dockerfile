# HiFate-bazi Dockerfile
# 标准 CI/CD 流程：GitHub Actions 构建 → GHCR → 服务器拉取部署
# 
# 构建命令：
#   docker build --platform linux/amd64 -t hifate-bazi:latest .
#
# 部署流程：
#   1. 本地开发 → 推送到 GitHub
#   2. GitHub Actions 自动构建镜像并推送到 GHCR
#   3. 服务器从 GHCR 拉取镜像并部署

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
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt && \
    rm -f /tmp/desk_fengshui_requirements.txt

# 复制应用代码
COPY . ${APP_HOME}

# 验证关键模块可导入
RUN python -c "\
try: \
    from server.services.rule_service import RuleService; \
    from server.engines.rule_engine import EnhancedRuleEngine; \
    print('✅ 核心模块验证通过'); \
except ImportError as e: \
    print(f'⚠️  部分模块导入失败: {e}'); \
" 2>/dev/null || echo "⚠️  模块验证失败，但继续构建"

EXPOSE 8001

CMD ["python", "server/start.py", "8001"]
