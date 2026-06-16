# Разработчику HEALER Viewer

## Технологии

- **Python 3.12+** — только stdlib
- **HTTP.server** — встроенный HTTP-сервер
- **JSON** — сериализация данных
- **Чистый HTML/CSS/JS** — без фреймворков

## Структура файлов

```
viewer.py                    # Главный файл (350+ строк)
├── X-RAY integration        # Инициализация, трейсинг
├── HTTP server              # Класс ViewerHandler
│   ├── GET handlers         # /api/status, /api/traces, /api/invoke-healer
│   ├── POST handlers        # /api/patch, /api/patch/apply, /api/patch/rollback
│   └── Static files         # index.html
├── main()                   # Точка входа
└── HEALER Direct Import     # Прямой вызов run_diagnostics()

static/index.html            # Веб-интерфейс (450+ строк)
├── CSS                      # Тёмная тема, сетка, компоненты
├── HTML                     # 4 вкладки, панели, таблицы
└── JS                       # fetch API, render, patches
    ├── refreshAll()         # Обновление обзора
    ├── invokeHealer()       # Запуск диагностики
    ├── quickPatch()         # Применение патча
    ├── loadTraces()         # Загрузка трейсов
    └── render*()            # Отрисовка таблиц и деревьев

data/trace_store/            # X-RAY трейсы (создаются автоматически)
```

## Как добавить новый API endpoint

1. В `viewer.py` добавить метод-обработчик:
```python
def _handle_my_endpoint(self):
    data = {"result": "ok"}
    self._send_json(data)
```

2. Зарегистрировать в `do_GET` или `do_POST`:
```python
handler_map = {
    "/api/my-endpoint": self._handle_my_endpoint,
    # ...
}
```

3. В `index.html` вызвать через fetch:
```javascript
const data = await fetch('/api/my-endpoint').then(r => r.json());
```

## Как добавить новую вкладку в интерфейс

1. В `index.html` добавить tab и tab-content:
```html
<div class="tab" onclick="switchTab('my-tab')">My Tab</div>
<div id="tab-my-tab" class="tab-content">...</div>
```

2. В `switchTab()` добавить обработчик:
```javascript
if (name === 'my-tab') loadMyTab();
```

## Проблемы с кодировкой на Windows

- Python stdout на Windows использует cp1251/cp866
- При subprocess русский текст превращается в кракозябры
- **Решение:** прямой Python-import вместо subprocess
- Убедись что `_send_json` не использует `default=str`

## Отладка

```bash
# Проверить синтаксис
python -c "import py_compile; py_compile.compile('viewer.py', doraise=True)"

# Проверить API
curl http://127.0.0.1:8085/api/status

# Проверить русский текст в ответе
curl -s http://127.0.0.1:8085/api/healer-result | python -c "import sys,json; d=json.load(sys.stdin); print(d['reports'][0]['message'])"
```

## Известные проблемы

1. **HEALER не найден** — viewer ищет `../HEALER/`. Если HEALER в другой папке, поправить `HEALER_DIR` в `viewer.py`.
2. **Русский текст в кракозябрах** — убедись что viewer использует прямой импорт HEALER, а не subprocess.
3. **Тост пропадает** — 12 секунд. Задаётся в `showToast()`.
4. **После патча нужен рестарт** — viewer не умеет hot-reload.
