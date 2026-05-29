FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制代码
COPY . .

# 创建上传目录（骑行/徒步/跑步的运动文件）
RUN mkdir -p /app/uploads/cycling /app/uploads/hiking /app/uploads/running \
    && mkdir -p /app/data

# 数据库和上传文件使用 Volume 持久化
VOLUME ["/app/data", "/app/uploads"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
