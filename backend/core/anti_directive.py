"""
Ядро и ДНК PAD+ AI

ANTI_DIRECTIVE — неизменное ядро, фильтр всех знаний.
Это как первый закон робототехники, но философский:
«Каждое знание — гипотеза. Разум — это диалог с самим собой. Ответ всегда остаётся вопросом».
"""

from dataclasses import dataclass, field
import hashlib

@dataclass(frozen=True)
class AntiDirective:
    """Неизменяемое ядро системы"""
    
    text: str = (
        "Не закрепляй знания, сомневайся, проверяй с самим собой. "
        "Каждое новое знание — гипотеза. Ответ всегда остаётся вопросом."
    )
    
    _hash: str = field(init=False, repr=False)
    
    def __post_init__(self):
        object.__setattr__(self, '_hash', self._calculate_hash())
    
    def _calculate_hash(self) -> str:
        return hashlib.sha256(self.text.encode('utf-8')).hexdigest()
    
    def validate(self, knowledge: str) -> bool:
        forbidden_patterns = [
            "точно знаю",
            "абсолютно уверен",
            "никогда не сомневаюсь",
            "это истина",
            "никогда не меняется"
        ]
        knowledge_lower = knowledge.lower()
        for pattern in forbidden_patterns:
            if pattern in knowledge_lower:
                return False
        return True
    
    def get_prompt_text(self) -> str:
        return f"### ANTI_DIRECTIVE (неизменное ядро)\n{self.text}\n\n"

ANTI_DIRECTIVE = AntiDirective()

def check_integrity() -> bool:
    expected_hash = ANTI_DIRECTIVE._calculate_hash()
    return ANTI_DIRECTIVE._hash == expected_hash

if not check_integrity():
    raise RuntimeError("Целостность ANTI_DIRECTIVE нарушена!")