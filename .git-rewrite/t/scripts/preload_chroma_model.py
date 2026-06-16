"""
Скрипт для предзагрузки ChromaDB embedding модели

Запускается во время build на Render чтобы избежать задержек при первом запросе
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("ПРЕДЗАГРУЗКА CHROMADB EMBEDDING MODEL")
print("=" * 60)

try:
    from sentence_transformers import SentenceTransformer
    
    model_name = "all-MiniLM-L6-v2"
    print(f"🔄 Загрузка модели: {model_name}")
    print(f"📁 Это может занять 1-2 минуты при первом запуске...")
    
    model = SentenceTransformer(model_name)
    
    print(f"✅ Модель успешно загружена!")
    print(f"📊 Размер модели: ~79 MB")
    print(f"📍 Путь к кэшу: /opt/render/.cache/chroma/")
    
    # Проверка что модель работает
    test_embedding = model.encode(["test"])
    print(f"✅ Тестовый эмбеддинг выполнен успешно")
    print(f"📏 Размер эмбеддинга: {test_embedding.shape}")
    
    print("\n" + "=" * 60)
    print("ГОТОВО! Модель готова к использованию")
    print("=" * 60)
    
except ImportError as e:
    print(f"❌ Ошибка: sentence-transformers не установлен")
    print(f"   Установите: pip install sentence-transformers")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка при загрузке модели: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
