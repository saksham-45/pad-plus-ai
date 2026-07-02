import shutil
import os

files_to_move = [
    'DIAGNOSTIC_INSTRUCTIONS.md',
    'FINAL_MIGRATION.md',
    'FIX_RENDER_DB.md',
    'FIX_RENDER_ISSUE.md',
    'MIGRATE_TO_NEW_DB.md',
    'PLAN.md',
    'PRODUCTION_AUDIT_REPORT.md',
    'RENDER_QUICK_CHECK.md',
    'TODO_MCP_RENDER_SETUP.md',
    'README - копия.md',
    'diagnostic_production.log',
    'exported_episodes.json',
    'index.json',
    'PAD_AI_README_COPY.txt',
    'train_result.json',
    'Новый текстовый документ.txt'
]

dst = 'docs/archive/legacy/'

for f in files_to_move:
    if os.path.exists(f):
        shutil.move(f, dst)
        print(f"Moved: {f}")
    else:
        print(f"Not found: {f}")

print("Done!")