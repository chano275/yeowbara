FROM python:3.13

WORKDIR /app

# 기본 툴 설치
RUN apt-get update && apt-get install -y \
    curl build-essential git gnupg ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# kubectl 설치
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# requirements.txt 복사 후 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY app/ ./app/

EXPOSE 8000

# 개발용 reload 포함 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
