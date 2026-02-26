# GitHub Actions для CI/CD PAD+ AI

## Описание

Ниже приведена конфигурация GitHub Actions для автоматизации процессов CI/CD проекта PAD+ AI. Эти workflow обеспечивают тестирование, проверку кода и автоматическое развертывание.

## Основные workflow

### 1. Тестирование кода (.github/workflows/test.yml)

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest black flake8

    - name: Lint with flake8
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

    - name: Check formatting with Black
      run: |
        black --check .

    - name: Test with pytest
      run: |
        python -m pytest tests/ -v

    - name: Run backend import test
      run: |
        cd backend && python -c "import main; print('Backend imports successfully')"
```

### 2. Сборка и публикация Docker образов (.github/workflows/docker.yml)

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*.*.*' ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push-image:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata for backend
        id: backend-meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend

      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: plans/Dockerfile.backend
          push: true
          tags: ${{ steps.backend-meta.outputs.tags }}
          labels: ${{ steps.backend-meta.outputs.labels }}

      - name: Extract metadata for frontend
        id: frontend-meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend

      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: plans/Dockerfile.frontend
          push: true
          tags: ${{ steps.frontend-meta.outputs.tags }}
          labels: ${{ steps.frontend-meta.outputs.labels }}
```

### 3. Автоматическое развертывание на Render (.github/workflows/deploy.yml)

```yaml
name: Deploy to Render

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Trigger Render deployment
      run: |
        curl -X POST "${{ secrets.RENDER_DEPLOY_HOOK }}"
```

### 4. Проверка безопасности (.github/workflows/security.yml)

```yaml
name: Security Scan

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sundays

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Run security audit
      run: |
        pip install pip-audit
        pip-audit --requirement requirements.txt
```

## Необходимые секреты для репозитория

Для работы GitHub Actions потребуется настроить следующие секреты в репозитории:

1. `RENDER_DEPLOY_HOOK` - URL вебхука для триггера деплоя на Render
2. `OPENROUTER_API_KEY` - API ключ для OpenRouter (если используется в тестах)

## Инструкции по настройке

1. Создайте директорию `.github/workflows/` в репозитории
2. Поместите каждый workflow файл в отдельный YAML файл
3. Настройте секреты в настройках репозитория GitHub
4. При первом запуске убедитесь, что все зависимости указаны правильно

## Особенности

- Workflow автоматически запускаются при пуше в основную ветку
- Тесты запускаются для нескольких версий Python для обеспечения совместимости
- Docker образы публикуются в GitHub Container Registry
- Система безопасности регулярно проверяет зависимости на уязвимости