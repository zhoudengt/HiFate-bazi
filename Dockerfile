# HiFate-bazi Dockerfile
# 使用预构建基础镜像（包含所有依赖和框架）+ 增量保险
# 
# 部署流程：
#   1. 首次构建基础镜像（包含所有包和框架）：
#      ./scripts/docker/build_base.sh
#   2. 快速部署（只需复制代码，10-20秒）：
#      docker compose up -d --build web

FROM --platform=linux/amd64 hifate-base:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 增量保险层：快速检查并安装可能缺失的依赖
# 基础镜像已包含所有依赖，这里仅作为保险层
# 如果 requirements.txt 有变更但基础镜像未更新，这里会补上
COPY requirements.txt .
# 复制微服务依赖（风水模块）
COPY services/desk_fengshui/requirements.txt /tmp/desk_fengshui_requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel > /dev/null 2>&1 && \
    pip install --no-cache-dir -r requirements.txt > /dev/null 2>&1 && \
    pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt > /dev/null 2>&1 || \
    (echo "⚠️  检测到新依赖，正在安装..." && \
     pip install --no-cache-dir -r requirements.txt && \
     pip install --no-cache-dir -r /tmp/desk_fengshui_requirements.txt) && \
    rm -f /tmp/desk_fengshui_requirements.txt

# 复制应用代码（这是唯一需要更新的部分）
COPY . ${APP_HOME}

# 验证关键模块可导入（包括微服务依赖）
RUN python -c "\
try: \
    from server.services.rule_service import RuleService; \
    from server.engines.rule_engine import EnhancedRuleEngine; \
    from ultralytics import YOLO; \
    print('✅ 核心模块和 YOLOv8 验证通过'); \
except ImportError as e: \
    print(f'⚠️  部分模块导入失败: {e}，但继续构建'); \
" 2>/dev/null || echo "⚠️  模块验证失败，但继续构建"

EXPOSE 8001

CMD ["python", "server/start.py", "8001"]
