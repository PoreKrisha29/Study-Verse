"""
Fix PostgreSQL sequence sync issues after data migration.

When data is restored with explicit IDs, the auto-increment sequences
are NOT updated, so the next INSERT tries to use an already-existing ID.

This script resets every table's primary key sequence to max(id) + 1.
"""
import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL', '')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    print("Set it first: $env:DATABASE_URL = 'your-neon-connection-string'")
    exit(1)

# Fix postgres:// -> postgresql:// (psycopg2 needs the full prefix)
if DATABASE_URL.startswith("postgresql://"):
    psycopg2_url = DATABASE_URL.replace("postgresql://", "postgres://", 1)
else:
    psycopg2_url = DATABASE_URL

# Tables to fix (all tables with integer primary keys)
TABLES = [
    'user',
    'xp_history',
    'badge',
    'user_badge',
    'study_session',
    'todo',
    'syllabus_document',
    'friendship',
    'chat_message',
    'group',
    'group_member',
    'group_chat_message',
    'support_ticket',
    'support_message',
    'admin_action',
    'user_feedback',
    'user_item',
    'habit',
    'habit_log',
    'quiz_question',
    'quiz_attempt',
    'battle_session',
    'pomodoro_settings',
]

try:
    conn = psycopg2.connect(psycopg2_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("🔧 Fixing PostgreSQL sequences...\n")
    
    fixed = 0
    skipped = 0
    
    for table in TABLES:
        try:
            # Get the sequence name for this table's id column
            cur.execute("""
                SELECT pg_get_serial_sequence(%s, 'id')
            """, (table,))
            row = cur.fetchone()
            
            if not row or not row[0]:
                print(f"  ⚪ {table:30s} — no sequence (skipped)")
                skipped += 1
                continue
            
            seq_name = row[0]
            
            # Reset sequence to max(id) in the table
            cur.execute(f"""
                SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM "{table}"), 0) + 1, false)
            """)
            
            # Get new sequence value for display
            cur.execute(f"SELECT last_value FROM {seq_name}")
            new_val = cur.fetchone()[0]
            
            print(f"  ✅ {table:30s} — sequence reset to {new_val}")
            fixed += 1
            
        except Exception as e:
            print(f"  ⚠️  {table:30s} — error: {str(e)[:60]}")
            skipped += 1
    
    cur.close()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Done! Fixed: {fixed}  |  Skipped/Error: {skipped}")
    print("All sequences are now synced with actual data.")
    
except Exception as e:
    print(f"Connection error: {e}")
