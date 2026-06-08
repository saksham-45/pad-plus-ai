# ============================================================================
# PAD+ AI — Скрипт исправления RLS политик
# ============================================================================
# Этот скрипт применяет исправления RLS политик для таблицы user_api_keys
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PAD+ AI — Исправление RLS политик" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия .env файла
$envPath = Join-Path $PSScriptRoot "..\.env"
if (-Not (Test-Path $envPath)) {
    Write-Host "❌ Ошибка: Файл .env не найден!" -ForegroundColor Red
    Write-Host "   Создайте .env файл из .env.example" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Файл .env найден" -ForegroundColor Green

# Загрузка переменных окружения
Write-Host "📥 Загрузка переменных окружения..." -ForegroundColor Cyan
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim('"')
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

# Проверка DATABASE_URL
$databaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL")
if (-Not $databaseUrl) {
    Write-Host "❌ Ошибка: DATABASE_URL не настроен!" -ForegroundColor Red
    Write-Host "   Добавьте DATABASE_URL в файл .env" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ DATABASE_URL найден: ${databaseUrl:0:30}..." -ForegroundColor Green

# Проверка наличия psycopg2
Write-Host ""
Write-Host "🔍 Проверка psycopg2..." -ForegroundColor Cyan
try {
    Add-Type -AssemblyName System.Data
    # Пытаемся импортировать psycopg2 через Python
    $pythonCheck = python -c "import psycopg2; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ psycopg2 установлен" -ForegroundColor Green
    } else {
        Write-Host "⚠️  psycopg2 не найден, пробуем установить..." -ForegroundColor Yellow
        python -m pip install psycopg2-binary
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ psycopg2 успешно установлен" -ForegroundColor Green
        } else {
            Write-Host "❌ Не удалось установить psycopg2" -ForegroundColor Red
            Write-Host "   Установите вручную: pip install psycopg2-binary" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "⚠️  Не удалось проверить psycopg2: $_" -ForegroundColor Yellow
}

# Путь к миграции
$migrationFile = Join-Path $PSScriptRoot "..\backend\database\migrations\007_fix_api_keys_rls.sql"
if (-Not (Test-Path $migrationFile)) {
    Write-Host "❌ Ошибка: Файл миграции не найден: $migrationFile" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Файл миграции найден" -ForegroundColor Green

# Чтение SQL миграции
$migrationSql = Get-Content $migrationFile -Raw

# Вывод инструкции для пользователя
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ВАЖНОЕ СООБЩЕНИЕ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для применения RLS политик есть два варианта:" -ForegroundColor White
Write-Host ""
Write-Host "1️⃣  [РЕКОМЕНДУЕТСЯ] Через Supabase Dashboard:" -ForegroundColor Yellow
Write-Host "   - Откройте https://supabase.com/dashboard" -ForegroundColor White
Write-Host "   - Перейдите в SQL Editor" -ForegroundColor White
Write-Host "   - Скопируйте содержимое файла: $migrationFile" -ForegroundColor White
Write-Host "   - Нажмите Run" -ForegroundColor White
Write-Host ""
Write-Host "2️⃣  Через команду psql (если установлен):" -ForegroundColor Yellow
Write-Host "   psql '$databaseUrl' -f '$migrationFile'" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Предложить применить через psql если доступен
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if ($psqlPath) {
    Write-Host "🔍 psql найден: $($psqlPath.Source)" -ForegroundColor Green
    $confirm = Read-Host "Применить миграцию через psql? (y/n)"
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        Write-Host "🔄 Применение миграции..." -ForegroundColor Cyan
        & psql -d $databaseUrl -f $migrationFile
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Миграция успешно применена!" -ForegroundColor Green
        } else {
            Write-Host "❌ Ошибка при применении миграции" -ForegroundColor Red
        }
    }
} else {
    Write-Host "⚠️  psql не найден. Используйте Supabase Dashboard." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Следующие шаги:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Перезапустите backend:" -ForegroundColor White
Write-Host "   python backend/main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Попробуйте добавить API ключ через frontend" -ForegroundColor White
Write-Host ""
Write-Host "3. Проверьте логи — ошибка 42501 должна исчезнуть" -ForegroundColor White
Write-Host ""
Write-Host "Готово!" -ForegroundColor Green
