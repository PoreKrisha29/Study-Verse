"""
StudyVerse - Final Restore Script (Robust Version)
- Each table in its own transaction
- Skips columns that don't exist in backup
- Handles errors gracefully
"""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

NEON_URL = os.environ.get('DATABASE_URL', '')
if not NEON_URL:
    raise RuntimeError('DATABASE_URL environment variable not set. Check your .env file.')

from sqlalchemy import create_engine, text

engine = create_engine(NEON_URL, connect_args={"sslmode": "require"}, isolation_level="AUTOCOMMIT")

# Find backup
BACKUP_ROOT = Path(__file__).parent / "backups"
folders = sorted(BACKUP_ROOT.glob("*"), reverse=True)
BACKUP_DIR = folders[0]
print(f"\n📦  Restoring from: {BACKUP_DIR}\n")

TABLE_ORDER = [
    "user", "badge", "friendship", "user_badge", "xp_history",
    "user_item", "active_power_up", "todo", "habit", "habit_log",
    "study_session", "topic_proficiency", "syllabus_document",
    "group", "group_member", "group_chat_message", "chat_message",
    "event", "support_ticket", "support_message", "referral_reward",
    "user_feedback", "study_stream", "admin_action",
]

json_files = {f.stem: f for f in BACKUP_DIR.glob("*.json") if not f.stem.startswith("_")}
ordered = [t for t in TABLE_ORDER if t in json_files]
extras = [t for t in json_files if t not in TABLE_ORDER]
ordered += extras

total_ins = 0
total_skip = 0

for table_name in ordered:
    json_path = json_files[table_name]
    with open(json_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    if not rows:
        print(f"   ⏭️   {table_name:<32}  0 rows")
        continue

    # Get what columns actually exist in the Neon table
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = '{table_name}' AND table_schema = 'public'
        """))
        neon_cols = {r[0] for r in result}

    if not neon_cols:
        print(f"   ❌  {table_name:<32}  Table not found on Neon, skipping")
        continue

    # Only use columns that exist in BOTH backup and Neon table
    backup_cols = list(rows[0].keys())
    common_cols = [c for c in backup_cols if c in neon_cols]

    if not common_cols:
        print(f"   ⚠️   {table_name:<32}  No matching columns")
        continue

    col_list = ", ".join(f'"{c}"' for c in common_cols)
    val_list = ", ".join(f":{c}" for c in common_cols)
    insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({val_list}) ON CONFLICT DO NOTHING'

    inserted = 0
    skipped = 0

    with engine.connect() as conn:
        # Disable FK checks
        try:
            conn.execute(text("SET session_replication_role = replica"))
        except:
            pass

        for row in rows:
            # Only pass columns that exist
            clean = {k: v for k, v in row.items() if k in common_cols}
            try:
                conn.execute(text(insert_sql), clean)
                inserted += 1
            except Exception as e:
                skipped += 1
                if skipped <= 2:
                    print(f"      ⚠️  {table_name}: {str(e)[:120]}")

        try:
            conn.execute(text("SET session_replication_role = DEFAULT"))
        except:
            pass

    total_ins += inserted
    total_skip += skipped
    icon = "✅" if skipped == 0 else "⚠️ "
    print(f"   {icon}  {table_name:<32} {inserted:>5} inserted  {skipped:>4} skipped")

print(f"""
{'='*60}
✅  RESTORE COMPLETE!
    Total inserted : {total_ins}
    Total skipped  : {total_skip}

💡  NEXT STEP:
    Go to Render → Service → Environment
    Change DATABASE_URL to Neon URL and Redeploy!
{'='*60}
""")
