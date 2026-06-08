# Apply migration 009 - fix dialog stats trigger
import os, sys, psycopg2

# Load .env (handle encoding issues)
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "rb") as f:
        raw = f.read()
    for line in raw.decode("utf-8", errors="replace").split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("err: DATABASE_URL not found")
    sys.exit(1)

mp = os.path.join(os.path.dirname(__file__), "..", "backend", "database", "migrations", "009_fix_dialog_stats_trigger.sql")
with open(mp) as f:
    sql = f.read()

print("Applying migration...")
conn = psycopg2.connect(db_url, connect_timeout=5)
conn.autocommit = True
conn.cursor().execute(sql)
conn.close()
print("Migration 009 applied")

