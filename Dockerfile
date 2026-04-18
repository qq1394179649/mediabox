# MediaBox Dockerfile
# Multi-stage build for smaller production image

# ==================== Build Stage ====================
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# ==================== Production Stage ====================
FROM python:3.11-slim

# 安全配置
RUN useradd --create-home --shell /bin/bash mediabox && \
    mkdir /app && \
    chown -R mediabox:mediabox /app

WORKDIR /app

# 从 builder 复制 Python 虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制应用代码
COPY --chown=mediabox:mediabox . .

# 创建必要目录
RUN mkdir -p /app/data /app/logs && \
    chown -R mediabox:mediabox /app/data /app/logs

# 配置 Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 切换到非 root 用户
USER mediabox

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
