#!/bin/bash

echo "🚀 Выполняем коммит изменений..."

# Добавляем все изменения
git add .

# Создаем коммит
git commit -m "🔧 Исправление CORS middleware и 500 ошибок

- Перенесен allow_origins в начало main.py для корректной работы middleware
- Исправлены CORS заголовки для production среды
- Улучшена обработка ошибок в middleware
- Добавлены принудительные CORS заголовки для всех ответов
- Исправлены ошибки форматирования

#fix #cors #backend #production"

echo "✅ Коммит выполнен!"
echo "Теперь нужно выполнить push вручную:"
echo "git push origin main"