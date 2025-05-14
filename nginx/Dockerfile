FROM nginx:latest

# 커스텀 설정 복사
COPY nginx.conf /etc/nginx/conf.d/custom.conf

# Nginx 포그라운드 실행
CMD ["nginx", "-g", "daemon off;"]