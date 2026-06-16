import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
val = os.getenv('GIGACHAT_AUTH_KEY')
print(f'GIGACHAT_AUTH_KEY: {val[:30] if val else "NOT SET"}...')
print(f'Length: {len(val) if val else 0}')
