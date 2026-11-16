FROM python:3.12-slim

WORKDIR /app

# 安装健康检查工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制代码
COPY . .

# 创建上传目录（运动文件 / 健康报告 / 物品照片）
RUN mkdir -p /app/uploads/cycling /app/uploads/hiking /app/uploads/running \
    /app/uploads/health /app/uploads/items \
    && mkdir -p /app/data

# 数据库和上传文件使用 Volume 持久化
VOLUME ["/app/data", "/app/uploads"]

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
