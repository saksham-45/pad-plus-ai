# 🧠 Cognitive UX Layer — План реализации

> **Статус:** ✅ **РЕАЛИЗОВАНО** (версия 1.0.0 от 08.04.2026)  
> См. [COGNITIVE_UX_IMPLEMENTATION.md](./COGNITIVE_UX_IMPLEMENTATION.md) для полной документации

## 🎯 Проблема

**PAD+ AI = мощный backend без проявления in UX**

- Система у нас есть ✅
- Архитектура сильная ✅
- Но пользователь этого не видит ❌

### Текущее состояние:
```
Интеллект = 8/10
Наблюдаемость = 2/10
Итог = 3/10
```

### Цель:
```
Интеллект = 8/10
Наблюдаемость = 9/10
Итог = 8/10
```

---

## 📐 Формула успеха

```
ИНТЕЛЛЕКТ × НАБЛЮДАЕМОСТЬ = ВОСПРИНИМАЕМАЯ МОЩНОСТЬ
```

---

## 🚀 6 Этапов реализации

---

### 🔴 Этап 1: Расширенный формат ответа API (1-2 часа)

**Файлы:** `backend/core/pipeline.py`, `backend/api/routes.py`

**Задача:** Изменить формат ответа чтобы включить мета-данные о когнитивном процессе.

**Изменения:**

1. Обновить `PipelineResult.to_dict()`:
```python
def to_dict(self) -> dict:
    return {
        "answer": self.response,  # Основной ответ
        "cognitive": {
            "strategy": self.strategy,
            "confidence": self.confidence,
            "health_score": self.health_score,
            "execution_time_ms": self.execution_time_ms
        },
        "memory": {
            "rag_used": self.rag_used,
            "facts_used": self.facts_used,
            "episode_id": self.episode_id,
            "sources": self.sources
        },
        "emotion": {
            "style": self.emotion_style,
            "truth_confidence": self.truth_confidence
        },
        "meta": {
            "intent": self.intent,
            "provider": self.provider,
            "errors": self.errors
        }
    }
```

2. Добавить query параметр `?explain=true` для расширенного режима

**Результат (API ответ):**
```json
{
  "answer": "Привет! Рад тебя видеть.",
  "cognitive": {
    "strategy": "simple",
    "confidence": 0.62,
    "health_score": 0.69,
    "execution_time_ms": 1855
  },
  "memory": {
    "rag_used": false,
    "facts_used": 0,
    "episode_id": null,
    "sources": {
      "rag": {"count": 0, "confidence": 0.0},
      "facts": {"count": 0},
      "episodic": {"count": 0},
      "llm": {"model": "GigaChat-2-Pro", "provider": "gigachat"}
    }
  },
  "emotion": {
    "style": {"tone": "friendly", "verbosity": "moderate", "color": "balanced"},
    "truth_confidence": 0.5
  },
  "meta": {
    "intent": "chat_general",
    "provider": "gigachat",
    "errors": []
  }
}
```

---

### 🔴 Этап 2: X-Ray мета-данные (2-3 часа)

**Файлы:** `backend/core/xray/insights.py`, `backend/core/pipeline.py`

**Задача:** Добавить когнитивные мета-данные в API ответ.

**Изменения:**

1. Создать `CognitiveExplainer` класс для генерации мета-данных:
```python
# backend/core/cognitive_explainer.py
class CognitiveExplainer:
    def generate_insights(self, result: PipelineResult) -> dict:
        return {
            "strategy": result.strategy,
            "strategy_description": self._get_strategy_desc(result.strategy),
            "pipeline_stages": self._get_pipeline_stages(result),
            "memory_usage": {
                "rag": result.rag_used,
                "facts": result.facts_used > 0,
                "episodic": result.episode_id is not None
            },
            "verification": {
                "status": self._get_verification_status(result.truth_confidence),
                "confidence": result.truth_confidence
            }
        }
    
    def _get_strategy_desc(self, strategy: str) -> str:
        descriptions = {
            "simple": "Прямая генерация ответа",
            "retrieval": "Поиск и синтез информации",
            "reasoning": "Логический анализ",
            "creative": "Творческая генерация"
        }
        return descriptions.get(strategy, "Обработка запроса")
```

2. Добавить xray секцию при `?explain=true`:
```python
# В PipelineResult.to_dict() добавить:
if explain:
    explainer = CognitiveExplainer()
    result.xray = explainer.generate_insights(result)
```

**Результат (API ответ с ?explain=true):**
```json
{
  "answer": "Привет! Рад тебя видеть.",
  "xray": {
    "strategy": "simple",
    "strategy_description": "Прямая генерация ответа",
    "pipeline_stages": ["safety", "intent", "generate"],
    "memory_usage": {
      "rag": false,
      "facts": false,
      "episodic": false
    },
    "verification": {
      "status": "neutral",
      "confidence": 0.5
    }
  }
}
```

---

### 🟡 Этап 3: Эмоциональные мета-данные (1 час)

**Файлы:** `backend/core/pipeline.py`, `backend/emotion/pad_model.py`

**Задача:** Добавить эмоциональные показатели в API ответ (без изменения текста).

**Изменения:**

1. Добавить эмоцию в мета-данные ответа:
```python
# В PipelineResult.to_dict() добавить:
"emotion": {
    "tone": emotion_style.get('tone', 'neutral'),
    "verbosity": emotion_style.get('verbosity', 'moderate'),
    "confidence": emotion_state.get('уверенность', 0.5),
    "pleasure": emotion_state.get('удовольствие', 0.0),
    "arousal": emotion_state.get('возбуждение', 0.0)
}
```

2. Эмоции влияют только на системный промпт (не на текст ответа):
```python
# В system_prompt добавить инструкцию модели:
"""
Адаптируй тон ответа на основе эмоционального контекста:
- При pleasure > 0.3: более тёплый тон
- При pleasure < -0.3: более сдержанный тон
- При confidence < 0.3: более осторожные формулировки
"""
```

**Результат (API ответ):**
```json
{
  "answer": "Привет! Рад тебя видеть.",
  "emotion": {
    "tone": "friendly",
    "verbosity": "moderate",
    "confidence": 0.5,
    "pleasure": 0.1,
    "arousal": 0.0
  }
}
```

---

### 🟡 Этап 4: Индикаторы памяти (1-2 часа)

**Файлы:** `backend/memory/episodic.py`, `backend/core/pipeline.py`

**Задача:** Показывать использование памяти через API мета-данные.

**Изменения:**

1. Добавить детальную информацию о памяти в ответ:
```python
# В PipelineResult.to_dict() обновить memory секцию:
"memory": {
    "rag_used": self.rag_used,
    "facts_used": self.facts_used,
    "episode_id": self.episode_id,
    "episodic_matches": len(similar) if similar else 0,
    "sources": self.sources,
    "consolidation_pending": self._dialogs_since_consolidation >= self._consolidation_interval
}
```

2. Frontend отображает индикаторы:
- RAG активен (когда rag_used=true)
- Факты найдены (когда facts_used > 0)
- Эпизоды учтены (когда episode_id != null)

**Результат (API ответ):**
```json
{
  "memory": {
    "rag_used": true,
    "facts_used": 3,
    "episode_id": "abc123",
    "episodic_matches": 2,
    "sources": {
      "rag": {"count": 2, "confidence": 0.8},
      "facts": {"count": 3},
      "episodic": {"count": 2}
    }
  }
}
```

---

### 🟡 Этап 5: TruthLoop метрики (1 час)

**Файлы:** `backend/core/truth_loop.py`, `backend/core/pipeline.py`

**Задача:** Добавить метрики верификации в API ответ.

**Изменения:**

1. Добавить truth секцию в ответ:
```python
# В PipelineResult.to_dict() добавить:
"truth": {
    "confidence": result.truth_confidence,
    "claims_verified": result.claims_verified,
    "claims_total": len(claims) if claims else 0,
    "status": "verified" if result.truth_confidence > 0.8 else 
              "partial" if result.truth_confidence > 0.5 else 
              "unverified",
    "sources_count": result.sources["rag"]["count"] + result.sources["facts"]["count"]
}
```

2. Frontend отображает индикатор:
- verified (confidence > 0.8)
- partial (0.5 < confidence <= 0.8)
- unverified (confidence <= 0.5)

**Результат (API ответ):**
```json
{
  "truth": {
    "confidence": 0.85,
    "claims_verified": 3,
    "claims_total": 3,
    "status": "verified",
    "sources_count": 5
  }
}
```

---

### 🟢 Этап 6: Frontend дашборд (3-4 часа)

**Файлы:** `frontend/src/components/`, `frontend/src/pages/`

**Задача:** Создать UI для отображения когнитивных мета-данных.

**Изменения:**

1. Создать `CognitivePanel.jsx`:
```jsx
// frontend/src/components/CognitivePanel.jsx
const CognitivePanel = ({ cognitive, memory, emotion, truth, xray }) => {
  return (
    <div className="cognitive-panel">
      <h4>Когнитивные метрики</h4>
      
      <div className="metric">
        <span className="label">Стратегия:</span>
        <span className="value">{xray?.strategy || cognitive?.strategy}</span>
      </div>
      
      <div className="metric">
        <span className="label">Уверенность:</span>
        <div className="confidence-bar">
          <div className="fill" style={{width: `${(cognitive?.confidence || 0) * 100}%`}} />
        </div>
        <span className="value">{((cognitive?.confidence || 0) * 100).toFixed(0)}%</span>
      </div>
      
      {memory?.rag_used && (
        <div className="metric">
          <span className="label">RAG источников:</span>
          <span className="value">{memory.sources?.rag?.count || 0}</span>
        </div>
      )}
      
      {truth && (
        <div className="metric">
          <span className="label">Верификация:</span>
          <span className={`status ${truth.status}`}>{truth.status}</span>
        </div>
      )}
      
      <div className="metric">
        <span className="label">Время:</span>
        <span className="value">{cognitive?.execution_time_ms || 0}ms</span>
      </div>
    </div>
  );
};
```

2. Добавить переключатель режимов в `ChatPage.jsx`:
```jsx
const [showMetrics, setShowMetrics] = useState(false);

// В UI:
<button onClick={() => setShowMetrics(!showMetrics)}>
  {showMetrics ? 'Скрыть метрики' : 'Показать метрики'}
</button>

{showMetrics && <CognitivePanel {...response} />}
```

3. Стили для CognitivePanel:
```css
/* frontend/src/components/CognitivePanel.css */
.cognitive-panel {
  background: #f8f9fa;
  border-left: 3px solid #007bff;
  padding: 12px 16px;
  margin-top: 16px;
  border-radius: 4px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.confidence-bar {
  width: 100px;
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
  overflow: hidden;
}

.confidence-bar .fill {
  height: 100%;
  background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
  transition: width 0.3s;
}

.status.verified { color: #28a745; }
.status.partial { color: #ffc107; }
.status.unverified { color: #dc3545; }
```

---

## 📅 Timeline

| Этап | Описание | Время | Приоритет |
|------|----------|-------|-----------|
| 1 | Расширенный API | 1-2ч | 🔴 Высокий |
| 2 | X-Ray мета-данные | 2-3ч | 🔴 Высокий |
| 3 | Эмоциональные мета-данные | 1ч | 🟡 Средний |
| 4 | Индикаторы памяти | 1-2ч | 🟡 Средний |
| 5 | TruthLoop метрики | 1ч | 🟡 Средний |
| 6 | Frontend дашборд | 3-4ч | 🟢 Низкий |

**Итого: 9-13 часов работы**

---

## ✅ Критерии успеха

1. **API возвращает полные мета-данные** (cognitive, memory, emotion, truth, xray)
2. **?explain=true возвращает xray секцию с деталями**
3. **Эмоции доступны через API** (без изменения текста ответа)
4. **Память видна через индикаторы** (rag_used, facts_used, episode_id)
5. **TruthLoop статус доступен** (verified/partial/unverified)
6. **Frontend отображает CognitivePanel с метриками**

---

## 🔄 Порядок реализации

1. Сначала **Этап 1** (API) — основа для всего
2. Затем **Этап 2** (X-Ray) — объяснения
3. Параллельно **Этапы 3-5** (эмоции, память, верификация)
4. В конце **Этап 6** (Frontend) — визуализация

---

## 🎯 Первый шаг

Начать с **Этапа 1**: изменить `PipelineResult.to_dict()` и добавить `?explain=true` параметр.