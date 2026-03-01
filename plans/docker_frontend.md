# Dockerfile для frontend PAD+ AI

```dockerfile
# Stage 1: Build stage
FROM node:18-alpine AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование package файлов
COPY frontend/package*.json ./

# Установка зависимостей
RUN npm ci --only=production

# Копирование исходных файлов
COPY frontend/ ./

# Сборка приложения
RUN npm run build

# Stage 2: Runtime stage
FROM nginx:alpine

# Копирование сконфигурированного nginx.conf
COPY plans/nginx.conf /etc/nginx/nginx.conf

# Копирование собранных файлов из stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Экспорт порта
EXPOSE $PORT 80

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]
```

## Описание

Этот Dockerfile использует многоступенчатую сборку для контейнеризации frontend части системы PAD+ AI:

1. Первый этап: сборка приложения с использованием Node.js
2. Второй этап: размещение собранных файлов в nginx сервере
3. Использует легковесный alpine образ для минимизации размера контейнера
4. Включает настроенный nginx.conf для правильной маршрутизации SPA приложения

## Дополнительно: nginx.conf

Для корректной работы SPA приложения, потребуется следующий nginx.conf:

```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    server {
        listen $PORT;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        location /api {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        location /ws {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}