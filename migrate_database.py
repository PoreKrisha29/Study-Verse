"""
Database Migration Script
=========================
This script adds the new admin panel columns to existing database.

Run this ONCE to update your database schema.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate_database():
    """Add new columns to existing database"""
    
    with app.app_context():
        print("🔧 Migrating database for admin panel...")
        
        try:
            # Add columns to User table
            print("\n📊 Adding columns to User table...")
            
            with db.engine.connect() as conn:
                # Add admin fields
                try:
                    conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                    print("  ✅ Added is_admin column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  is_admin column already exists")
                    else:
                        print(f"  ❌ Error adding is_admin: {e}")
                
                # Add ban fields
                try:
                    conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN is_banned BOOLEAN DEFAULT FALSE"))
                    print("  ✅ Added is_banned column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  is_banned column already exists")
                    else:
                        print(f"  ❌ Error adding is_banned: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN ban_reason TEXT"))
                    print("  ✅ Added ban_reason column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  ban_reason column already exists")
                    else:
                        print(f"  ❌ Error adding ban_reason: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN banned_at TIMESTAMP"))
                    print("  ✅ Added banned_at column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  banned_at column already exists")
                    else:
                        print(f"  ❌ Error adding banned_at: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN banned_by INTEGER REFERENCES \"user\"(id)"))
                    print("  ✅ Added banned_by column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  banned_by column already exists")
                    else:
                        print(f"  ❌ Error adding banned_by: {e}")
                
                conn.commit()
            
            # Add columns to SyllabusDocument table
            print("\n📄 Adding columns to SyllabusDocument table...")
            
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN file_path VARCHAR(255)"))
                    print("  ✅ Added file_path column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  file_path column already exists")
                    else:
                        print(f"  ❌ Error adding file_path: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN file_size INTEGER"))
                    print("  ✅ Added file_size column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  file_size column already exists")
                    else:
                        print(f"  ❌ Error adding file_size: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN extraction_status VARCHAR(20) DEFAULT 'pending'"))
                    print("  ✅ Added extraction_status column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  extraction_status column already exists")
                    else:
                        print(f"  ❌ Error adding extraction_status: {e}")
                
                try:
                    conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                    print("  ✅ Added is_active column")
                except Exception as e:
                    if "already exists" in str(e):
                        print("  ⚠️  is_active column already exists")
                    else:
                        print(f"  ❌ Error adding is_active: {e}")
                
                conn.commit()
            
            # Create AdminAction table
            print("\n🔐 Creating AdminAction table...")
            try:
                db.create_all()
                print("  ✅ AdminAction table created")
            except Exception as e:
                print(f"  ⚠️  AdminAction table may already exist: {e}")
            
            print("\n" + "="*60)
            print("✅ Database migration complete!")
            print("="*60)
            print("\nNext step: Run setup_admin.py to create admin account")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_database()
