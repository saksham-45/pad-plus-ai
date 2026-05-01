import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
from core.encryption import get_encryptor
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)
encryptor = get_encryptor()

# Проверяем последний сохранённый ключ GigaChat
result = supabase.table('user_api_keys').select('id, provider, model_preference, api_key_encrypted').eq('provider', 'gigachat').order('created_at', desc=True).limit(1).execute()
if result.data:
    k = result.data[0]
    enc = k['api_key_encrypted']
    print(f'Key ID: {k["id"]}')
    print(f'Model: {k.get("model_preference")}')
    print(f'Encrypted length in DB: {len(enc)}')
    try:
        decrypted = encryptor.decrypt(enc)
        print(f'Decrypted length: {len(decrypted)}')
        print(f'Decrypted: {decrypted}')
    except Exception as e:
        print(f'Decrypt error: {e}')
else:
    print('No GigaChat keys found')
