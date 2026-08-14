<div align="center">

<img src="https://img.shields.io/badge/StudyVerse-AI%20Powered-4ade80?style=for-the-badge&logo=bookstack&logoColor=black" alt="StudyVerse"/>

# 🎓 StudyVerse — AI-Powered Study Companion

**The ultimate student productivity platform built with Flask, powered by Google Gemini AI.**  
Gamified learning · Real-time collaboration · Smart AI tools · All in one place.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Production-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Gemini AI](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render.com-46E3B7?style=flat-square&logo=render&logoColor=white)](https://render.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-Real--time-010101?style=flat-square&logo=socket.io&logoColor=white)](https://socket.io)

</div>

---

## ✨ Features

### 🤖 AI-Powered Tools
| Feature | Description |
|---------|-------------|
| **AI Study Coach** | Context-aware Gemini AI chatbot — understands your syllabus, answers questions, explains topics |
| **Topic Resolver** | Deep-dive any topic: get explanations, YouTube videos, visual diagrams, all in one click |
| **Photo Solver** | Upload a photo of any question — AI solves it instantly (Gemini Vision) |
| **AI Quiz Generator** | Auto-generates MCQ quizzes based on your uploaded syllabus PDF |
| **AI Planner** | Generates a smart daily study plan based on your tasks and goals |
| **VERSE AI Assistant** | Voice-enabled AI assistant — talk to it, navigate the app hands-free |

---

### 📚 Study & Productivity
| Feature | Description |
|---------|-------------|
| **Dashboard** | Real-time study stats, XP, level, streak, daily productivity meter, temporal task grid |
| **Task Manager (Todos)** | Smart to-do list with priorities, categories, due dates, undo stack, and AI batch generation |
| **Pomodoro Timer (Focus Mode)** | Focus sessions with break scheduling, session logging, daily goals, and XP rewards |
| **Syllabus Tracker** | Upload PDF syllabi, track topic proficiency, AI generates tasks from course content |
| **Progress Tracker** | Detailed study analytics — XP history, time studied, quiz accuracy, streak graphs |
| **Habit Tracker** | Daily habits with streaks and completion stats |
| **Calendar & Events** | Schedule events, set reminders, get deadline warnings |

---

### 🎮 Gamification
| Feature | Description |
|---------|-------------|
| **XP & Level System** | Earn XP from tasks, quizzes, focus sessions, streaks — level up continuously |
| **Rank System** | Bronze → Silver → Gold → Platinum → Diamond → Heroic → Master → Grandmaster |
| **Badges** | Achievement badges for milestones, streaks, quiz scores, and more |
| **Daily Streaks** | Study every day to maintain and grow your streak |
| **Leaderboard** | Compete with all StudyVerse users globally on XP ranking |
| **Item Shop** | Spend coins on power-ups, profile frames, themes, and cosmetics |
| **Byte Battle** | Real-time competitive 1v1 quiz battles against other users |

---

### 👥 Social & Collaboration
| Feature | Description |
|---------|-------------|
| **Group Study Rooms** | Create/join study groups with invite codes, real-time chat via Socket.IO |
| **File Sharing in Groups** | Share images, PDFs, ZIP files, code files (HTML/JS/Python/etc.) in group chat |
| **Pinned Messages** | Admins can pin important announcements in group chat |
| **Friends System** | Send/accept friend requests, view friend profiles and stats |
| **Live Streams** | Watch and host live study streams within the platform |
| **Video Calls** | Built-in call feature for real-time study sessions |
| **Invite & Earn** | Referral system — invite friends and earn rewards |

---

### 🔐 Authentication & Security
| Feature | Description |
|---------|-------------|
| **Email Sign Up / Sign In** | Secure registration with OTP email verification via SendGrid |
| **Google OAuth 2.0** | One-click sign in with Google |
| **Session Management** | Flask-Login with secure cookie sessions |
| **Password Hashing** | Werkzeug bcrypt-based password security |
| **Ban / Appeal System** | Admin can ban users; users can submit ban appeals |

---

### 🛠️ Admin Panel
| Feature | Description |
|---------|-------------|
| **User Management** | View all users, adjust XP, ban/unban, delete accounts, send alerts |
| **Support Center** | Full ticket system — users submit issues, admins reply and close tickets |
| **Analytics Dashboard** | Platform-wide stats — signups, active users, session counts, quiz plays |
| **Gamification Control** | Manage XP events, badge criteria, shop items |
| **Battle Monitor** | View all active and past Byte Battles |
| **Feedback Dashboard** | View all user feedback submissions with emoji ratings and categories |
| **Action Logs** | Full audit trail of all admin actions |

---

### 🎨 UX & Design
| Feature | Description |
|---------|-------------|
| **Dark Mode UI** | Premium dark theme with glassmorphism cards and gradient accents |
| **Zen Mode** | Distraction-free study mode — hides sidebar, clears clutter |
| **PWA Support** | Installable as a Progressive Web App — works offline |
| **Feedback Widget** | In-app feedback modal from sidebar — emoji rating + categories |
| **Responsive Design** | Works on desktop, tablet, and mobile |
| **Settings & Profile** | Custom display name, profile image, cover image, bio, public profile page |

---

## 🧠 Architecture

```
StudyVerse/
├── app.py                    # 9400+ line Flask app (routes, models, services, sockets)
├── templates/                # Jinja2 HTML templates
│   ├── layout.html           # Base layout — sidebar, modals, global JS
│   ├── dashboard.html        # Main dashboard
│   ├── group_chat.html       # Real-time group study rooms
│   ├── battle.html           # Byte Battle quiz arena
│   ├── topic_resolver.html   # AI topic deep-dive
│   ├── photo_solver.html     # AI image question solver
│   ├── live.html             # Live streams
│   └── ...                   # 20+ more templates
├── static/
│   ├── css/style.css         # Main stylesheet
│   ├── js/                   # Feature-specific JS modules
│   └── uploads/              # User uploaded files (dev only)
├── requirements.txt          # Python dependencies
├── render.yaml               # Render.com deployment config
├── Procfile                  # Gunicorn production server config
└── gunicorn.conf.py          # Gunicorn settings
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, Flask 3.0, Flask-SocketIO 5.5, Eventlet |
| **AI** | Google Gemini 2.5 Flash (text + vision), YouTube Data API v3 |
| **Database** | PostgreSQL via Neon (production), SQLite (development) |
| **ORM** | Flask-SQLAlchemy 3.1 |
| **Auth** | Flask-Login, Authlib (OAuth 2.0), SendGrid (OTP email) |
| **Real-time** | Socket.IO, Eventlet (WebSocket) |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript ES6+, Socket.IO Client |
| **Deployment** | Render.com, Gunicorn, WhiteNoise (static files) |

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the repo
```bash
git clone https://github.com/Manin1311/StudyVerse_Final.git
cd StudyVerse_Final
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:
```env
# Required
SECRET_KEY=your-secret-key-here
DATABASE_URL=your-postgresql-url

# AI (Google Gemini)
AI_API_KEY=your-gemini-api-key
AI_API_TYPE=google
AI_MODEL=models/gemini-2.5-flash

# Email OTP (SendGrid)
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_SENDER_EMAIL=your@email.com
SENDGRID_SENDER_NAME=StudyVerse

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# YouTube API (for Topic Resolver videos)
YOUTUBE_API_KEY=your-youtube-api-key
```

### 5. Run the app
```bash
python app.py
```

Open → [http://localhost:5000](http://localhost:5000)

---

## 🌐 Deployment (Render.com)

This project is production-ready for Render.com:

1. Fork this repo
2. Create a new **Web Service** on Render
3. Connect your GitHub repo
4. Set all environment variables in Render dashboard
5. Render auto-detects `render.yaml` / `Procfile` — deploy!

The app uses **Gunicorn + Eventlet** as the production server and **WhiteNoise** for static file serving.

---

## 📊 Data Structures & Algorithms Used

- **Stack (LIFO)** — Undo functionality for todo deletions
- **LRU Cache** — Optimizes repeated DB queries
- **Hash Maps** — O(1) lookups for user sessions, quiz scoring
- **Sorting** — Leaderboard ranking, quiz question shuffle
- **Graph** — Syllabus topic proficiency visualization

---

## 📄 License

This project is for educational purposes.  
Built with ❤️ by the StudyVerse Team.

---

<div align="center">

**⭐ Star this repo if you find it useful!**

[![GitHub stars](https://img.shields.io/github/stars/Manin1311/StudyVerse_Final?style=social)](https://github.com/Manin1311/StudyVerse_Final)

</div>
