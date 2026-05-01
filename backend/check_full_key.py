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

result = supabase.table('user_api_keys').select('*').eq('id', '52435c07-48d3-4d05-931b-0a464238d92c').execute()
if result.data:
    key = result.data[0]
    decrypted = encryptor.decrypt(key['api_key_encrypted'])
    print(f'FULL KEY: [{decrypted}]')
    print(f'LENGTH: {len(decrypted)}')
    print(f'Has colon: {":" in decrypted}')
else:
    print('Key not found')
