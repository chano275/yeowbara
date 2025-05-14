FROM node:22.13.1

# 시스템 타임존, git 등 필요한 패키지 설치 (선택)
RUN apt-get update && apt-get install -y git

# 앱 작업 디렉토리
WORKDIR /app

# 종속성 먼저 복사 후 설치
COPY package*.json ./
RUN npm install

# 전체 코드 복사
COPY . .

# 포트 노출 (Vite 기본: 5173)
EXPOSE 5173
