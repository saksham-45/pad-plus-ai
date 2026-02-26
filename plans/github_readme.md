# NeuroMind AI (PAD+ AI v3.5) - Cognitive Layer for LLMs

## Overview

NeuroMind AI (also known as PAD+ AI v3.5) is an advanced cognitive system that adds emotions and self-awareness to any Large Language Model (LLM). The system implements a complex cognitive architecture including multiple cognitive layers: memory, emotions, autonomy, knowledge verification, and meta-cognitive control.

## Key Features

### 💬 Communication
- **Chat** - intelligent dialogs with RAG v3.0
- **Streaming Chat** - SSE streaming responses
- **WebSocket** - real-time communication

### 🧠 Memory
- **RAG Memory v3.0** - semantic memory with ChromaDB
  - Topic classification of dialogs
  - Entity and relationship extraction
  - Hybrid search with ranking
  - LLM summarization
- **Episodic Memory** - episodic memory with timestamps
- **Semantic Memory** - general knowledge and concepts
- **Fact Memory** - structured facts (subject-predicate-object)
- **Roots Memory** - fundamental principles (philosophy, ethics, identity)
- **Persona** - evolving personality with character traits
- **Hygiene** - automatic memory cleaning
- **Consolidation** - memory consolidation similar to sleep

### 😊 Emotions
- **PAD+ Model** - 6 dimensions:
  - Pleasure, Arousal, Dominance
  - Curiosity, Confidence, Social Connection
- Automatic emotion decay
- Influence on communication style

### 🔄 Autonomy
- **Planner** - autonomous questions and tasks
- **Hierarchical Planner** - multi-level goals (Goals → Tasks → Actions)
- **Dreams** - "dreams" for processing memory during idle periods
- **Auto-reflection** - every N dialogs
- **Quality Assessor** - self-assessment of answer quality
- **Knowledge Auto-Updater** - automatic knowledge graph population

### 🛡️ Safety
- **Safety Layer** - injection protection
- **Anti-Loop Guard** - protection against loops
- **Rate Limiter** - request limiting

### 🧩 Meta-Cognition
- **Meta Controller** - strategy management
- **Intent Router** - intent classification
- **Truth Loop** - statement verification
- **Health Monitor** - cognitive health
- **Cognitive Load** - load assessment

### 📊 Analytics
- **Metrics** - usage metrics
- **Dashboard** - activity visualization
- **Feedback System** - reinforcement learning from human feedback (RLHF)

### ⚙️ Infrastructure
- **Response Cache** - smart response caching
- **Session Manager** - session management
- **Config Manager** - system configuration
- **Data Manager** - data export/import
- **Event Bus** - event system

## Architecture

The system implements a 9-stage pipeline:
1. **Safety** - security checks
2. **Intent** - intent classification
3. **Retrieve** - context retrieval (RAG, facts, knowledge)
4. **Episodic** - similar past situations
5. **Semantic** - procedural knowledge
6. **Generate** - response generation
7. **Verify** - verification via TruthLoop
8. **Remember** - memory storage
9. **Emit** - events

## Installation

### Requirements
- Python 3.10+
- Node.js 16+
- OpenRouter API key (optional, for LLMs)

### Setup
```bash
# Clone the repository
git clone https://github.com/your-username/neuromind-ai.git
cd neuromind-ai

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Configuration
cp .env.example .env
# Edit .env
```

### Running
```bash
# Windows
start.bat

# Or manually:
# Terminal 1 - Backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend  
cd frontend && npm run dev
```

Open http://localhost:5173

## API Endpoints (80+)

### Main
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/chat` | Chat |
| `POST /api/v1/chat/stream` | Streaming chat (SSE) |
| `GET /api/v1/mind-state` | Full system state |

### Memory
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/rag/stats` | RAG stats |
| `POST /api/v1/rag/search` | Semantic search |
| `POST /api/v1/rag/hybrid` | Hybrid search |
| `GET /api/v1/facts/stats` | Facts stats |
| `POST /api/v1/facts/search` | Facts search |
| `GET /api/v1/roots` | Root knowledge |

### Emotions and Persona
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/emotion/state` | PAD+ emotions |
| `GET /api/v1/persona/traits` | Character traits |
| `POST /api/v1/persona/adjust` | Trait adjustment |

### Autonomy
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/autonomy/status` | Autonomy status |
| `POST /api/v1/autonomy/reflect` | Self-reflection |
| `GET /api/v1/meta/stats` | Meta-cognition |

### Analytics and Health
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/analytics/report` | Analytics |
| `GET /api/v1/health` | Cognitive health |
| `POST /api/v1/feedback` | Feedback |

Full documentation: http://localhost:8000/docs

## Philosophy: ANTI_DIRECTIVE

The philosophical core of the system:
> *"Don't fix knowledge, doubt, verify. Every statement is a hypothesis."*

This immutable core prevents knowledge fixation and maintains a skeptical approach to information.

## Technologies

- **Backend**: Python, FastAPI, SQLite, ChromaDB, NetworkX
- **Frontend**: React, WebSocket
- **ML**: Vector embeddings via ChromaDB
- **Asynchronous**: asyncio for parallel processing

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 - see [LICENSE](LICENSE) file

---

**NeuroMind AI v3.5** - *A cognitive layer adding emotions and self-awareness to any LLM.*