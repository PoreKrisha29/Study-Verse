from app import app, db
from sqlalchemy import text

def create_tables():
    """Create support tables via direct SQL execution for robustness"""
    with app.app_context():
        print("Creating support system tables...")
        try:
            # Check db type
            db_type = db.engine.dialect.name
            connection = db.engine.connect()
            
            if db_type == 'postgresql':
                print("Using PostgreSQL syntax...")
                # Support Ticket Table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS support_ticket (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES "user"(id),
                        subject VARCHAR(200) NOT NULL,
                        category VARCHAR(50) DEFAULT 'general',
                        status VARCHAR(20) DEFAULT 'open',
                        priority VARCHAR(20) DEFAULT 'normal',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP,
                        user_unread_count INTEGER DEFAULT 0,
                        admin_unread_count INTEGER DEFAULT 1
                    );
                """))
                print("✓ support_ticket table created/verified")
                
                # Support Message Table
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS support_message (
                        id SERIAL PRIMARY KEY,
                        ticket_id INTEGER NOT NULL REFERENCES support_ticket(id),
                        sender_id INTEGER NOT NULL REFERENCES "user"(id),
                        message TEXT NOT NULL,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        read_by_user BOOLEAN DEFAULT FALSE,
                        read_by_admin BOOLEAN DEFAULT FALSE
                    );
                """))
                print("✓ support_message table created/verified")
                
            else:
                # SQLite syntax
                print("Using SQLite syntax...")
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS support_ticket (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        subject VARCHAR(200) NOT NULL,
                        category VARCHAR(50) DEFAULT 'general',
                        status VARCHAR(20) DEFAULT 'open',
                        priority VARCHAR(20) DEFAULT 'normal',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        closed_at DATETIME,
                        user_unread_count INTEGER DEFAULT 0,
                        admin_unread_count INTEGER DEFAULT 1,
                        FOREIGN KEY(user_id) REFERENCES user(id)
                    );
                """))
                print("✓ support_ticket table created/verified")
                
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS support_message (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket_id INTEGER NOT NULL,
                        sender_id INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        is_admin BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        read_by_user BOOLEAN DEFAULT FALSE,
                        read_by_admin BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY(ticket_id) REFERENCES support_ticket(id),
                        FOREIGN KEY(sender_id) REFERENCES user(id)
                    );
                """))
                print("✓ support_message table created/verified")
            
            connection.commit()
            connection.close()
            print("\n✅ Support tables created successfully!")
            
        except Exception as e:
            print(f"\n❌ Error creating tables: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_tables()
