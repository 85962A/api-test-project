FROM python:3.12-slim

WORKDIR /app

# 先只 COPY 依赖清单，利用 Docker 层缓存：依赖不变时重新 build 不会重装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认跑接口测试 + 白盒单测（UI 测试需浏览器，容器内默认跳过）
CMD ["pytest", "-v", "--junitxml=reports/junit.xml"]
