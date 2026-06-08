"""
PipelineContext — контекст выполнения пайплайна.

Содержит все входные данные для одной итерации pipeline.execute():
- user_message, context, session_id
- api_key, provider (из Фазы 1)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PipelineContext:
    user_message: str
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = None
