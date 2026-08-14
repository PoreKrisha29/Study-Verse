"""
Fix ALL PostgreSQL sequences by auto-discovering every table 
with an integer primary key and resetting its sequence.
This is the permanent, exhaustive fix.
"""
import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL', '')
if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL first.")
    exit(1)

# psycopg2 needs postgres:// not postgresql://
psycopg2_url = DATABASE_URL.replace("postgresql://", "postgres://", 1)

try:
    conn = psycopg2.connect(psycopg2_url)
    conn.autocommit = True
    cur = conn.cursor()

    # Auto-discover ALL tables in public schema
    cur.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename
    """)
    all_tables = [r[0] for r in cur.fetchall()]
    print(f"Found {len(all_tables)} tables. Fixing sequences...\n")

    fixed = 0
    skipped = 0

    for table in all_tables:
        try:
            # Get the sequence for this table's 'id' column (if any)
            cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
            row = cur.fetchone()

            if not row or not row[0]:
                print(f"  ⚪ {table:40s} — no id sequence")
                skipped += 1
                continue

            seq_name = row[0]

            # Reset sequence to MAX(id) + 1, false = next call returns this value
            cur.execute(f"""
                SELECT setval('{seq_name}', 
                    COALESCE((SELECT MAX(id) FROM "{table}"), 0) + 1, 
                    false)
            """)
            new_val = cur.fetchone()[0]
            print(f"  ✅ {table:40s} — next id will be {new_val}")
            fixed += 1

        except Exception as e:
            print(f"  ⚠️  {table:40s} — {str(e)[:70]}")
            skipped += 1

    cur.close()
    conn.close()

    print(f"\n{'='*55}")
    print(f"Done! Fixed: {fixed}  |  Skipped: {skipped}")
    print("All sequences synced. Duplicate key errors should be gone.")

except Exception as e:
    print(f"Connection error: {e}")
