"""
🔗 Integration Bridge — соединяет PAD+ X-RAY с HEALER

Позволяет:
- Релеить события PAD+ пайплайна в HEALER TraceStore
- Запускать диагностику HEALER на коде PAD+
- Использовать AST-патчер HEALER с верификацией
- Просматривать трейсы PAD+ через HEALER Viewer
"""

from .healer_bridge import HealerBridge, get_healer_bridge

__all__ = ["HealerBridge", "get_healer_bridge"]
