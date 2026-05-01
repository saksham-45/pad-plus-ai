import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')

print('=== Emotion ===', flush=True)
try:
    from emotion.pad_model import get_pad_model
    pad = get_pad_model()
    print(f'OK: {pad.get_state().to_dict()}', flush=True)
except Exception as e:
    print(f'ERROR: {e}', flush=True)

print('=== RAG ===', flush=True)
try:
    from memory.rag import get_rag
    rag = get_rag()
    print(f'OK: {rag.get_stats()}', flush=True)
except Exception as e:
    print(f'ERROR: {e}', flush=True)

print('=== Knowledge ===', flush=True)
try:
    from knowledge.graph import get_knowledge_graph
    g = get_knowledge_graph()
    print(f'OK: {g.get_stats()}', flush=True)
except Exception as e:
    print(f'ERROR: {e}', flush=True)

print('=== Pipeline ===', flush=True)
try:
    from core.pipeline import get_pipeline
    p = get_pipeline()
    print(f'OK: {p.get_stats()}', flush=True)
except Exception as e:
    print(f'ERROR: {e}', flush=True)
