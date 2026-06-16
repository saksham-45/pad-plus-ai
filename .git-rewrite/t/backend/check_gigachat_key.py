import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
from core.encryption import get_encryptor
from core.supabase_client import get_supabase

supabase = get_supabase()
encryptor = get_encryptor()

result = supabase.table('user_api_keys').select('*').eq('provider', 'gigachat').execute()
if result.data:
    for key in result.data:
        decrypted = encryptor.decrypt(key['api_key_encrypted'])
        print(f'Key ID: {key["id"]}')
        print(f'Provider: {key["provider"]}')
        print(f'Model: {key.get("model_preference")}')
        print(f'Decrypted key (first 30): {decrypted[:30]}...')
        print(f'Key length: {len(decrypted)}')
        print()
else:
    print('No GigaChat keys found in DB')
