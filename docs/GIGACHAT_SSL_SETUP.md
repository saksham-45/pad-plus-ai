# Настройка SSL сертификатов для GigaChat

## Способ 1: Автоматическая установка (рекомендуется)

```powershell
# Запустите PowerShell от имени Администратора и выполните:
cd "c:\пад ал датабаз а  чистый\PAD+ AI чистый"
.\install_sber_certs.ps1
```

## Способ 2: Ручная установка

### Шаг 1: Скачать сертификаты Сбера

1. Откройте браузер и перейдите на: https://ngw.devices.sberbank.ru:9443
2. Нажмите на замок 🔒 в адресной строке
3. "Сертификат" → "Путь сертификации"
4. Экспортируйте каждый сертификат в цепочке:
   - Корневой (Root CA)
   - Промежуточный (Intermediate)
   - Конечный (End Entity)

### Шаг 2: Установить в Windows

1. Дважды кликните по `.cer` файлу
2. "Установить сертификат"
3. "Локальный компьютер" → "Далее"
4. "Поместить все сертификаты в следующее хранилище"
5. "Обзор" → "Доверенные корневые центры сертификации"
6. "Далее" → "Готово"

### Шаг 3: Установить для Python

```bash
# Найдите путь к cacert.pem
python -c "import certifi; print(certifi.where())"

# Скопируйте содержимое сертификата в конец файла cacert.pem
# Или установите через pip
pip install certifi
```

## Способ 3: Использование переменной окружения

```bash
# Скачайте сертификат и укажите путь
set REQUESTS_CA_BUNDLE=C:\path\to\sber_root.crt
set CURL_CA_BUNDLE=C:\path\to\sber_root.crt
```

## Способ 4: В коде Python (для разработки)

```python
import os
import ssl
import certifi

# Создаем SSL контекст с сертификатом Сбера
ssl_context = ssl.create_default_context(cafile=certifi.where())
# Добавляем сертификат Сбера
ssl_context.load_verify_locations('sber_root.crt')
```

## Проверка

```bash
# Проверьте подключение
curl -v https://ngw.devices.sberbank.ru:9443/api/v2/oauth

# Или через Python
python -c "import requests; requests.get('https://ngw.devices.sberbank.ru:9443', verify=True)"
```

## Важно

После установки сертификатов **верните `verify=True`** в `litellm_service.py`:
- Строки 557, 582, 658, 687

Это обеспечит безопасное соединение.
