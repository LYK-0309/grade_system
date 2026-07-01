FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 创建必要目录
RUN mkdir -p uploads exports backups

# 暴露端口
EXPOSE 8000

# 使用 gunicorn 启动
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "run:app"]
