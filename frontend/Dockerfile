# Stage 1: Build stage
FROM node:18-alpine AS builder

# Установка рабочей директории
WORKDIR /app

# Копирование package файлов
COPY package*.json ./

# Установка зависимостей
RUN npm ci --only=production

# Копирование исходных файлов
COPY . ./

# Сборка приложения
RUN npm run build

# Stage 2: Runtime stage
FROM nginx:alpine

# Копирование сконфигурированного nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Копирование собранных файлов из stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Экспорт порта
EXPOSE $PORT 80

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]