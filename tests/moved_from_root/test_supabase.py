import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from supabase import create_client

# Load .env from repository root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")


def test_supabase_connection():
    if not supabase_url or not supabase_key:
        pytest.skip("SUPABASE_URL or SUPABASE_KEY is missing in .env")

    client = create_client(supabase_url, supabase_key)
    result = client.table("users").select("count").limit(1).execute()

    if isinstance(result, dict):
        error = result.get("error")
    else:
        error = getattr(result, "error", None)

    assert error is None, f"Supabase query failed: {error}"
    assert result is not None
