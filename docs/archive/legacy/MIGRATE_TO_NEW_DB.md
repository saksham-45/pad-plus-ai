# 🚀 Миграция на новую базу данных

## Ситуация

У вас была старая версия PAD+ AI с базой данных, содержащей все наработки (111 эпизодов, 4 знания). Затем вы создали новый проект в GitHub и новый проект в Render с новой пустой базой. Поэтому в Render метрики показывают 0.

## Решение

Перенести данные из старой базы в новую.

## Шаг 1: Экспорт данных из старой базы

Запустите скрипт экспорта:

```bash
python export_old_data.py
```

Этот скрипт:
- Экспортирует все эпизоды из старой базы в `exported_episodes.json`
- Экспортирует все знания из старой базы в `exported_knowledge.json`
- Импортирует данные в новую базу

## Шаг 2: Обновить конфигурацию

Обновите `.env` файл с новой базой:

```ini
DATABASE_URL=postgresql://postgres.uixqufwbxefvkmhmausm:i8Edeq5rosD8sAeV@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
```

## Шаг 3: Обновить переменные окружения в Render

1. Зайти в [Render Dashboard](https://dashboard.render.com/)
2. Найти сервис `pad-plus-ai-deploy`
3. Перейти в раздел "Environment" (Окружение)
4. Обновить переменную `DATABASE_URL` на новое значение:
   ```
   postgresql://postgres.uixqufwbxefvkmhmausm:i8Edeq5rosD8sAeV@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
   ```
5. Сохранить изменения

## Шаг 4: Редеплой в Render

1. В Render Dashboard нажать "Manual Deploy"
2. Выбрать последний коммит
3. Нажать "Deploy"
4. Подождать завершения деплоя (5-10 минут)

## Шаг 5: Проверка

После завершения деплоя:

```bash
# Проверка API
curl https://pad-plus-ai-deploy.onrender.com/api/v1/memory/dashboard

# Ожидаемый результат:
{
  "episodic": {"total_episodes": 111, ...},
  "semantic": {"total_knowledge": 4, ...}
}
```

## Шаг 6: Обновление GitHub

Закоммитьте изменения в GitHub:

```bash
git add .env
git commit -m "feat: migrate to new database"
git push origin main
```

## Проверка после миграции

1. **Локально**: `python debug_render_memory.py` - должно показывать 111 эпизодов, 4 знания
2. **В Render**: `curl https://pad-plus-ai-deploy.onrender.com/api/v1/memory/dashboard` - должно показывать 111 эпизодов, 4 знания
3. **Фронтенд**: Открыть https://pad-plus-ai.onrender.com - метрики должны отображаться

## Если что-то пошло не так

1. Проверить логи деплоя в Render
2. Убедиться, что `DATABASE_URL` правильный
3. Проверить подключение к новой базе:
   ```bash
   python debug_render_memory.py
   ```
4. Создать issue в GitHub с описанием проблемы

## Дополнительная информация

- **Старая база**: `postgresql://postgres.hgjbjccpeirwrabbcjhr:TiMuPom13Q5OfKBi@aws-1-eu-central-1.pooler.supabase.com:6543/postgres`
- **Новая база**: `postgresql://postgres.uixqufwbxefvkmhmausm:i8Edeq5rosD8sAeV@aws-1-eu-central-1.pooler.supabase.com:6543/postgres`
- **Данные**: 111 эпизодов, 4 знания

После миграции все наработки будут доступны в новой базе и в Render.