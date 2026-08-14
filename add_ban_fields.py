"""
Database Migration: Add Ban Fields to User Table
This script uses Flask-SQLAlchemy to add ban fields to the user table.
"""

from app import app, db
from sqlalchemy import text

def migrate():
    """Add ban fields to user table"""
    with app.app_context():
        try:
            # Get database connection
            connection = db.engine.connect()
            
            # Check database type
            db_type = db.engine.dialect.name
            print(f"Database type: {db_type}")
            
            if db_type == 'postgresql':
                # PostgreSQL syntax
                try:
                    connection.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE"))
                    print("✓ is_banned column added/verified")
                except Exception as e:
                    print(f"is_banned: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS ban_reason TEXT"))
                    print("✓ ban_reason column added/verified")
                except Exception as e:
                    print(f"ban_reason: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP"))
                    print("✓ banned_at column added/verified")
                except Exception as e:
                    print(f"banned_at: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS banned_by INTEGER"))
                    print("✓ banned_by column added/verified")
                except Exception as e:
                    print(f"banned_by: {e}")
                
            else:
                # SQLite syntax
                try:
                    connection.execute(text("ALTER TABLE user ADD COLUMN is_banned BOOLEAN DEFAULT 0"))
                    print("✓ is_banned column added")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print("✓ is_banned column already exists")
                    else:
                        print(f"is_banned error: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE user ADD COLUMN ban_reason TEXT"))
                    print("✓ ban_reason column added")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print("✓ ban_reason column already exists")
                    else:
                        print(f"ban_reason error: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE user ADD COLUMN banned_at DATETIME"))
                    print("✓ banned_at column added")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print("✓ banned_at column already exists")
                    else:
                        print(f"banned_at error: {e}")
                
                try:
                    connection.execute(text("ALTER TABLE user ADD COLUMN banned_by INTEGER"))
                    print("✓ banned_by column added")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print("✓ banned_by column already exists")
                    else:
                        print(f"banned_by error: {e}")
            
            connection.commit()
            connection.close()
            
            print("\n✅ Migration completed successfully!")
            print("Ban system is now active.")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("STUDYVERSE - BAN SYSTEM MIGRATION")
    print("=" * 60)
    print("\nThis will add ban-related fields to the user table.")
    print("Fields to be added:")
    print("  - is_banned (BOOLEAN)")
    print("  - ban_reason (TEXT)")
    print("  - banned_at (DATETIME)")
    print("  - banned_by (INTEGER)")
    print("\n" + "=" * 60 + "\n")
    
    migrate()
