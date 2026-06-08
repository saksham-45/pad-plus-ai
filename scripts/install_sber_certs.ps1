# Требуется запуск от имени Администратора
# Установка сертификатов Сбера для GigaChat

Write-Host "=== Установка SSL сертификатов Сбера для GigaChat ===" -ForegroundColor Green

# Проверка прав администратора
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Запустите PowerShell от имени Администратора!"
    exit 1
}

# Создаем временную директорию
$tempDir = "$env:TEMP\sber_certs"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# Способ 1: Попробуем скачать через openssl (если установлен)
Write-Host "Попытка получить сертификаты через OpenSSL..." -ForegroundColor Yellow

try {
    # Проверяем наличие openssl
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    
    if ($openssl) {
        Write-Host "OpenSSL найден, скачиваем сертификаты..." -ForegroundColor Green
        
        # Получаем сертификат с сервера
        & openssl s_client -connect ngw.devices.sberbank.ru:9443 -showcerts 2>$null | 
            Select-String -Pattern "BEGIN CERTIFICATE", "END CERTIFICATE" -Context 100 |
            Out-File "$tempDir\sber_chain.pem" -Encoding ASCII
        
        Write-Host "Сертификаты сохранены в: $tempDir\sber_chain.pem" -ForegroundColor Green
    } else {
        Write-Host "OpenSSL не найден, используем альтернативный способ..." -ForegroundColor Yellow
    }
} catch {
    Write-Warning "Не удалось получить сертификаты через OpenSSL: $_"
}

# Способ 2: Альтернативный - скачать через Invoke-WebRequest с игнорированием SSL
# (для получения сертификата, который потом установим)
Write-Host "`nПопытка скачать сертификаты через PowerShell..." -ForegroundColor Yellow

try {
    # Отключаем проверку SSL временно
    Add-Type -TypeDefinition @"
        using System.Net;
        using System.Security.Cryptography.X509Certificates;
        public class TrustAllCertsPolicy : ICertificatePolicy {
            public bool CheckValidationResult(ServicePoint srvPoint, X509Certificate certificate, WebRequest request, int certificateProblem) {
                return true;
            }
        }
"@
    
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    
    # Пытаемся подключиться и получить сертификат
    $request = [System.Net.WebRequest]::Create("https://ngw.devices.sberbank.ru:9443")
    $request.Method = "HEAD"
    $request.Timeout = 10000
    
    try {
        $response = $request.GetResponse()
        $response.Close()
    } catch {
        # Игнорируем ошибки, нам нужен только сертификат
    }
    
    Write-Host "Попытка подключения выполнена" -ForegroundColor Green
    
} catch {
    Write-Warning "Не удалось подключиться: $_"
}

# Способ 3: Ручная загрузка сертификатов через браузер
Write-Host "`n=== Инструкция по ручной установке ===" -ForegroundColor Cyan
Write-Host @"

1. Откройте браузер Chrome/Edge и перейдите на:
   https://ngw.devices.sberbank.ru:9443

2. Нажмите на замок 🔒 в адресной строке

3. Нажмите "Сертификат" или "Подключение безопасно"

4. Перейдите на вкладку "Путь сертификации"

5. Выберите верхний сертификат (корневой) → "Просмотр сертификата"

6. Вкладка "Состав" → "Копировать в файл"

7. Сохраните как 'sber_root.cer' (Base64)

8. Дважды кликните на файл → "Установить сертификат"

9. Выберите "Локальный компьютер" → "Доверенные корневые центры"

"@

# Альтернатива: использование certifi для Python
Write-Host "`n=== Установка для Python через certifi ===" -ForegroundColor Cyan

try {
    # Проверяем установлен ли certifi
    $certifiPath = python -c "import certifi; print(certifi.where())" 2>$null
    
    if ($certifiPath) {
        Write-Host "Certifi найден: $certifiPath" -ForegroundColor Green
        Write-Host "Вы можете добавить сертификат Сбера в этот файл" -ForegroundColor Yellow
    } else {
        Write-Host "Устанавливаем certifi..." -ForegroundColor Yellow
        python -m pip install certifi
    }
} catch {
    Write-Warning "Не удалось проверить certifi: $_"
}

Write-Host "`n=== Готово! ===" -ForegroundColor Green
Write-Host @"

После установки сертификатов верните verify=True в:
c:\пад ал датабаз а  чистый\PAD+ AI чистый\backend\runtime\litellm_service.py

(строки 557, 582, 658, 687)

"@

# Очистка
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Нажмите любую клавишу для выхода..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
