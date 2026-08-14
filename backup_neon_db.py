"""
StudyVerse - Neon Database Backup Script
=========================================
Run this script locally to back up ALL data from your Neon (PostgreSQL) database.
It exports every table to:
  1. JSON files (easy to inspect / re-import)
  2. A single SQL dump file (full restore)

Usage:
  1. Set DATABASE_URL in your .env file (copy from Render env vars)
  2. Run: python backup_neon_db.py

Output folder: ./backups/YYYY-MM-DD_HH-MM-SS/
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env so DATABASE_URL is available ────────────────────────────────────
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    print("❌  DATABASE_URL not found in environment / .env file.")
    print("    Copy your Neon connection string from Render → Environment Variables,")
    print("    paste it into your .env file as:  DATABASE_URL=postgresql://...")
    sys.exit(1)

# Fix old postgres:// prefix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Prepare output folder ─────────────────────────────────────────────────────
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
BACKUP_DIR = Path(__file__).parent / "backups" / timestamp
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

print(f"\n📦  StudyVerse Database Backup")
print(f"    Target folder : {BACKUP_DIR}")
print(f"    Timestamp     : {timestamp}\n")

# ── All tables in the correct restore order (parents before children) ─────────
TABLES = [
    "user",
    "badge",
    "friendship",
    "user_badge",
    "xp_history",
    "user_item",
    "active_power_up",
    "todo",
    "habit",
    "habit_log",
    "study_session",
    "topic_proficiency",
    "syllabus_document",
    "group",
    "group_member",
    "group_chat_message",
    "chat_message",
    "event",
    # Extra tables that may exist (added later)
    "support_ticket",
    "support_message",
    "referral",
    "notification",
    "coin_transaction",
    "battle",
    "battle_participant",
    "quiz_question",
]

# ── Method 1 : Python / SQLAlchemy JSON export ────────────────────────────────
def export_json():
    """Export every table to a separate JSON file via SQLAlchemy."""
    try:
        from sqlalchemy import create_engine, text, inspect
    except ImportError:
        print("⚠️   SQLAlchemy not installed – skipping JSON export.")
        return

    print("📄  Exporting tables to JSON …")
    engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})

    with engine.connect() as conn:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        summary = {}
        for table in existing_tables:
            try:
                result = conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = [dict(row._mapping) for row in result]

                # Serialise: convert non-JSON-serialisable types
                def serialise(obj):
                    if isinstance(obj, (datetime,)):
                        return obj.isoformat()
                    if hasattr(obj, '__str__'):
                        return str(obj)
                    return repr(obj)

                json_path = BACKUP_DIR / f"{table}.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=2, default=serialise)

                summary[table] = len(rows)
                print(f"   ✅  {table:<30}  {len(rows):>6} rows   →  {table}.json")

            except Exception as e:
                print(f"   ⚠️   {table}: {e}")

    # Write summary
    summary_path = BACKUP_DIR / "_summary.json"
    with open(summary_path, "w") as f:
        json.dump({"timestamp": timestamp, "tables": summary}, f, indent=2)

    total = sum(summary.values())
    print(f"\n   📊  Total rows backed up: {total}")
    print(f"   📝  Summary saved to: _summary.json\n")


# ── Method 2 : pg_dump SQL dump (full restore capability) ────────────────────
def export_sql_dump():
    """
    Run pg_dump to create a full SQL dump file.
    Requires pg_dump to be installed (comes with PostgreSQL).
    On Windows: install PostgreSQL or use the portable binaries.
    """
    dump_path = BACKUP_DIR / "studyverse_full_dump.sql"

    # pg_dump expects a plain PostgreSQL URL
    try:
        print("🗄️   Running pg_dump (full SQL dump) …")
        result = subprocess.run(
            ["pg_dump", "--no-password", "--clean", "--if-exists",
             "--format=plain", "--encoding=UTF8", DATABASE_URL,
             f"--file={dump_path}"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            size_kb = dump_path.stat().st_size // 1024
            print(f"   ✅  SQL dump saved → studyverse_full_dump.sql  ({size_kb} KB)\n")
        else:
            print(f"   ❌  pg_dump failed: {result.stderr.strip()}")
            print(f"   💡  Install PostgreSQL to get pg_dump, or use only JSON backup.\n")
    except FileNotFoundError:
        print("   ⚠️   pg_dump not found – skipping SQL dump.")
        print("   💡  Install PostgreSQL client tools to enable this feature.\n")
    except subprocess.TimeoutExpired:
        print("   ❌  pg_dump timed out after 120 seconds.\n")


# ── Method 3 : Write a restore script ────────────────────────────────────────
def write_restore_guide():
    guide = """# StudyVerse Database Restore Guide
Generated: {ts}

## Option A — Restore from SQL dump (recommended)
```
psql YOUR_NEW_DATABASE_URL < studyverse_full_dump.sql
```

## Option B — Restore from JSON files (manual / selective)
Run the companion script:
```
python restore_from_json.py --backup-dir ./backups/{ts}
```

## Steps to migrate to a new Neon project
1. Create a new Neon project at https://neon.tech
2. Copy the new connection string (postgresql://...)
3. Update DATABASE_URL in Render → Environment Variables
4. Run the restore: psql NEW_URL < studyverse_full_dump.sql
5. Redeploy on Render

## Tables backed up
{tables}
""".format(
        ts=timestamp,
        tables="\n".join(f"- {t}" for t in TABLES)
    )
    guide_path = BACKUP_DIR / "RESTORE_GUIDE.md"
    guide_path.write_text(guide, encoding="utf-8")
    print(f"📖  Restore guide saved → RESTORE_GUIDE.md\n")


# ── Run all export methods ────────────────────────────────────────────────────
if __name__ == "__main__":
    export_json()
    export_sql_dump()
    write_restore_guide()

    print("=" * 60)
    print(f"✅  Backup complete!")
    print(f"    Location: {BACKUP_DIR}")
    print(f"\n💡  NEXT STEPS:")
    print(f"    1. Keep this 'backups/' folder safe (copy to Google Drive / USB)")
    print(f"    2. Run this script monthly or before Render DB expires")
    print(f"    3. To restore: see RESTORE_GUIDE.md inside the backup folder")
    print("=" * 60)
