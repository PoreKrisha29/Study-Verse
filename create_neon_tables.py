"""
Create all StudyVerse tables on Neon - NO Flask/eventlet import
Just SQLAlchemy + raw DDL
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

NEON_URL = os.environ.get('DATABASE_URL', '')
if not NEON_URL:
    raise RuntimeError('DATABASE_URL environment variable not set. Check your .env file.')

engine = create_engine(NEON_URL, connect_args={"sslmode": "require"})

DDL = """
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    google_id VARCHAR(100) UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    profile_image VARCHAR(255),
    cover_image VARCHAR(255),
    about_me TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    total_xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    is_public_profile BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMP DEFAULT NOW(),
    is_admin BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,
    banned_at TIMESTAMP,
    banned_by INTEGER REFERENCES "user"(id),
    referral_code VARCHAR(20) UNIQUE,
    referred_by INTEGER REFERENCES "user"(id),
    coins INTEGER DEFAULT 0,
    otp_code VARCHAR(10),
    otp_expires_at TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS badge (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    icon VARCHAR(50) DEFAULT 'fa-medal',
    criteria_type VARCHAR(50),
    criteria_value INTEGER
);

CREATE TABLE IF NOT EXISTS support_ticket (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    subject VARCHAR(200) NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    status VARCHAR(20) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    user_unread_count INTEGER DEFAULT 0,
    admin_unread_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS support_message (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES support_ticket(id),
    sender_id INTEGER NOT NULL REFERENCES "user"(id),
    message TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    read_by_user BOOLEAN DEFAULT FALSE,
    read_by_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS friendship (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    friend_id INTEGER NOT NULL REFERENCES "user"(id),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS study_stream (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    topic VARCHAR(200) DEFAULT 'Studying',
    subject VARCHAR(100) DEFAULT 'General',
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    duration_min INTEGER DEFAULT 0,
    peak_watchers INTEGER DEFAULT 0,
    solidarity_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'live',
    timer_minutes INTEGER DEFAULT 25
);

CREATE TABLE IF NOT EXISTS user_badge (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    badge_id INTEGER NOT NULL REFERENCES badge(id),
    earned_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS xp_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    source VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS todo (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    text VARCHAR(500) NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    due_date TIMESTAMP,
    priority VARCHAR(20) DEFAULT 'medium',
    subject VARCHAR(100),
    xp_awarded BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS habit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    name VARCHAR(200) NOT NULL,
    frequency VARCHAR(20) DEFAULT 'daily',
    created_at TIMESTAMP DEFAULT NOW(),
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS habit_log (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habit(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    completed_at TIMESTAMP DEFAULT NOW(),
    date DATE
);

CREATE TABLE IF NOT EXISTS study_session (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    duration_minutes INTEGER NOT NULL,
    subject VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    xp_awarded INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topic_proficiency (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    topic VARCHAR(200) NOT NULL,
    score FLOAT DEFAULT 0.0,
    questions_attempted INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS syllabus_document (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    filename VARCHAR(255),
    original_filename VARCHAR(255),
    subject VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    file_path VARCHAR(500),
    processed BOOLEAN DEFAULT FALSE,
    content_summary TEXT
);

CREATE TABLE IF NOT EXISTS "group" (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT NOW(),
    max_members INTEGER DEFAULT 50,
    is_private BOOLEAN DEFAULT FALSE,
    invite_code VARCHAR(20) UNIQUE
);

CREATE TABLE IF NOT EXISTS group_member (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES "group"(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS group_chat_message (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES "group"(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    message TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS chat_message (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES "user"(id),
    receiver_id INTEGER NOT NULL REFERENCES "user"(id),
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS event (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP,
    event_type VARCHAR(50) DEFAULT 'study',
    color VARCHAR(20) DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT NOW(),
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id),
    feedback_text TEXT NOT NULL,
    rating INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    category VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS referral_reward (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER NOT NULL REFERENCES "user"(id),
    referred_id INTEGER NOT NULL REFERENCES "user"(id),
    coins_awarded INTEGER DEFAULT 0,
    xp_awarded INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_item (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    item_id VARCHAR(100) NOT NULL,
    purchased_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS active_power_up (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    power_up_id VARCHAR(100) NOT NULL,
    activated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS admin_action (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES "user"(id),
    action_type VARCHAR(100),
    target_user_id INTEGER REFERENCES "user"(id),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

print("🏗️  Creating tables on Neon...")
try:
    with engine.connect() as conn:
        for stmt in DDL.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    print("✅  All tables created successfully on Neon!")
    
    # Verify
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        tables = [r[0] for r in result]
        print(f"\n📋  Tables on Neon ({len(tables)}):")
        for t in tables:
            print(f"    ✓ {t}")
except Exception as e:
    print(f"❌  Error: {e}")
    sys.exit(1)
