import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print(f"SUPABASE_URL: {supabase_url}")
print(f"SUPABASE_KEY: {supabase_key[:20]}...")

if not supabase_url or not supabase_key:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")
else:
    try:
        # Test connection
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Test a simple query
        result = client.table("users").select("count").limit(1).execute()
        print(f"✅ Users table query successful: {result}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Try adding SSL configuration if needed")
