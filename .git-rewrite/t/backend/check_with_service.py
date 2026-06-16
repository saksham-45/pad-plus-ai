import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / '.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')

print(f'URL: {url}')
print(f'Key starts with: {key[:20]}...' if key else 'No service key')

supabase = create_client(url, key)

result = supabase.table('user_api_keys').select('id, provider, api_key_encrypted').eq('provider', 'gigachat').execute()
if result.data:
    for key in result.data:
        enc = key.get('api_key_encrypted', '')
        print(f'Key ID: {key["id"]}')
        print(f'Encrypted length: {len(enc)}')
        print(f'First 50: {enc[:50]}...')
        print()
else:
    print('No GigaChat keys found')
