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

result = supabase.table('user_api_keys').select('id, provider, model_preference, api_key_encrypted').eq('provider', 'gigachat').execute()
if result.data:
    for k in result.data:
        enc = k['api_key_encrypted']
        print(f'Key ID: {k["id"]}')
        print(f'Model: {k.get("model_preference")}')
        print(f'Encrypted length: {len(enc)}')
        try:
            decrypted = encryptor.decrypt(enc)
            print(f'Decrypted length: {len(decrypted)}')
            print(f'Decrypted: {decrypted[:50]}...')
        except Exception as e:
            print(f'Decrypt error: {e}')
        print()
else:
    print('No GigaChat keys found')
