"""
Experience Analyzer — CLI-отчёт по накопленному опыту.

Запуск:
    python -m core.experience.analyzer
    python -m core.experience.analyzer --min-significance 0.5
    python -m core.experience.analyzer --recent 20
"""

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime

from .store import ExperienceStore


def analyze(store: ExperienceStore, min_sig: float = 0.0, recent: int = 0):
    records = store.load_all()
    if not records:
        print("Нет записей опыта.")
        return

    if recent > 0:
        records = records[-recent:]

    total = len(records)
    if total == 0:
        print("Нет записей после фильтрации.")
        return

    sigs = [r.get("significance", 0) for r in records]
    types = [r.get("interaction_type", "unknown") for r in records]
    deltas = [r.get("delta", "") for r in records]

    print(f"{'='*60}")
    print(f"  Отчёт Experience Layer")
    print(f"  Записей: {total}")
    print(f"  Период:  {records[0].get('timestamp','?')[:10]} — {records[-1].get('timestamp','?')[:10]}")
    print(f"{'='*60}")

    # Распределение по типам
    print(f"\n  Распределение по типам:")
    type_dist = Counter(types)
    for t, cnt in sorted(type_dist.items(), key=lambda x: -x[1]):
        pct = cnt / total * 100
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        print(f"    {t:<20s} {cnt:>4d} ({pct:5.1f}%) {bar}")

    # Significance
    avg_sig = sum(sigs) / total
    high = sum(1 for s in sigs if s >= 0.7)
    print(f"\n  Significance:")
    print(f"    средняя:     {avg_sig:.3f}")
    print(f"    высокая>=0.7: {high} ({high/total*100:.1f}%)")
    print(f"    мин/макс:    {min(sigs):.3f} / {max(sigs):.3f}")

    # Дельта-распределение
    print(f"\n  Дельта-распределение:")
    delta_dist = Counter(deltas)
    for d, cnt in delta_dist.most_common():
        print(f"    {cnt:>4d} x {d}")

    # Последние записи
    print(f"\n  Последние записи (до 10):")
    for r in records[-10:]:
        print(f"    [{r.get('interaction_type','?'):<18s}] sig={r.get('significance',0):.3f}  "
              f"\"{r.get('user_message','')[:50]:50s}\"  ->  \"{r.get('ai_response','')[:50]:50s}\"")

    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Experience Layer Analyzer")
    parser.add_argument("--min-significance", type=float, default=0.0, help="Мин. significance (0-1)")
    parser.add_argument("--recent", type=int, default=0, help="Показать только последние N записей")
    args = parser.parse_args()

    store = ExperienceStore()
    analyze(store, min_sig=args.min_significance, recent=args.recent)


if __name__ == "__main__":
    main()
