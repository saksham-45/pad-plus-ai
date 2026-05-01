import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
from core.supabase_client import get_supabase

supabase = get_supabase()

result = supabase.table('user_api_keys').select('id, provider, api_key_encrypted').eq('id', '52435c07-48d3-4d05-931b-0a464238d92c').execute()
if result.data:
    key = result.data[0]
    enc = key.get('api_key_encrypted', '')
    print(f'Encrypted key length from DB: {len(enc)}')
    print(f'Encrypted key (first 50): {enc[:50]}...')
else:
    print('Key not found')
