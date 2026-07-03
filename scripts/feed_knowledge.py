"""
Скрипт пакетной загрузки файлов в RAG-базу знаний PAD+.

Использование:
    python feed_knowledge.py --dir ./knowledge
    python feed_knowledge.py --dir ./knowledge --url https://pad-plus-ai.onrender.com --token sntrys_...
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Установи httpx: pip install httpx")
    sys.exit(1)


def feed_knowledge(
    directory: str,
    base_url: str = "http://localhost:8642",
    token: str | None = None,
    collection_id: str | None = None,
):
    KNOWN_EXTS = {".txt", ".md", ".pdf", ".csv", ".json", ".xml", ".html", ".docx"}

    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Директория не найдена: {directory}")
        return

    files = sorted(
        [f for f in dir_path.iterdir() if f.suffix.lower() in KNOWN_EXTS],
        key=lambda f: f.name,
    )

    if not files:
        print(f"Нет файлов с известными расширениями ({', '.join(KNOWN_EXTS)}) в {directory}")
        return

    print(f"Найдено {len(files)} файлов в {directory}")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ok = 0
    fail = 0
    upload_url = f"{base_url.rstrip('/')}/api/v1/documents/upload"
    files_list = files[:50]  # макс 50 за раз

    for f in files_list:
        print(f"  [{ok + fail + 1}/{len(files_list)}] Загрузка {f.name}... ", end="", flush=True)

        try:
            with open(f, "rb") as fh:
                form = {"file": (f.name, fh, "application/octet-stream")}
                if collection_id:
                    form["collection_id"] = (None, collection_id)

                resp = httpx.post(upload_url, files=form, headers=headers, timeout=120)

            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"✅ id={data.get('id', '?')[:12]} status={data.get('status', '?')}")
                ok += 1
            elif resp.status_code == 401:
                print("❌ 401 Unauthorized — нужен токен")
                fail += 1
                break
            elif resp.status_code == 413:
                print(f"❌ Слишком большой (>50MB)")
                fail += 1
            else:
                print(f"❌ {resp.status_code}: {resp.text[:120]}")
                fail += 1

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            fail += 1

        time.sleep(0.5)

    print(f"\nГотово: ✅ {ok} загружено, ❌ {fail} ошибок")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузка файлов в RAG базу знаний PAD+")
    parser.add_argument("--dir", default="./knowledge", help="Директория с файлами (по умолч. ./knowledge)")
    parser.add_argument("--url", default="http://localhost:8642", help="Базовый URL PAD+ (по умолч. http://localhost:8642)")
    parser.add_argument("--token", help="JWT токен аутентификации")
    parser.add_argument("--collection", help="ID коллекции (опционально)")
    args = parser.parse_args()

    feed_knowledge(
        directory=args.dir,
        base_url=args.url,
        token=args.token,
        collection_id=args.collection,
    )
