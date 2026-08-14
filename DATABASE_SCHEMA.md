# StudyVerse Database Schema Documentation
## Complete ER Diagram Reference

---

## 📊 **TABLE OVERVIEW**

The StudyVerse database consists of **18 main tables** organized into the following categories:

1. **User Management** (2 tables)
2. **Gamification System** (5 tables)
3. **Task Management** (3 tables)
4. **Study & Progress Tracking** (3 tables)
5. **Social Features** (4 tables)
6. **Shop & Inventory** (2 tables)
7. **Events & Calendar** (1 table)

---

## 🗂️ **DETAILED TABLE SCHEMAS**

### **1. USER MANAGEMENT**

#### **Table: `user`**
**Purpose:** Core user account and profile information

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique user identifier |
| `email` | VARCHAR(120) | UNIQUE, NOT NULL, INDEXED | User email (login credential) |
| `password_hash` | VARCHAR(255) | NULLABLE | Encrypted password (NULL for OAuth users) |
| `google_id` | VARCHAR(100) | UNIQUE, NULLABLE | Google OAuth identifier |
| `first_name` | VARCHAR(50) | | User's first name |
| `last_name` | VARCHAR(50) | | User's last name |
| `profile_image` | VARCHAR(255) | NULLABLE | Avatar URL or path |
| `cover_image` | VARCHAR(255) | NULLABLE | Profile banner image path |
| `about_me` | TEXT | NULLABLE | User bio/description |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Account creation date |
| `total_xp` | INTEGER | DEFAULT 0 | Total experience points earned |
| `level` | INTEGER | DEFAULT 1 | User level (calculated from XP) |
| `current_streak` | INTEGER | DEFAULT 0 | Current daily activity streak |
| `longest_streak` | INTEGER | DEFAULT 0 | Best streak record |
| `last_activity_date` | DATE | NULLABLE | Last activity date for streak tracking |
| `is_public_profile` | BOOLEAN | DEFAULT TRUE | Profile visibility setting |
| `last_seen` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Last activity timestamp |

**Relationships:**
- One-to-Many with `Todo`, `ChatMessage`, `StudySession`, `TopicProficiency`, `Event`, `UserBadge`, `UserItem`, `ActivePowerUp`, `SyllabusDocument`, `Habit`
- Many-to-Many with `User` (via `Friendship`)
- Many-to-Many with `Group` (via `GroupMember`)

**Cardinality:**
- User → Todos: **1:N** (One user has many todos)
- User → Badges: **M:N** (Many-to-many via UserBadge)
- User → Friends: **M:N** (Many-to-many via Friendship)

---

#### **Table: `friendship`**
**Purpose:** Manages friend connections and requests between users

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique friendship record ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Friend request sender |
| `friend_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Friend request receiver |
| `status` | VARCHAR(20) | DEFAULT 'pending' | Status: pending/accepted/rejected |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Request timestamp |

**Relationships:**
- Many-to-One with `User` (user_id)
- Many-to-One with `User` (friend_id)

**Cardinality:**
- User → Friendships (sent): **1:N**
- User → Friendships (received): **1:N**

---

### **2. GAMIFICATION SYSTEM**

#### **Table: `badge`**
**Purpose:** Defines available achievement badges

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique badge ID |
| `name` | VARCHAR(100) | NOT NULL | Badge name (e.g., "Consistency King") |
| `description` | VARCHAR(255) | NOT NULL | Badge description |
| `icon` | VARCHAR(50) | DEFAULT 'fa-medal' | FontAwesome icon class |
| `criteria_type` | VARCHAR(50) | | Type: 'streak', 'level', 'wins' |
| `criteria_value` | INTEGER | | Threshold value for earning |

**Relationships:**
- Many-to-Many with `User` (via `UserBadge`)

**Cardinality:**
- Badge → Users: **M:N** (Many users can earn the same badge)

---

#### **Table: `user_badge`**
**Purpose:** Junction table tracking which badges users have earned

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique record ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | User who earned badge |
| `badge_id` | INTEGER | FOREIGN KEY → badge.id, NOT NULL | Badge earned |
| `earned_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When badge was earned |

**Relationships:**
- Many-to-One with `User`
- Many-to-One with `Badge`

**Cardinality:**
- User → UserBadges: **1:N**
- Badge → UserBadges: **1:N**

---

#### **Table: `xp_history`**
**Purpose:** Log of all XP transactions for analytics and debugging

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique transaction ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | User who earned/lost XP |
| `source` | VARCHAR(50) | NOT NULL | Source: 'battle', 'task', 'focus', 'quiz' |
| `amount` | INTEGER | NOT NULL | XP amount (can be negative) |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Transaction timestamp |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → XP History: **1:N**

---

#### **Table: `user_item`**
**Purpose:** Tracks purchased cosmetic items (themes, frames)

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique record ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Item owner |
| `item_id` | VARCHAR(50) | NOT NULL | Item identifier (e.g., 'theme_cyberpunk') |
| `purchased_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Purchase timestamp |
| `is_active` | BOOLEAN | DEFAULT FALSE | Whether item is currently equipped |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → UserItems: **1:N**

---

#### **Table: `active_power_up`**
**Purpose:** Tracks active power-ups with duration and effects

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique record ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Power-up owner |
| `power_up_id` | VARCHAR(50) | NOT NULL | Power-up type (e.g., 'xp_boost') |
| `activated_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Activation timestamp |
| `expires_at` | DATETIME | NULLABLE | Expiration time (NULL for instant) |
| `multiplier` | FLOAT | DEFAULT 1.0 | XP/time multiplier value |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether power-up is currently active |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → ActivePowerUps: **1:N**

---

### **3. TASK MANAGEMENT**

#### **Table: `todo`**
**Purpose:** User tasks and subtasks with priorities and categories

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique task ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Task owner |
| `title` | VARCHAR(200) | NOT NULL | Task title/description |
| `completed` | BOOLEAN | DEFAULT FALSE | Completion status |
| `priority` | VARCHAR(20) | DEFAULT 'medium' | Priority: low/medium/high |
| `due_date` | VARCHAR(50) | | Due date (YYYY-MM-DD format) |
| `due_time` | VARCHAR(20) | NULLABLE | Due time (HH:MM format) |
| `is_notified` | BOOLEAN | DEFAULT FALSE | Notification sent flag |
| `category` | VARCHAR(50) | | Task category/chapter |
| `is_group` | BOOLEAN | DEFAULT FALSE | Whether task is group-related |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `completed_at` | DATETIME | NULLABLE | Completion timestamp |
| `syllabus_id` | INTEGER | FOREIGN KEY → syllabus_document.id, NULLABLE | Linked syllabus |

**Relationships:**
- Many-to-One with `User`
- Many-to-One with `SyllabusDocument`

**Cardinality:**
- User → Todos: **1:N**
- SyllabusDocument → Todos: **1:N**

---

#### **Table: `habit`**
**Purpose:** User-defined habits to track

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique habit ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Habit owner |
| `title` | VARCHAR(100) | NOT NULL | Habit name |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Relationships:**
- Many-to-One with `User`
- One-to-Many with `HabitLog`

**Cardinality:**
- User → Habits: **1:N**
- Habit → HabitLogs: **1:N**

---

#### **Table: `habit_log`**
**Purpose:** Daily completion logs for habits

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique log ID |
| `habit_id` | INTEGER | FOREIGN KEY → habit.id, NOT NULL | Associated habit |
| `completed_date` | DATE | NOT NULL | Date habit was completed |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Log timestamp |

**Relationships:**
- Many-to-One with `Habit`

**Cardinality:**
- Habit → HabitLogs: **1:N**

---

### **4. STUDY & PROGRESS TRACKING**

#### **Table: `study_session`**
**Purpose:** Pomodoro timer sessions and focus time tracking

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique session ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Session owner |
| `duration` | INTEGER | NOT NULL | Duration in minutes |
| `mode` | VARCHAR(20) | DEFAULT 'focus' | Mode: focus/shortBreak/longBreak |
| `completed_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Session completion time |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → StudySessions: **1:N**

---

#### **Table: `topic_proficiency`**
**Purpose:** User's proficiency/confidence level per topic

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique record ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | User |
| `topic_name` | VARCHAR(200) | NOT NULL | Topic/chapter name |
| `proficiency` | INTEGER | DEFAULT 0 | Proficiency score (0-100) |
| `completed` | BOOLEAN | DEFAULT FALSE | Topic completion status |
| `updated_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → TopicProficiencies: **1:N**

---

#### **Table: `syllabus_document`**
**Purpose:** Uploaded PDF syllabi with extracted text for AI context

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique document ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Document owner |
| `filename` | VARCHAR(100) | NOT NULL | Original filename |
| `extracted_text` | TEXT | NULLABLE | Extracted PDF text for AI |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Upload timestamp |

**Relationships:**
- Many-to-One with `User`
- One-to-Many with `Todo`

**Cardinality:**
- User → SyllabusDocuments: **1:N**
- SyllabusDocument → Todos: **1:N**

---

### **5. SOCIAL FEATURES**

#### **Table: `group`**
**Purpose:** Study group/room information

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique group ID |
| `name` | VARCHAR(100) | NOT NULL | Group name |
| `admin_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Group creator/admin |
| `invite_code` | VARCHAR(10) | UNIQUE, NOT NULL | Invite code for joining |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Relationships:**
- Many-to-One with `User` (admin)
- Many-to-Many with `User` (via `GroupMember`)
- One-to-Many with `GroupChatMessage`

**Cardinality:**
- User (admin) → Groups: **1:N**
- Group → Members: **M:N** (via GroupMember)
- Group → Messages: **1:N**

---

#### **Table: `group_member`**
**Purpose:** Junction table for group membership

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique membership ID |
| `group_id` | INTEGER | FOREIGN KEY → group.id, NOT NULL | Group |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Member |
| `joined_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Join timestamp |

**Constraints:**
- UNIQUE(group_id, user_id) - Prevents duplicate memberships

**Relationships:**
- Many-to-One with `Group`
- Many-to-One with `User`

**Cardinality:**
- Group → GroupMembers: **1:N**
- User → GroupMembers: **1:N**

---

#### **Table: `group_chat_message`**
**Purpose:** Messages in group chat rooms

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique message ID |
| `group_id` | INTEGER | FOREIGN KEY → group.id, NOT NULL | Group/room |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NULLABLE | Sender (NULL for AI) |
| `role` | VARCHAR(20) | NOT NULL | Role: 'user' or 'assistant' |
| `content` | TEXT | NOT NULL | Message content |
| `file_path` | VARCHAR(255) | NULLABLE | Attached file path |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Message timestamp |

**Relationships:**
- Many-to-One with `Group`
- Many-to-One with `User`

**Cardinality:**
- Group → GroupChatMessages: **1:N**
- User → GroupChatMessages: **1:N**

---

#### **Table: `chat_message`**
**Purpose:** Personal AI chat messages (1-on-1 with AI assistant)

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique message ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | User |
| `role` | VARCHAR(20) | NOT NULL | Role: 'user' or 'assistant' |
| `content` | TEXT | NOT NULL | Message content |
| `is_group` | BOOLEAN | DEFAULT FALSE | Group message flag |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Message timestamp |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → ChatMessages: **1:N**

---

### **6. EVENTS & CALENDAR**

#### **Table: `event`**
**Purpose:** Calendar events and reminders

| Column Name | Data Type | Constraints | Description |
|------------|-----------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique event ID |
| `user_id` | INTEGER | FOREIGN KEY → user.id, NOT NULL | Event owner |
| `title` | VARCHAR(200) | NOT NULL | Event title |
| `description` | TEXT | NULLABLE | Event description |
| `date` | VARCHAR(50) | NOT NULL | Event date (YYYY-MM-DD) |
| `time` | VARCHAR(50) | NULLABLE | Event time (HH:MM) |
| `is_notified` | BOOLEAN | DEFAULT FALSE | Notification sent flag |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Relationships:**
- Many-to-One with `User`

**Cardinality:**
- User → Events: **1:N**

---

## 🔗 **RELATIONSHIP SUMMARY**

### **One-to-Many Relationships**

| Parent Table | Child Table | Foreign Key | Description |
|-------------|-------------|-------------|-------------|
| `user` | `todo` | user_id | User owns many tasks |
| `user` | `chat_message` | user_id | User has many chat messages |
| `user` | `study_session` | user_id | User has many study sessions |
| `user` | `topic_proficiency` | user_id | User tracks many topics |
| `user` | `event` | user_id | User has many events |
| `user` | `habit` | user_id | User has many habits |
| `user` | `syllabus_document` | user_id | User uploads many syllabi |
| `user` | `xp_history` | user_id | User has many XP transactions |
| `user` | `user_item` | user_id | User owns many items |
| `user` | `active_power_up` | user_id | User has many active power-ups |
| `user` | `group` | admin_id | User can admin many groups |
| `user` | `group_chat_message` | user_id | User sends many group messages |
| `group` | `group_chat_message` | group_id | Group has many messages |
| `habit` | `habit_log` | habit_id | Habit has many completion logs |
| `syllabus_document` | `todo` | syllabus_id | Syllabus generates many tasks |

### **Many-to-Many Relationships**

| Table 1 | Table 2 | Junction Table | Description |
|---------|---------|----------------|-------------|
| `user` | `badge` | `user_badge` | Users earn badges |
| `user` | `user` | `friendship` | Users befriend users |
| `user` | `group` | `group_member` | Users join groups |

---

## 📐 **CARDINALITY NOTATION**

### **Legend:**
- **1:1** - One-to-One
- **1:N** - One-to-Many
- **M:N** - Many-to-Many

### **Complete Cardinality Map:**

```
USER (1) ──────< (N) TODO
USER (1) ──────< (N) CHAT_MESSAGE
USER (1) ──────< (N) STUDY_SESSION
USER (1) ──────< (N) TOPIC_PROFICIENCY
USER (1) ──────< (N) EVENT
USER (1) ──────< (N) HABIT
USER (1) ──────< (N) SYLLABUS_DOCUMENT
USER (1) ──────< (N) XP_HISTORY
USER (1) ──────< (N) USER_ITEM
USER (1) ──────< (N) ACTIVE_POWER_UP

USER (M) ──────< FRIENDSHIP >──────< (N) USER
USER (M) ──────< USER_BADGE >──────< (N) BADGE
USER (M) ──────< GROUP_MEMBER >──────< (N) GROUP

GROUP (1) ──────< (N) GROUP_CHAT_MESSAGE
HABIT (1) ──────< (N) HABIT_LOG
SYLLABUS_DOCUMENT (1) ──────< (N) TODO
```

---

## 🎯 **KEY FEATURES & CONSTRAINTS**

### **Unique Constraints:**
- `user.email` - Ensures unique user accounts
- `user.google_id` - Prevents duplicate OAuth accounts
- `group.invite_code` - Unique group join codes
- `group_member(group_id, user_id)` - Prevents duplicate memberships

### **Indexes:**
- `user.email` - Fast login lookups
- Foreign keys automatically indexed for join performance

### **Cascading Behavior:**
- Most foreign keys use default CASCADE on delete
- Deleting a user removes all associated data
- Deleting a group removes all messages and memberships

---

## 📊 **GAMIFICATION LOGIC**

### **XP System:**
- **Level Calculation:** `level = floor(total_xp / 500) + 1`
- **XP Sources:** Tasks, Focus Sessions, Quizzes, Battles
- **Daily Caps:** Focus XP capped at 500/day to prevent farming

### **Rank System:**
| Level Range | Rank | Icon | Color |
|------------|------|------|-------|
| 1-5 | Bronze | fa-shield-halved | #CD7F32 |
| 6-10 | Silver | fa-shield-halved | #C0C0C0 |
| 11-20 | Gold | fa-shield-halved | #FFD700 |
| 21-35 | Platinum | fa-gem | #E5E4E2 |
| 36-50 | Diamond | fa-gem | #b9f2ff |
| 51-75 | Heroic | fa-crown | #ff4d4d |
| 76-100 | Master | fa-crown | #ff0000 |
| 101+ | Grandmaster | fa-dragon | #800080 |

### **Streak System:**
- Tracked via `user.last_activity_date`
- Increments on daily activity
- Resets if a day is missed
- `longest_streak` stores personal best

---

## 🛠️ **TECHNICAL NOTES**

### **Database Engine:**
- **Development:** SQLite
- **Production:** PostgreSQL (Render.com)

### **ORM:**
- SQLAlchemy with Flask-SQLAlchemy

### **Connection Pooling:**
- NullPool for eventlet compatibility
- pool_pre_ping enabled for connection validation

### **Timezone Handling:**
- All timestamps stored in UTC
- Converted to IST (Asia/Kolkata) for display

---

## 📝 **USAGE NOTES FOR ER DIAGRAM**

When creating your ER diagram, use this notation:

### **Entities (Tables):**
- Rectangle boxes for each table
- Primary keys underlined
- Foreign keys marked with (FK)

### **Relationships:**
- Lines connecting related tables
- Crow's foot notation for cardinality:
  - `──────<` for "many"
  - `──────|` for "one"
  - `──────○` for "zero or one"

### **Example ER Diagram Structure:**

```
┌─────────────────┐
│      USER       │
├─────────────────┤
│ id (PK)         │
│ email           │
│ total_xp        │
│ level           │
└─────────────────┘
        │
        │ 1:N
        │
        ▼
┌─────────────────┐
│      TODO       │
├─────────────────┤
│ id (PK)         │
│ user_id (FK)    │
│ title           │
│ completed       │
└─────────────────┘
```

---

## 🎓 **SUMMARY**

**Total Tables:** 18
**Total Relationships:** 23
**Primary Keys:** 18
**Foreign Keys:** 28
**Unique Constraints:** 5
**Indexes:** 6+

This schema supports a comprehensive gamified study platform with social features, AI integration, and robust progress tracking.

---

**Last Updated:** February 2026
**Version:** 2.0
**Database:** PostgreSQL (Production) / SQLite (Development)
