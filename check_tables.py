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

if not supabase_url or not supabase_key:
    print("❌ Missing SUPABASE_URL or SUPABASE_KEY in .env")
else:
    try:
        # Test connection
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Check if user_api_keys table exists
        try:
            result = client.table("user_api_keys").select("count").limit(1).execute()
            print(f"✅ user_api_keys table exists: {result}")
        except Exception as e:
            print(f"❌ user_api_keys table does not exist: {e}")
            
        # List all tables
        try:
            # This is a workaround to list tables - we'll try to get schema info
            from supabase import Client
            # Use raw SQL query to get tables
            response = client.rpc("get_all_tables").execute()
            print(f"All tables: {response}")
        except Exception as e:
            print(f"Could not list tables: {e}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
