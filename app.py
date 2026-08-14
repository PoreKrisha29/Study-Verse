"""
StudyVerse - AI-Powered Study Companion Platform
=================================================

OVERVIEW:
---------
StudyVerse is a comprehensive web-based study management platform that combines
gamification, AI assistance, and collaborative features to enhance student productivity.

KEY FEATURES:
-------------
1. **AI-Powered Study Assistant**: Context-aware chatbot using Google Gemini API
2. **Gamification System**: XP, levels, ranks, badges, and streaks to motivate learning
3. **Task Management**: Smart todo system with priorities, categories, and syllabus integration
4. **Pomodoro Timer**: Focus sessions with XP rewards and productivity tracking
5. **Quiz System**: AI-generated quizzes based on uploaded syllabus
6. **Battle Mode**: Competitive quiz battles between users
7. **Group Study**: Real-time collaborative chat rooms with file sharing
8. **Friends System**: Social features with friend requests and leaderboards
9. **Shop System**: Virtual currency (coins) to purchase power-ups and cosmetics
10. **Calendar Integration**: Event scheduling with reminders

ARCHITECTURE & DESIGN PATTERNS:
-------------------------------
- **MVC Pattern**: Flask routes (Controller), SQLAlchemy models (Model), Jinja templates (View)
- **Service Layer Pattern**: Separate service classes (AuthService, GamificationService, etc.)
- **Repository Pattern**: Database operations abstracted through SQLAlchemy ORM
- **Real-time Communication**: Socket.IO for chat and live updates
- **Data Structures**: Custom implementations (Stack for undo, LRU Cache for optimization)

TECHNOLOGIES USED:
------------------
Backend:
- Flask (Web framework)
- SQLAlchemy (ORM for database operations)
- Flask-Login (User session management)
- Flask-SocketIO (Real-time bidirectional communication)
- Eventlet (Asynchronous server for Socket.IO)
- Google Gemini AI (Natural language processing and quiz generation)
- OAuth 2.0 (Google authentication)

Frontend:
- HTML5, CSS3, JavaScript (ES6+)
- Socket.IO Client (Real-time features)
- Particles.js (Visual effects)
- Font Awesome (Icons)

Database:
- PostgreSQL (Production - Render.com)
- SQLite (Development)

DEPLOYMENT:
-----------
- Platform: Render.com
- Proxy: WhiteNoise for static file serving
- Environment: Production-ready with SSL/HTTPS support

DATA STRUCTURES & ALGORITHMS:
-----------------------------
1. **Stack**: LIFO structure for undo functionality in todos
2. **LRU Cache**: Least Recently Used cache for optimizing repeated queries
3. **Hash Maps**: Dictionary-based lookups for O(1) performance
4. **Sorting Algorithms**: Leaderboard ranking and quiz question ordering

GAMIFICATION LOGIC:
-------------------
- XP System: Users earn experience points from various activities
- Level Calculation: level = floor(total_xp / 500) + 1
- Ranks: Bronze †’ Silver †’ Gold †’ Platinum †’ Diamond †’ Heroic †’ Master †’ Grandmaster
- Badges: Achievement system based on streaks, levels, and milestones
- Streaks: Daily activity tracking with longest streak records

SECURITY FEATURES:
------------------
- Password hashing using Werkzeug's security functions
- CSRF protection via Flask-WTF
- Session management with secure cookies (HTTPS in production)
- OAuth 2.0 for secure third-party authentication
- Environment-based configuration for sensitive data

AUTHORS: StudyVerse Development Team
VERSION: 2.0
LAST UPDATED: February 2026
"""

# ============================================================================
# IMPORTS AND INITIALIZATION
# ============================================================================

# Eventlet monkey-patching for async Socket.IO support
# IMPORTANT: This must happen BEFORE other imports if eventlet is used.
# We guard it so it only activates when eventlet is actually the chosen worker/async mode.
# Unconditional patching at module import time infects the gunicorn *master* process
# and causes: RuntimeError: do not call blocking functions from the mainloop
import eventlet
eventlet.monkey_patch()



# Database and ORM imports
from sqlalchemy.pool import NullPool
from flask import Flask, render_template, request, session, redirect, url_for, Response, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_socketio import SocketIO, join_room, emit

# Security and authentication
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth

# Utilities
import base64
import io
import json
import os
import requests
from pytz import timezone, utc

import os
import sys
import time
import re
from dotenv import load_dotenv

# Load environment variables from .env file for configuration
load_dotenv()

# ============================================================================
# SIGNUP VALIDATION HELPERS
# ============================================================================

# --- Profanity Filter ---
# A curated list of common bad words / slang to block in user names.
_PROFANITY_LIST = [
    'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'cunt', 'dick', 'pussy',
    'cock', 'whore', 'slut', 'nigger', 'nigga', 'faggot', 'retard', 'idiot',
    'stupid', 'moron', 'dumbass', 'jackass', 'prick', 'wanker', 'twat',
    'rape', 'rapist', 'pedo', 'pedophile', 'sex', 'porn', 'nude', 'naked',
    'boob', 'tits', 'ass', 'arse', 'anal', 'dildo', 'jerk', 'loser',
    'gay', 'homo', 'tranny', 'chink', 'spic', 'kike', 'cracker',
    'admin', 'moderator', 'studyverse', 'support', 'official',
    'fuk', 'fck', 'fucc', 'fvck', 'phuck', 'sht', 'shyt', 'biatch',
    'bytch', 'b1tch', 'btch', 'azz', 'a55', 'a$$',
]

# Leet speak / symbol substitution map
# Converts tricks like f*ck †’ fuck, sh!t †’ shit, b!tch †’ bitch, @ss †’ ass
_LEET_MAP = str.maketrans({
    '@': 'a',  '4': 'a',  '3': 'e',  '1': 'i',  '!': 'i',
    '0': 'o',  '5': 's',  '$': 's',  '7': 't',  '+': 't',
    '9': 'g',  '6': 'g',  '8': 'b',  '2': 'z',
    '*': '',   '-': '',   '_': '',   '.': '',   ',': '',
    '(': 'c',  ')': '',   '#': 'h',  '%': '',   '^': '',
    '&': '',   '=': '',   '~': '',   '`': '',   "'": '',
    '"': '',   '/': '',   '\\': '',  '|': 'i',  '<': 'c',
    '>': '',   '[': '',   ']': '',   '{': '',   '}': '',
})

def _normalize_leet(text: str) -> str:
    """
    Normalize leet speak and symbol substitutions.
    e.g.  'f*ck' †’ 'fck', 'sh!t' †’ 'shit', 'b!tch' †’ 'bitch', '@ss' †’ 'ass'
    """
    return text.lower().translate(_LEET_MAP)

def contains_profanity(text: str) -> bool:
    """
    Check if text contains any profanity or bad words.
    Checks both the raw text AND the leet-speak-normalized version
    so tricks like f*ck, sh!t, b1tch, @sshole are all caught.
    """
    if not text:
        return False
    raw   = text.lower().strip()
    clean = _normalize_leet(raw)       # leet-decoded version
    for word in _PROFANITY_LIST:
        if word in raw or word in clean:
            return True
    return False


# --- Disposable / Fake Email Domain Blocklist ---
_BLOCKED_EMAIL_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'throwam.com',
    'yopmail.com', 'trashmail.com', 'sharklasers.com', 'guerrillamailblock.com',
    'grr.la', 'guerrillamail.info', 'spam4.me', 'bccto.me', 'chacuo.net',
    'dispostable.com', 'fakeinbox.com', 'filzmail.com', 'gawab.com',
    'get2mail.fr', 'getairmail.com', 'getmam.com', 'girlsundertheinfluence.com',
    'gkumar.com', 'glubex.com', 'gmailnull.com', 'gotmail.net', 'gotmail.org',
    'gowikibooks.com', 'gowikicampus.com', 'gowikifilms.com', 'gowikigames.com',
    'gowikimusic.com', 'gowikinetwork.com', 'gowikitravel.com', 'gowikitv.com',
    'gpatil.net', 'great-host.in', 'greensloth.com', 'grish.de', 'grr.la',
    'gs.com', 'gsrv.co.uk', 'gtermy.com', 'guam.net', 'guerrillamail.biz',
    'guerrillamail.de', 'guerrillamail.net', 'guerrillamail.org', 'guerrillamail.com',
    'maildrop.cc', 'mailnull.com', 'mailtemp.info', 'mailnesia.com',
    'spamgourmet.com', 'discard.email', 'tempinbox.com', 'tempr.email',
    'throwaway.email', 'nwytg.com', 'mohmal.com', 'owlpic.com',
    'spamboy.com', 'jourrapide.com', 'armyspy.com', 'cuvox.de',
    'dayrep.com', 'einrot.com', 'fleckens.hu', 'gustr.com', 'rhyta.com',
    'einrot.com', 'superrito.com', 'teleworm.us', 'thetestmail.com',
    'inboxbear.com', 'spambox.us', 'tempail.com', 'temp-mail.org',
    'temp-mail.io', 'tmpmail.net', 'tmpmail.org', 'emkei.cz', 'mt2014.com',
    'mt2015.com', 'verificationemail.com', 'vomoto.com', 'wpg.im',
    'xagloo.com', 'xemaps.com', 'xents.com', 'xmaily.com', 'xoxy.net',
    'ypmail.webarnak.fr.eu.org', 'yuurok.com', 'z1p.biz', 'za.com',
    'zippymail.info', 'zoemail.net', 'zoemail.org', 'zomg.info',
}


def is_blocked_email_domain(email: str) -> bool:
    """Check if the email domain is a known disposable/fake domain."""
    try:
        domain = email.strip().lower().split('@')[1]
        return domain in _BLOCKED_EMAIL_DOMAINS
    except (IndexError, AttributeError):
        return True  # Malformed email


def email_domain_has_mx(email: str) -> bool:
    """
    Check if the email domain has valid MX (Mail eXchange) DNS records.
    Uses dnspython to query DNS  catches fake domains like abc@notrealdomain123.com.
    Returns True if valid, False if the domain cannot receive emails.
    """
    try:
        import dns.resolver
        domain = email.strip().lower().split('@')[1]
        answers = dns.resolver.resolve(domain, 'MX', lifetime=5)
        return len(answers) > 0
    except Exception:
        # If DNS lookup fails (NXDOMAIN, timeout, etc.) †’ domain is invalid/fake
        return False


def validate_name_field(name: str, field_label: str) -> str:
    """
    Validate a name field (first name / last name).
    Returns an error message string, or empty string if valid.
    """
    name = name.strip()
    if not name:
        return f'{field_label} is required.'
    if len(name) < 2:
        return f'{field_label} must be at least 2 characters.'
    if len(name) > 50:
        return f'{field_label} must be at most 50 characters.'
    if not re.match(r"^[A-Za-z\s\-\']+$", name):
        return f'{field_label} can only contain letters, spaces, hyphens, and apostrophes.'
    if contains_profanity(name):
        return f'{field_label} contains inappropriate language. Please use your real name.'
    return ''

def send_task_reminder_email(to_email: str, first_name: str, task_title: str, due_date: str, due_time: str) -> bool:
    print(f"[*] Task Reminder: would send email to {to_email} for task '{task_title}' (due {due_date} {due_time})")
    return True


def send_otp_email(to_email: str, otp_code: str, first_name: str) -> bool:
    """
    Send a 6-digit OTP verification email via SendGrid HTTP API.
    No SMTP, no domain needed  delivers to ANY email address. Works on Render.
    Returns True if sent successfully, False otherwise.
    """
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    SENDER_EMAIL     = os.getenv('SENDGRID_SENDER_EMAIL', 'bhavsard094@gmail.com')
    SENDER_NAME      = os.getenv('SENDGRID_SENDER_NAME', 'StudyVerse')

    if not SENDGRID_API_KEY:
        print("[OTP] SENDGRID_API_KEY not set  skipping email send")
        return False


    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#0f0f0f;font-family:'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f0f;padding:40px 0;">
        <tr><td align="center">
          <table width="480" cellpadding="0" cellspacing="0"
                 style="background:#1a1a2e;border-radius:20px;border:1px solid rgba(255,255,255,0.08);overflow:hidden;">
            <!-- Header -->
            <tr>
              <td align="center" style="padding:36px 40px 24px;background:linear-gradient(135deg,#0ea5e9,#6366f1);">
                <div style="font-size:2.4rem;">“</div>
                <h1 style="color:white;margin:8px 0 0;font-size:1.6rem;font-weight:700;letter-spacing:-0.5px;">StudyVerse</h1>
                <p style="color:rgba(255,255,255,0.8);margin:4px 0 0;font-size:0.9rem;">Email Verification</p>
              </td>
            </tr>
            <!-- Body -->
            <tr>
              <td style="padding:36px 40px;">
                <p style="color:#e2e8f0;font-size:1rem;margin:0 0 8px;">Hey <strong>{first_name}</strong> ‘‹</p>
                <p style="color:#94a3b8;font-size:0.95rem;margin:0 0 28px;line-height:1.6;">
                  Thanks for joining StudyVerse! Use the verification code below to confirm your email address.
                  This code expires in <strong style="color:#f59e0b;">10 minutes</strong>.
                </p>
                <!-- OTP Box -->
                <div style="background:#0f172a;border:2px solid #0ea5e9;border-radius:16px;padding:28px;text-align:center;margin-bottom:28px;">
                  <p style="color:#64748b;font-size:0.8rem;margin:0 0 12px;text-transform:uppercase;letter-spacing:2px;">Your Verification Code</p>
                  <div style="font-size:3rem;font-weight:800;letter-spacing:12px;color:#0ea5e9;font-family:monospace;">{otp_code}</div>
                </div>
                <p style="color:#64748b;font-size:0.82rem;margin:0;line-height:1.6;">
                  š  Never share this code with anyone. StudyVerse will never ask for it.<br>
                  If you didn't request this, you can safely ignore this email.
                </p>
              </td>
            </tr>
            <!-- Footer -->
            <tr>
              <td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;">
                <p style="color:#475569;font-size:0.75rem;margin:0;"> 2026 StudyVerse  AI-Powered Study Companion</p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    try:
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers={
                'Authorization': f'Bearer {SENDGRID_API_KEY}',
                'Content-Type':  'application/json',
            },
            json={
                'personalizations': [{'to': [{'email': to_email}]}],
                'from':    {'email': SENDER_EMAIL, 'name': SENDER_NAME},
                'subject': f'{otp_code} is your StudyVerse verification code',
                'content': [{'type': 'text/html', 'value': html_body}],
            },
            timeout=10
        )
        # SendGrid returns 202 Accepted on success
        if response.status_code in (200, 201, 202):
            print(f"[OTP] Email sent via SendGrid to {to_email}")
            return True
        else:
            print(f"[OTP] SendGrid failed: {response.status_code}  {response.text}")
            return False
    except Exception as e:
        print(f"[OTP] Exception sending via SendGrid: {e}")
        return False




# ============================================================================
# AI API CONFIGURATION
# ============================================================================

# Allow OAuth over HTTP for local testing (commented out for production security)
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Check for required API Key - Google Gemini API for AI features
if not os.getenv("AI_API_KEY"):
    pass  # Application will work without AI features if key is missing

# Try to import Google Generative AI library for quiz generation and chat
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False  # Graceful degradation if library not installed

# ============================================================================
# FLASK APPLICATION INITIALIZATION
# ============================================================================

from werkzeug.middleware.proxy_fix import ProxyFix
from whitenoise import WhiteNoise



app = Flask(__name__)

# Template filter to convert UTC to IST
@app.template_filter('to_ist')
def to_ist_filter(dt):
    if dt:
        from datetime import timedelta
        return dt + timedelta(hours=5, minutes=30)
    return dt
# ProxyFix: Critical for deployment on Render/Heroku behind reverse proxy
# Ensures correct handling of HTTPS, host headers, and client IP addresses
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# WhiteNoise: Efficiently serve static files (CSS, JS, images) in production
# Reduces load on Flask app by handling static content directly
if os.getenv('RENDER') or os.getenv('PRODUCTION'):
    app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/', prefix='static/')

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

# Secret key for session encryption and CSRF protection
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database Configuration
# Production: Uses PostgreSQL from Render.com (DATABASE_URL environment variable)
# Development: Falls back to SQLite for local testing
database_url = os.getenv('DATABASE_URL', 'sqlite:///StudyVerse.db')

# Fix for Heroku/Render: Replace old 'postgres://' with 'postgresql://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable modification tracking to save memory

# Connection Pool Settings for Cloud PostgreSQL
# NullPool: Disables connection pooling to prevent "un-acquired lock" errors with eventlet
# pool_pre_ping: Tests connections before use to handle dropped connections
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': NullPool,      # No connection pooling (eventlet compatibility)
    'pool_pre_ping': True,      # Validate connections before use
}

# File upload configuration for profile images and syllabus PDFs
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# ============================================================================
# GOOGLE OAUTH 2.0 CONFIGURATION
# ============================================================================

# Google OAuth credentials from environment variables
# Allows users to sign in with their Google account
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Initialize OAuth client
oauth = OAuth(app)

# Register Google as an OAuth provider
# Scopes: openid (authentication), email (user email), profile (name, picture)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ============================================================================
# SESSION AND COOKIE CONFIGURATION
# ============================================================================

# Detect production environment (Render.com or manual PRODUCTION flag)
IS_PRODUCTION = os.getenv('RENDER', False) or os.getenv('PRODUCTION', False)

# Session lifetime: User stays logged in for 7 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Security settings for session cookies
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access (XSS protection)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# "Remember Me" functionality settings
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)  # 30-day remember me
app.config['REMEMBER_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS only in production
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================================
# SOCKET.IO INITIALIZATION (Real-Time Communication)
# ============================================================================

# Initialize Socket.IO for real-time features:
# - Group chat messaging
# - Live battle updates
# - Friend status updates
# - Real-time notifications
socketio = SocketIO(
    app,
    cors_allowed_origins="*",    # Allow all origins (configure for specific domain in production)
    async_mode='eventlet',        # Eventlet mode - matches gunicorn --worker-class eventlet in Procfile
    ping_timeout=120,             # 2-minute timeout for slow/mobile connections
    ping_interval=25,             # Send ping every 25 seconds to keep connection alive
    max_http_buffer_size=5e8,     # 500MB max message size (for file sharing)
    logger=False,                 # Disable verbose Socket.IO logs
    engineio_logger=False,        # Disable verbose Engine.IO logs
    transports=['polling', 'websocket'],  # Support both transports for compatibility
    cookie=None                   # Avoid session conflicts with some reverse proxies
)

# ============================================================================
# AI API CONFIGURATION (Google Gemini) - Multi-Key Rotation
# ============================================================================

# Collect all available API keys from environment variables.
# Priority: AI_API_KEY_1, AI_API_KEY_2, ... up to AI_API_KEY_9
# Backward-compatible: AI_API_KEY alone also works.
_raw_keys = []
for _i in range(1, 31):   # supports AI_API_KEY_1 ... AI_API_KEY_30
    _k = os.getenv(f"AI_API_KEY_{_i}", "").strip()
    if _k:
        _raw_keys.append(_k)
# Fall back to the original single-key env var if no numbered keys are set
if not _raw_keys:
    _single = os.getenv("AI_API_KEY", "").strip()
    if _single:
        _raw_keys.append(_single)

# Keep AI_API_KEY pointing to the first key (used in legacy checks like `if not AI_API_KEY`)
AI_API_KEY = _raw_keys[0] if _raw_keys else ""
AI_API_TYPE = os.getenv("AI_API_TYPE", "google")  # Currently only Google Gemini supported


class GeminiKeyRotator:
    """
    API Key Pool with automatic rotation on quota exhaustion.

    How it works:
    - Holds a list of Gemini API keys.
    - On every `generate_content` call, it uses the current active key.
    - If a ResourceExhausted (429) or quota error is detected, it rotates
      to the next key, re-configures genai, and retries automatically.
    - If ALL keys are exhausted, raises an exception.

    Usage in Render:
    - Set AI_API_KEY_1, AI_API_KEY_2, AI_API_KEY_3, ... in Render environment.
    """

    def __init__(self, keys: list):
        self.keys = keys
        self._index = 0  # Current active key index
        if GEMINI_AVAILABLE and self.keys:
            try:
                genai.configure(api_key=self.keys[0])
                print(f"[Gemini] Loaded {len(self.keys)} API key(s). Active: key #{1}")
            except Exception as e:
                print(f"[Gemini] Failed to configure with key #1: {e}")

    @property
    def current_key(self):
        return self.keys[self._index] if self.keys else ""

    def _is_quota_error(self, exc: Exception) -> bool:
        """Detect quota/rate-limit OR overload errors — rotate key on either."""
        err_str = str(exc).lower()
        rotatable_signals = [
            # Quota / rate-limit
            'resource_exhausted', 'resourceexhausted',
            'quota exceeded', 'quota_exceeded',
            '429', 'rate limit', 'ratelimit',
            'too many requests', 'per day',
            # Overload / high demand (503)
            '503', 'high demand', 'service unavailable',
            'unavailable', 'overloaded', 'server overload',
            'spikes in demand', 'try again later',
        ]
        return any(signal in err_str for signal in rotatable_signals)

    def _rotate(self) -> bool:
        """Rotate to the next available key. Returns True if rotation succeeded."""
        next_index = self._index + 1
        if next_index >= len(self.keys):
            print("[Gemini] All API keys exhausted. No more keys to try.")
            return False
        self._index = next_index
        new_key = self.keys[self._index]
        try:
            genai.configure(api_key=new_key)
            print(f"[Gemini] Rotated to API key #{self._index + 1}")
            return True
        except Exception as e:
            print(f"[Gemini] Failed to configure key #{self._index + 1}: {e}")
            return False

    def generate_content(self, model_name: str, *args, **kwargs):
        """
        Call generate_content with automatic key rotation on quota errors.
        Wraps genai.GenerativeModel(model_name).generate_content(...).
        """
        if not GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai library not installed.")
        if not self.keys:
            raise ValueError("No Gemini API keys configured.")

        tried = set()
        while True:
            if self._index in tried:
                raise RuntimeError("All Gemini API keys have been exhausted for today.")
            tried.add(self._index)
            try:
                model = genai.GenerativeModel(model_name)
                return model.generate_content(*args, **kwargs)
            except Exception as exc:
                if self._is_quota_error(exc):
                    print(f"[Gemini] Key #{self._index + 1} quota exhausted: {exc}")
                    if not self._rotate():
                        raise RuntimeError(
                            "All Gemini API keys have been exhausted for today. "
                            "Please try again tomorrow or add more API keys."
                        ) from exc
                    # Retry with the new key (loop continues)
                else:
                    raise  # Non-quota error  propagate immediately

    @property
    def available(self) -> bool:
        """True if at least one API key is configured."""
        return bool(self.keys)


# Global key rotator instance
gemini_rotator = GeminiKeyRotator(_raw_keys)

# ============================================================================
# TIMEZONE CONFIGURATION
# ============================================================================

# Indian Standard Time (IST) timezone for displaying times to users
IST = timezone('Asia/Kolkata')

def to_ist_time(utc_datetime):
    """
    Convert UTC datetime to IST and return formatted 12-hour time string.
    
    Args:
        utc_datetime: datetime object in UTC timezone
    
    Returns:
        str: Formatted time string in 12-hour format (e.g., "02:30 PM")
    """
    if not utc_datetime:
        return ""
    
    # Ensure datetime is timezone-aware (UTC)
    if utc_datetime.tzinfo is None:
        utc_datetime = utc.localize(utc_datetime)
    
    # Convert to IST
    ist_datetime = utc_datetime.astimezone(IST)
    
    # Format as 12-hour time with AM/PM
    return ist_datetime.strftime('%I:%M %p')

# ============================================================================
# DATABASE AND SERVICE INITIALIZATION
# ============================================================================

# AI Model selection (Gemini 2.5 Flash for fast responses)
AI_MODEL = os.getenv("AI_MODEL", "models/gemini-2.5-flash")

# Initialize SQLAlchemy for database operations
db = SQLAlchemy(app)

# Email functionality removed

# Initialize Flask-Login for user session management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'  # Redirect to 'auth' route if login required

# ============================================================================
# JINJA TEMPLATE FILTERS AND GLOBALS
# ============================================================================

# Register custom Jinja filter for timezone conversion in templates
@app.template_filter('ist_time')
def ist_time_filter(utc_datetime):
    """Jinja filter to convert UTC datetime to IST time string."""
    return to_ist_time(utc_datetime)

# Make to_ist_time available as a global function in all templates
app.jinja_env.globals.update(
    to_ist_time=to_ist_time,
    timedelta=timedelta,
    datetime=datetime
)


# ============================================================================
# DATABASE MODELS (ORM - Object Relational Mapping)

# ============================================================================
# These classes represent database tables using SQLAlchemy ORM
# Each class maps to a table, and each attribute maps to a column
# Benefits: Type safety, relationship management, query abstraction, database independence

class User(UserMixin, db.Model):
    """
    User Model - Core entity representing a StudyVerse user
    
    Inherits from:
    - UserMixin: Provides Flask-Login integration (is_authenticated, is_active, get_id, etc.)
    - db.Model: SQLAlchemy base class for ORM functionality
    
    Database Table: 'user'
    
    Field Categories:
    ----------------
    1. Authentication & Identity:
       - email: Unique identifier for login
       - password_hash: Encrypted password (bcrypt hashing)
       - google_id: For OAuth Google Sign-In users
    
    2. Profile Information:
       - first_name, last_name: User's name
       - profile_image: Avatar URL or path
       - cover_image: Profile banner image
       - about_me: Bio/description text
    
    3. Gamification (Motivation System):
       - total_xp: Cumulative experience points
       - level: Calculated from XP (500 XP per level)
       - current_streak: Consecutive days of activity
       - longest_streak: Record streak achievement
       - last_activity_date: For streak calculation
    
    4. Privacy & Status:
       - is_public_profile: Profile visibility setting
       - last_seen: Last activity timestamp
    
    Design Patterns Used:
    --------------------
    - Active Record: Model contains both data and behavior
    - Property Pattern: Computed fields (rank_info, active_frame_color)
    - Serialization: to_dict() for JSON API responses
    """
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication Fields
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth-only users
    google_id = db.Column(db.String(100), nullable=True, unique=True)  # Google OAuth ID
    
    # Profile Fields
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    profile_image = db.Column(db.String(255), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    about_me = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Gamification Fields (Core motivation system)
    total_xp = db.Column(db.Integer, default=0)  # Total experience points earned
    level = db.Column(db.Integer, default=1)  # User level (calculated from XP)
    current_streak = db.Column(db.Integer, default=0)  # Current daily activity streak
    longest_streak = db.Column(db.Integer, default=0)  # Best streak record
    last_activity_date = db.Column(db.Date, nullable=True)  # For streak tracking
    
    @property
    def rank_info(self):
        """
        Computed property: Returns rank details based on current level
        
        Returns:
            dict: {'name': str, 'icon': str, 'color': str}
            Example: {'name': 'Gold', 'icon': 'fa-shield-halved', 'color': '#FFD700'}
        """
        return GamificationService.get_rank(self.level)

    @property
    def active_frame_color(self):
        """
        Computed property: Returns the color of the user's equipped profile frame
        
        Profile frames are cosmetic items purchased from the shop.
        This property checks UserItem table for active frame items.
        
        Returns:
            str: Hex color code (e.g., '#FF5733') or None if no frame equipped
        """
        try:
            # Query all active items for this user
            active_items = UserItem.query.filter_by(user_id=self.id, is_active=True).all()
            for u_item in active_items:
                # Look up item details in shop catalog
                cat_item = ShopService.ITEMS.get(u_item.item_id)
                if cat_item and cat_item.get('type') == 'frame':
                    return cat_item.get('color')
        except Exception:
            pass  # Graceful degradation if shop system unavailable
        return None

    # Backward Compatibility Properties
    # These properties maintain compatibility with older template code
    @property
    def rank(self):
        """Backward compatibility: Returns rank name string"""
        return self.rank_info['name']

    @property
    def rank_name(self):
        """Backward compatibility: Returns rank name string"""
        return self.rank_info['name']

    @property
    def rank_icon(self):
        """Backward compatibility: Returns FontAwesome icon class"""
        return self.rank_info['icon']

    @property
    def rank_color(self):
        """Backward compatibility: Returns rank color hex code"""
        return self.rank_info['color']
    
    def get_avatar(self, size=200):
        """
        Generate avatar URL for the user
        
        Logic:
        1. If user uploaded custom image, use it
        2. Otherwise, generate initials-based avatar using UI Avatars API
        
        Args:
            size (int): Avatar size in pixels (default: 200)
        
        Returns:
            str: Avatar image URL
        """
        # Use uploaded profile image if available
        if self.profile_image and "ui-avatars.com" not in self.profile_image:
            return self.profile_image
        
        # Extract initials from name
        f_name = (self.first_name or '').strip()
        l_name = (self.last_name or '').strip()
        
        f = f_name[0] if f_name else ''
        l = l_name[0] if l_name else ''
        
        # Create initials (fallback to 'U' for User if no name)
        initials = f"{f}{l}".upper()
        if not initials:
            initials = "U"
        
        # Generate avatar using UI Avatars API
        return f"https://ui-avatars.com/api/?name={initials}&background=0ea5e9&color=fff&size={size}"
    
    def to_dict(self):
        """
        Serialize user data to dictionary for JSON API responses
        
        Use cases:
        - REST API endpoints
        - AJAX responses
        - Friend list data
        - Leaderboard entries
        
        Returns:
            dict: User data with computed fields
        """
        rank_data = GamificationService.get_rank(self.level)
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'level': self.level,
            'total_xp': self.total_xp,
            'rank': rank_data['name'],
            'rank_icon': rank_data['icon'],
            'rank_color': rank_data['color'],
            'avatar': self.get_avatar(),
            'is_public': self.is_public_profile
        }

    # Privacy & Status Fields
    is_public_profile = db.Column(db.Boolean, default=True)  # Profile visibility
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)  # Last activity timestamp
    
    # Admin Fields
    is_admin = db.Column(db.Boolean, default=False)  # Admin access flag
    
    # Ban/Suspension Fields
    is_banned = db.Column(db.Boolean, default=False)  # User ban status
    ban_reason = db.Column(db.Text, nullable=True)  # Reason for ban
    banned_at = db.Column(db.DateTime, nullable=True)  # When user was banned
    banned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who banned

    # Referral System Fields
    referral_code = db.Column(db.String(20), nullable=True, unique=True)  # Unique referral code
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who referred this user

class SupportTicket(db.Model):
    """
    Support Ticket Model - User support requests to admin
    
    Purpose: Allow users to contact admin for help, report issues, etc.
    
    Status Flow:
    1. User creates ticket †’ status='open'
    2. Admin responds †’ status='in_progress'
    3. Issue resolved †’ status='closed'
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('support_tickets', lazy=True))
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='general')  # general, bug, inappropriate, help
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    
    # Notification tracking
    user_unread_count = db.Column(db.Integer, default=0)  # Unread messages for user
    admin_unread_count = db.Column(db.Integer, default=1)  # Unread messages for admin (starts at 1 for new ticket)

class SupportMessage(db.Model):
    """
    Support Message Model - Messages within a support ticket
    
    Purpose: Track conversation between user and admin
    """
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # True if sent by admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_by_user = db.Column(db.Boolean, default=False)  # Has user read this?
    read_by_admin = db.Column(db.Boolean, default=False)  # Has admin read this?

class Friendship(db.Model):
    """
    Friendship Model - Manages friend connections between users
    
    Purpose: Track friend requests and relationships
    
    Relationship Type: Many-to-Many (User †” User)
    - A user can have many friends
    - Each friendship has a status (pending/accepted/rejected)
    
    Status Flow:
    1. User A sends friend request †’ status='pending'
    2. User B accepts †’ status='accepted'
    3. User B rejects †’ status='rejected'
    
    Database Design:
    - user_id: The user who sent the friend request
    - friend_id: The user who received the friend request
    - Foreign keys ensure referential integrity
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Request sender
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Request receiver
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Request timestamp
    
    # Optional: Bidirectional relationships (commented out for simplicity)
    # user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('friendships_sent', lazy='dynamic'))
    # friend = db.relationship('User', foreign_keys=[friend_id], backref=db.backref('friendships_received', lazy='dynamic'))


class StudyStream(db.Model):
    """
    StudyStream Model  Live study broadcast sessions.
    When a user goes live, a record is created here.
    Watchers and reactions are ephemeral (handled via SocketIO rooms).
    """
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic        = db.Column(db.String(200), default='Studying')
    subject      = db.Column(db.String(100), default='General')
    started_at   = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at     = db.Column(db.DateTime, nullable=True)
    duration_min = db.Column(db.Integer, default=0)        # minutes actually studied
    peak_watchers    = db.Column(db.Integer, default=0)    # max concurrent watchers
    solidarity_count = db.Column(db.Integer, default=0)    # friends who joined in
    status       = db.Column(db.String(20), default='live')  # 'live' | 'ended'
    timer_minutes = db.Column(db.Integer, default=25)       # Pomodoro session length


class Badge(db.Model):
    """
    Badge Model - Achievement badges for gamification
    
    Purpose: Define available achievement badges
    
    Badge Types:
    - Streak Badges: Awarded for consecutive daily activity
    - Level Badges: Awarded for reaching specific levels
    - Activity Badges: Awarded for completing specific tasks
    
    Fields:
    - name: Badge title (e.g., "Consistency King")
    - description: What the badge represents
    - icon: FontAwesome icon class (e.g., 'fa-fire')
    - criteria_type: What triggers the badge (streak, level, wins)
    - criteria_value: Threshold value (e.g., 30 for 30-day streak)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Badge name
    description = db.Column(db.String(255), nullable=False)  # Badge description
    icon = db.Column(db.String(50), default='fa-medal')  # FontAwesome icon class
    criteria_type = db.Column(db.String(50))  # Type: 'streak', 'level', 'wins', etc.
    criteria_value = db.Column(db.Integer)  # Threshold value

class UserBadge(db.Model):
    """
    UserBadge Model - Junction table for user-badge relationships
    
    Purpose: Track which badges each user has earned
    
    Relationship: Many-to-Many (User †” Badge)
    - A user can earn multiple badges
    - A badge can be earned by multiple users
    
    Design Pattern: Association Object
    - Links User and Badge tables
    - Stores additional data (earned_at timestamp)
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who earned badge
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)  # Badge earned
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)  # When badge was earned
    
    # Relationships for easy access
    user = db.relationship('User', backref='badges')  # Access user.badges
    badge = db.relationship('Badge')  # Access badge details

class XPHistory(db.Model):
    """
    XPHistory Model - Log of all XP transactions
    
    Purpose: Track XP gains and losses for analytics and debugging
    
    Use Cases:
    1. Daily XP caps (prevent farming)
    2. XP source analytics (which features earn most XP)
    3. User activity timeline
    4. Debugging XP discrepancies
    
    Sources:
    - 'battle': XP from quiz battles
    - 'task': XP from completing todos
    - 'focus': XP from Pomodoro sessions
    - 'quiz': XP from solo quizzes
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who earned/lost XP
    source = db.Column(db.String(50), nullable=False)  # Source: battle, task, focus, quiz
    amount = db.Column(db.Integer, nullable=False)  # XP amount (can be negative for losses)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # When XP was earned/lost

class GamificationService:
    """
    GamificationService - Business logic for XP, levels, ranks, and badges
    
    Design Pattern: Service Layer Pattern
    - Separates business logic from routes and models
    - Provides reusable methods for gamification features
    - Centralizes complex calculations and rules
    
    Responsibilities:
    1. XP Management: Add/deduct experience points with multipliers
    2. Level Calculation: Convert XP to levels (500 XP per level)
    3. Rank Assignment: Map levels to ranks (Bronze †’ Grandmaster)
    4. Badge Awards: Check criteria and award achievement badges
    5. Streak Tracking: Daily activity streak management
    
    Key Algorithms:
    - Level formula: level = floor(total_xp / 500) + 1
    - Rank lookup: O(1) dictionary lookup by level range
    - Daily cap: Prevents XP farming (max 500 XP/day from focus)
    
    Power-up Integration:
    - XP Multipliers: Boost XP gains (2x, 3x)
    - Time Multipliers: Double focus session rewards
    - XP Protection: Prevent XP loss in battles
    """
    
    # Rank System: Maps level ranges to rank details
    # Format: (min_level, max_level): (name, icon, color)
    RANKS = {
        (1, 5): ('Bronze', 'fa-shield-halved', '#CD7F32'),  # Beginner
        (6, 10): ('Silver', 'fa-shield-halved', '#C0C0C0'),  # Intermediate
        (11, 20): ('Gold', 'fa-shield-halved', '#FFD700'),  # Advanced
        (21, 35): ('Platinum', 'fa-gem', '#E5E4E2'),  # Expert
        (36, 50): ('Diamond', 'fa-gem', '#b9f2ff'),  # Master
        (51, 75): ('Heroic', 'fa-crown', '#ff4d4d'),  # Elite
        (76, 100): ('Master', 'fa-crown', '#ff0000'),  # Legendary
        (101, 10000000000000): ('Grandmaster', 'fa-dragon', '#800080')
    }

    @staticmethod
    def calculate_level(total_xp):
        # Level = floor(total_xp / 500) + 1
        return max(1, int(total_xp / 500) + 1)

    @staticmethod
    def get_rank(level):
        if level is None: level = 1
        for (min_lvl, max_lvl), (name, icon, color) in GamificationService.RANKS.items():
            if min_lvl <= level <= max_lvl:
                return {'name': name, 'icon': icon, 'color': color}
        return {'name': 'Bronze', 'icon': 'fa-shield-halved', 'color': '#CD7F32'}

    @staticmethod
    def add_xp(user_id, source, amount, force_deduct=False):
        user = User.query.get(user_id)
        if not user:
            return
        
        # Prevent XP changes for demo/test users
        # This stops automatic XP increments for presentation/demo accounts
        demo_emails = ['daksh@gmail.com', 'daksh@studyverse.com', 'demo@studyverse.com']
        if user.email and user.email.lower() in demo_emails:
            print(f"XP change blocked for demo user: {user.email}")
            return {'earned': 0, 'message': 'Demo account - XP locked'}


        # 1. Fetch ALL active power-ups for the user
        active_powerups = ActivePowerUp.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        # 2. Categorize and clean up expired power-ups
        xp_multiplier = 1.0
        time_multiplier = 1.0
        has_protection = False
        active_boost = None

        for powerup in active_powerups:
            if powerup.is_expired():
                powerup.is_active = False
                continue
            
            # Fetch item details from catalog to know the effect type
            item_id = powerup.power_up_id
            cat_item = ShopService.ITEMS.get(item_id)
            if not cat_item: continue

            effect = cat_item.get('effect')
            
            if effect in ['xp_multiplier', 'mega_xp_multiplier']:
                if powerup.multiplier > xp_multiplier:
                    xp_multiplier = powerup.multiplier
                    active_boost = item_id
            elif effect == 'time_multiplier':
                if powerup.multiplier > time_multiplier:
                    time_multiplier = powerup.multiplier
            elif effect == 'xp_protection':
                has_protection = True
        
        # 3. Handle XP loss protection
        if amount < 0:
            if not force_deduct and has_protection:
                return {'earned': 0, 'message': 'XP Protection Active! No XP lost.'}
            
            # Direct deduction logic
            user.total_xp = max(0, user.total_xp + amount) # Check bounds? Or allow negative? keeping 0 floor
            
            # Log negative history
            log = XPHistory(user_id=user.id, source=source, amount=amount)
            db.session.add(log)
            # Note: caller is responsible for committing
            return {'earned': amount, 'new_total': user.total_xp}

        # 4. Apply special multipliers based on source (e.g., Double Time for focus)
        actual_multiplier = xp_multiplier
        if source == 'focus' and time_multiplier > 1.0:
            # If both XP boost and Double Time are active, they might stack or we take the highest.
            # Usually, Double Time specifically doubles the focus reward.
            actual_multiplier *= time_multiplier

        # 5. Cap Focus XP daily (Check BEFORE multipliers to keep cap consistent)
        if source == 'focus':
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_focus_xp = db.session.query(db.func.sum(XPHistory.amount))\
                .filter(XPHistory.user_id == user.id, XPHistory.source == 'focus', XPHistory.timestamp >= today_start)\
                .scalar() or 0
            
            # Simple daily cap logic: max 500 XP from focus per day
            if daily_focus_xp >= 500:
                return {'earned': 0, 'message': 'Daily Focus XP cap reached!'}
            
            if daily_focus_xp + amount > 500:
                amount = 500 - daily_focus_xp

        if amount <= 0:
            return

        # Apply multiplier
        original_amount = amount
        if actual_multiplier > 1.0:
            amount = int(amount * actual_multiplier)

        user.total_xp += amount
        
        # Level Up Check
        new_level = GamificationService.calculate_level(user.total_xp)
        leveled_up = False
        if new_level > user.level:
            user.level = new_level
            leveled_up = True
            
        # Log History
        log = XPHistory(user_id=user.id, source=source, amount=amount)
        db.session.add(log)
        
        # Update Streak (if not already updated today)
        GamificationService.update_streak(user)
        
        # Check Badges
        GamificationService.check_badges(user)
        
        # Note: caller is responsible for committing
        
        result = {
            'earned': amount, 
            'new_total': user.total_xp, 
            'leveled_up': leveled_up,
            'new_level': user.level,
            'rank': GamificationService.get_rank(user.level)
        }
        
        # Add multiplier info if active
        if actual_multiplier > 1.0:
            result['multiplier'] = actual_multiplier
            result['base_amount'] = original_amount
            result['boost_active'] = active_boost
        
        return result

    @staticmethod
    def update_streak(user):
        today = datetime.utcnow().date()
        if user.last_activity_date == today:
            return # Already active today
        
        if user.last_activity_date == today - timedelta(days=1):
            user.current_streak += 1
        else:
            user.current_streak = 1 # Reset if missed a day (or first time)
            
        user.last_activity_date = today
        if user.current_streak > user.longest_streak:
            user.longest_streak = user.current_streak

    @staticmethod
    def check_badges(user):
        # 1. Streak Badges
        if user.current_streak >= 30:
            GamificationService.award_badge(user, 'Consistency King')
        
        # 2. XP Badges (Level based roughly)
        if user.level >= 10:
             GamificationService.award_badge(user, 'Rising Star')
        if user.level >= 50:
             GamificationService.award_badge(user, 'Dedicated Scholar')
        if user.level >= 100:
             GamificationService.award_badge(user, 'Centurion')
             
        # More rules can be added here
        
    @staticmethod
    def award_badge(user, badge_name):
        badge = Badge.query.filter_by(name=badge_name).first()
        if not badge:
            # Create default if missing (lazy init)
            if badge_name == 'Consistency King':
                badge = Badge(name='Consistency King', description='Achieve a 30-day streak', icon='fa-fire', criteria_type='streak', criteria_value=30)
            elif badge_name == 'Rising Star':
                badge = Badge(name='Rising Star', description='Reach Level 10', icon='fa-star', criteria_type='level', criteria_value=10)
            elif badge_name == 'Dedicated Scholar':
                badge = Badge(name='Dedicated Scholar', description='Reach Level 50', icon='fa-book-open', criteria_type='level', criteria_value=50)
            elif badge_name == 'Centurion':
                badge = Badge(name='Centurion', description='Reach Level 100', icon='fa-crown', criteria_type='level', criteria_value=100)
            else:
                return 
            db.session.add(badge)
            db.session.commit()
            
        if not UserBadge.query.filter_by(user_id=user.id, badge_id=badge.id).first():
            ub = UserBadge(user_id=user.id, badge_id=badge.id)
            db.session.add(ub)



class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='medium')
    due_date = db.Column(db.String(50))
    # Time specific fields
    due_time = db.Column(db.String(20), nullable=True) # HH:MM format
    is_notified = db.Column(db.Boolean, default=False)
    
    category = db.Column(db.String(50))
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    syllabus_id = db.Column(db.Integer, db.ForeignKey('syllabus_document.id'), nullable=True)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Could add color, icon, etc. later

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    # We only care about the DATE for the log
    completed_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    mode = db.Column(db.String(20), default='focus')  # focus, shortBreak, longBreak
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class TopicProficiency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    proficiency = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invite_code = db.Column(db.String(10), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)       # Optional group description
    avatar_emoji = db.Column(db.String(10), nullable=True, default='“š')  # Group icon emoji
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id], backref='owned_groups')
    members = db.relationship('GroupMember', backref='group', cascade='all, delete-orphan')
    messages = db.relationship('GroupChatMessage', backref='group', cascade='all, delete-orphan')

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # 'admin' or 'member'
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, nullable=True)  # For unread badge count

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
    )

    user = db.relationship('User', backref='group_memberships')

class GroupChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)  # Admin can pin announcements
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='group_messages')

class SyllabusDocument(db.Model):
    """PDF syllabus documents uploaded by users"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=True)  # Path to PDF file in filesystem
    extracted_text = db.Column(db.Text, nullable=True)  # AI Context
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    extraction_status = db.Column(db.String(20), default='pending')  # pending, success, failed
    is_active = db.Column(db.Boolean, default=True)  # For archiving
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='syllabus_documents')

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.String(50), nullable=False) # Format: YYYY-MM-DD
    time = db.Column(db.String(50), nullable=True)
    is_notified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminAction(db.Model):
    """Audit log for all admin actions"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # 'ban_user', 'delete_message', etc.
    target_type = db.Column(db.String(50))  # 'user', 'message', 'group', 'pdf'
    target_id = db.Column(db.Integer)
    details = db.Column(db.JSON)  # Additional context
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref='admin_actions')

class UserFeedback(db.Model):
    """
    UserFeedback Model - Quick feedback from users about the app
    Accessible from admin panel to understand user sentiment.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for anon
    rating = db.Column(db.String(10), nullable=False)  # Emoji: 'love','happy','neutral','sad','awful'
    message = db.Column(db.Text, nullable=True)  # Optional message
    category = db.Column(db.String(30), default='general')  # bug, feature, general
    page_url = db.Column(db.String(200), nullable=True)  # Which page they were on
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='feedbacks')

class ReferralReward(db.Model):
    """
    ReferralReward Model - Tracks completed referrals and rewards
    """
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who shared link
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Who signed up
    xp_awarded = db.Column(db.Integer, default=500)  # XP given to referrer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_made')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referral_from')

# ------------------------------
# Data Structures (DS) Utilities
# ------------------------------

class Stack:
    """Simple LIFO stack.

    Used for: Undo delete in Todos.
    """

    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        if not self._items:
            return None
        return self._items.pop()

    def is_empty(self):
        return len(self._items) == 0


class LRUCache:
    """LRU Cache using dict + list (simplified).

    DS concept:
    - Hash map (dict) for O(1) key lookup
    - List to track usage order for eviction
    """

    def __init__(self, capacity=50):
        self.capacity = capacity
        self.cache = {}
        self.order = []  # most recent at end

    def get(self, key):
        if key not in self.cache:
            return None
        if key in self.order:
            self.order.remove(key)
        self.order.append(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache[key] = value
            if key in self.order:
                self.order.remove(key)
            self.order.append(key)
            return

        if len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)
            del self.cache[oldest]

        self.cache[key] = value
        self.order.append(key)


# ------------------------------
# OOP Services
# ------------------------------

class AuthService:
    """Authentication service (OOP abstraction around auth logic)."""

    @staticmethod
    def create_user(email: str, password: str, first_name: str, last_name: str, referral_code: str = None) -> "User":
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already registered")

        # Validate names (server-side redundancy check)
        name_err = validate_name_field(first_name, 'First name')
        if name_err:
            raise ValueError(name_err)
        name_err = validate_name_field(last_name, 'Last name')
        if name_err:
            raise ValueError(name_err)

        import random, string
        def generate_ref_code():
            chars = string.ascii_uppercase + string.digits
            return ''.join(random.choices(chars, k=8))

        # Generate unique referral code for this new user
        ref_code = generate_ref_code()
        while User.query.filter_by(referral_code=ref_code).first():
            ref_code = generate_ref_code()

        # Find referrer if a code was provided
        referrer = None
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            referral_code=ref_code,
            referred_by=referrer.id if referrer else None
        )
        db.session.add(user)
        db.session.commit()

        # Award XP to BOTH referrer and new user
        if referrer:
            try:
                # Track the referral reward in DB
                reward = ReferralReward(
                    referrer_id=referrer.id,
                    referred_id=user.id,
                    xp_awarded=500  # Per person
                )
                db.session.add(reward)
                db.session.commit()

                # +500 XP to referrer (person who shared the link)
                GamificationService.add_xp(referrer.id, 'referral', 500)

                # +500 XP to new user (person who joined via the link)
                GamificationService.add_xp(user.id, 'referral_bonus', 500)

                # Commit all referral XP changes together
                db.session.commit()

            except Exception as e:
                print(f"Referral reward error: {e}")
                db.session.rollback()


        return user

    @staticmethod
    def authenticate(email: str, password: str):
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists
        if not user:
            return None
        
        # Check if user has a password (not a Google OAuth user)
        if not user.password_hash:
            # User signed up with Google OAuth, no password set
            return None
        
        # Verify password
        if check_password_hash(user.password_hash, password):
            return user
        
        return None


# Maximum groups a single user can be in simultaneously
GROUP_MEMBER_LIMIT = 5

class GroupService:
    """Group operations: create, join, leave, admin controls, membership checks."""

    @staticmethod
    def _generate_invite_code(length: int = 6) -> str:
        import random, string
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(random.choice(alphabet) for _ in range(length))

    # ”€”€ EMOJI POOL for auto-assigned group avatars ”€”€
    _EMOJI_POOL = ['“š', '§ ', '”¬', '“', '†', 'š¡', 'ŒŸ', '’¡', '”¥', '¯',
                   'š€', 'Œˆ', '¦‹', 'ŒŠ', '¨', '®', '§©', '”­', 'µ', '€']

    @staticmethod
    def create_group(admin_user_id: int, name: str, description: str = '') -> Group:
        """Create a new group. Raises ValueError if user already in 5 groups."""
        # Enforce 5-group limit
        current_count = GroupMember.query.filter_by(user_id=admin_user_id).count()
        if current_count >= GROUP_MEMBER_LIMIT:
            raise ValueError(f"You can only be in up to {GROUP_MEMBER_LIMIT} groups at a time.")

        invite_code = GroupService._generate_invite_code()
        while Group.query.filter_by(invite_code=invite_code).first() is not None:
            invite_code = GroupService._generate_invite_code()

        group = Group(
            name=name,
            admin_id=admin_user_id,
            invite_code=invite_code,
            description=description.strip() if description else '',
            avatar_emoji=''
        )
        db.session.add(group)
        db.session.commit()

        # Creator gets 'admin' role in membership
        db.session.add(GroupMember(group_id=group.id, user_id=admin_user_id, role='admin'))
        db.session.commit()
        return group

    @staticmethod
    def join_group(user_id: int, invite_code: str) -> Group:
        """Join a group by invite code. Raises ValueError on bad code or limit exceeded."""
        group = Group.query.filter_by(invite_code=invite_code).first()
        if not group:
            raise ValueError("Invalid invite code  double-check and try again.")

        # Already a member?
        existing = GroupMember.query.filter_by(group_id=group.id, user_id=user_id).first()
        if existing:
            return group  # Silently succeed (just navigate them there)

        # Enforce 5-group limit
        current_count = GroupMember.query.filter_by(user_id=user_id).count()
        if current_count >= GROUP_MEMBER_LIMIT:
            raise ValueError(f"You can only be in up to {GROUP_MEMBER_LIMIT} groups at a time. Leave one first.")

        db.session.add(GroupMember(group_id=group.id, user_id=user_id, role='member'))
        db.session.commit()
        return group

    @staticmethod
    def get_user_groups(user_id: int):
        """Return all Group objects the user is a member of, newest first."""
        memberships = (
            GroupMember.query
            .filter_by(user_id=user_id)
            .order_by(GroupMember.joined_at.desc())
            .all()
        )
        groups = []
        for m in memberships:
            g = Group.query.get(m.group_id)
            if g:
                groups.append(g)
        return groups

    @staticmethod
    def get_user_group(user_id: int):
        """Backward-compat: returns the most recent group or None."""
        groups = GroupService.get_user_groups(user_id)
        return groups[0] if groups else None

    @staticmethod
    def get_membership(group_id: int, user_id: int):
        """Return the GroupMember row or None."""
        return GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()

    @staticmethod
    def is_admin(group_id: int, user_id: int) -> bool:
        """Return True if the user is the admin of the group."""
        group = Group.query.get(group_id)
        return group is not None and group.admin_id == user_id

    @staticmethod
    def leave_group(group_id: int, user_id: int):
        """Remove user from group. If admin leaves and others remain, transfer admin. If last member, delete group."""
        group = Group.query.get(group_id)
        if not group:
            return

        membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
        if not membership:
            return

        db.session.delete(membership)
        db.session.commit()

        # Count remaining members
        remaining = GroupMember.query.filter_by(group_id=group_id).all()
        if not remaining:
            # No members left  delete the group entirely
            GroupChatMessage.query.filter_by(group_id=group_id).delete()
            db.session.delete(group)
            db.session.commit()
        elif group.admin_id == user_id:
            # Admin left but others remain  transfer admin to oldest remaining member
            oldest = min(remaining, key=lambda m: m.joined_at)
            group.admin_id = oldest.user_id
            oldest.role = 'admin'
            db.session.commit()

    @staticmethod
    def kick_member(group_id: int, admin_user_id: int, target_user_id: int):
        """Admin removes another member from the group."""
        if not GroupService.is_admin(group_id, admin_user_id):
            raise PermissionError("Only the group admin can kick members.")
        if admin_user_id == target_user_id:
            raise ValueError("You cannot kick yourself. Use Leave Group instead.")
        membership = GroupMember.query.filter_by(group_id=group_id, user_id=target_user_id).first()
        if not membership:
            raise ValueError("That user is not in this group.")
        db.session.delete(membership)
        db.session.commit()

    @staticmethod
    def rename_group(group_id: int, admin_user_id: int, new_name: str):
        """Admin renames the group."""
        if not GroupService.is_admin(group_id, admin_user_id):
            raise PermissionError("Only the group admin can rename the group.")
        new_name = new_name.strip()
        if not new_name or len(new_name) > 50:
            raise ValueError("Group name must be 1–50 characters.")
        if contains_profanity(new_name):
            raise ValueError("Group name contains inappropriate language. Please choose a respectful name.")
        group = Group.query.get(group_id)
        group.name = new_name
        db.session.commit()

    @staticmethod
    def delete_group(group_id: int, admin_user_id: int):
        """Admin permanently deletes the group and all its messages."""
        if not GroupService.is_admin(group_id, admin_user_id):
            raise PermissionError("Only the group admin can delete the group.")
        group = Group.query.get(group_id)
        if not group:
            return
        GroupChatMessage.query.filter_by(group_id=group_id).delete()
        GroupMember.query.filter_by(group_id=group_id).delete()
        db.session.delete(group)
        db.session.commit()

    @staticmethod
    def regen_invite_code(group_id: int, admin_user_id: int) -> str:
        """Admin regenerates the invite code, invalidating the old one."""
        if not GroupService.is_admin(group_id, admin_user_id):
            raise PermissionError("Only the group admin can regenerate the invite code.")
        new_code = GroupService._generate_invite_code()
        while Group.query.filter_by(invite_code=new_code).first() is not None:
            new_code = GroupService._generate_invite_code()
        group = Group.query.get(group_id)
        group.invite_code = new_code
        db.session.commit()
        return new_code

    @staticmethod
    def get_unread_count(group_id: int, user_id: int) -> int:
        """Count messages in this group since user last read (for unread badge)."""
        membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
        if not membership or not membership.last_read_at:
            return 0
        return GroupChatMessage.query.filter(
            GroupChatMessage.group_id == group_id,
            GroupChatMessage.created_at > membership.last_read_at,
            GroupChatMessage.user_id != user_id
        ).count()

    @staticmethod
    def mark_read(group_id: int, user_id: int):
        """Update last_read_at for this user in this group."""
        membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
        if membership:
            membership.last_read_at = datetime.utcnow()
            db.session.commit()

    @staticmethod
    def get_member_count(group_id: int) -> int:
        return GroupMember.query.filter_by(group_id=group_id).count()


class SyllabusService:
    """PDF syllabus upload + extraction and retrieval (simple)."""

    @staticmethod
    def save_syllabus(user_id: int, filename: str, extracted_text: str) -> SyllabusDocument:
        # existing = SyllabusDocument.query.filter_by(user_id=user_id).first()
        # if existing:
        #     db.session.delete(existing)
        #     db.session.commit()

        doc = SyllabusDocument(user_id=user_id, filename=filename, extracted_text=extracted_text)
        db.session.add(doc)
        db.session.commit()
        return doc

    @staticmethod
    def get_syllabus_text(user_id: int) -> str:
        doc = SyllabusDocument.query.filter_by(user_id=user_id).first()
        return doc.extracted_text if doc else ""

    @staticmethod
    def extract_tasks_from_pdf(pdf_bytes: bytes) -> list:
        # Use ALL rotator keys (AI_API_KEY_1 ... AI_API_KEY_N), not just the first one
        all_keys = gemini_rotator.keys if gemini_rotator.keys else ([AI_API_KEY] if AI_API_KEY else [])
        if not all_keys:
            raise ValueError("No AI API keys configured")

        model_id = os.environ.get("GEMINI_PDF_MODEL", "models/gemini-2.5-flash")
        base_endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/{model_id}:generateContent"
            if "/" in model_id else
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
        )

        prompt = (
            "You are a study assistant. Analyze the attached PDF notes. "
            "Identify the main chapters and key topics. "
            "Output ONLY valid JSON in this exact format: "
            "{\"tasks\": [{\"title\": \"Chapter Name\", \"subtasks\": [\"Topic 1\", \"Topic 2\"]}]}"
        )

        pdf_data = base64.b64encode(pdf_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "application/pdf",
                                "data": pdf_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }

        import time as _time

        response = None
        result_data = {}
        last_error = None

        # Try each key in the pool; rotate on 429/503
        for key_idx, api_key in enumerate(all_keys):
            endpoint = base_endpoint + f"?key={api_key}"
            key_label = f"key #{key_idx + 1}/{len(all_keys)}"
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=180
                )
                result_data = response.json() if response.text else {}

                if response.status_code in (429, 503):
                    error_msg = result_data.get("error", {}).get("message", "")
                    print(f"[PDF] {key_label} got {response.status_code}: {error_msg[:80]} — trying next key")
                    last_error = f"Google Error ({key_label}): {error_msg}"
                    _time.sleep(2)  # brief pause before next key
                    continue  # rotate to next key

                # Non-quota HTTP error
                if response.status_code != 200:
                    error_msg = result_data.get("error", {}).get("message", response.text or "Unknown error")
                    raise ValueError(f"Google Error: {error_msg}")

                if "error" in result_data:
                    raise ValueError(f"Google Error: {result_data['error'].get('message', 'Unknown API Error')}")

                print(f"[PDF] Success with {key_label}")
                break  # got a good response

            except requests.exceptions.Timeout:
                print(f"[PDF] {key_label} timed out — trying next key")
                last_error = f"Timeout on {key_label}"
                continue
        else:
            # All keys failed
            raise ValueError(last_error or "All API keys are overloaded. Please try again in a minute.")

        if response is None or response.status_code != 200:
            raise ValueError(last_error or "Could not reach Google AI. Please try again.")

        raw = ""
        if "candidates" in result_data and result_data["candidates"]:
            raw = result_data["candidates"][0]["content"]["parts"][0].get("text", "")
        if not raw:
            raise ValueError("AI could not read this PDF")

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].lstrip()

        parsed = None
        # Try to parse JSON with multiple fallback approaches
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            try:
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
        
        if parsed is None:
            raise ValueError("AI response could not be parsed as JSON. Please try again.")

        tasks = parsed.get("tasks", [])
        if not isinstance(tasks, list):
            raise ValueError("Invalid AI response: tasks is not a list")
        return tasks

    @staticmethod
    def build_chapters_from_todos(user_id: int, syllabus_id: int = None) -> list:
        query = Todo.query.filter_by(user_id=user_id, is_group=False)
        
        # If specific syllabus requested, filter by it
        if syllabus_id:
            query = query.filter_by(syllabus_id=syllabus_id)
        
        # If no syllabus ID, ideally we show tasks that are EITHER linked to active
        # OR linked to None (legacy), OR we just show everything?
        # User requested: "Active syllabus tasks no need to show completed course task"
        # Since we just migrated everything, we should enforce filtering if syllabus_id is passed.
        # If syllabus_id is None, maybe we just fetch ALL? 
        # But 'active' syllabus assumes the newest doc.
        
        todos = query.order_by(Todo.created_at.asc()).all()

        chapters = {}
        for t in todos:
            if not t.category:
                continue
            chapters.setdefault(t.category, []).append(t)

        result = []
        for category, items in chapters.items():
            total = len(items)
            completed = sum(1 for x in items if x.completed)
            percent = int((completed / total) * 100) if total else 0
            
            # Fetch proficiency for this chapter (category)
            prof_entry = TopicProficiency.query.filter_by(user_id=user_id, topic_name=category).first()
            proficiency = prof_entry.proficiency if prof_entry else 0
            
            result.append({
                'name': category,
                'todos': items,
                'total': total,
                'completed': completed,
                'percent': percent,
                'proficiency': proficiency
            })

        result.sort(key=lambda x: x['name'].lower())
        return result


# ------------------------------
# API HELPER (Fix for missing function)
# ------------------------------
def call_ai_api(messages):
    """
    Call Google Gemini API with automatic key rotation on quota exhaustion.
    messages: list of dicts [{'role': 'user', 'content': '...'}]
    Returns: str (response content)
    """
    if not gemini_rotator.available:
        raise ValueError("No Gemini API keys configured. Set AI_API_KEY_1, AI_API_KEY_2, etc. in environment.")

    conversation_history = ""
    for m in messages:
        role = "User" if m['role'] == 'user' else "Model"
        conversation_history += f"{role}: {m['content']}\n"

    # Limit context to last 3000 chars to stay within free-tier token limits
    final_prompt = conversation_history[-3000:]

    try:
        model_id = os.environ.get("GEMINI_MODEL", AI_MODEL)
        # Use rotator  automatically switches key on quota exhaustion
        response = gemini_rotator.generate_content(model_id, final_prompt)
        return response.text

    except Exception as e:
        print(f"[Gemini] call_ai_api failed: {e}")
        raise e


class ChatService:
    """Personal + group AI chat.

    Uses DS concept:
    - LRU cache to avoid repeated calls for same query.
    """

    _cache = LRUCache(capacity=100)

    @staticmethod
    def build_system_prompt(user: User, syllabus_text: str) -> str:
        base = (
            "You are StudyVerse, an expert AI Study Coach and academic mentor. "
            "Your goal is to help students learn effectively, stay motivated, and organize their studies.\n"
            "Guidelines:\n"
            "1. Be encouraging, structured, and clear. Use Markdown (bold, lists) for readability.\n"
            "2. The user has uploaded their syllabus/course material for REFERENCE. Do NOT generate solutions, summaries, or lessons from it unless the user EXPLICITLY asks.\n"
            "3. If the user says 'Hello' or similar, just greet them warmly and ask how you can help.\n"
            "4. Keep responses concise but helpful. Avoid long monologues unless necessary.\n"
            "5. Remember the context of the conversation."
        )
        if syllabus_text:
            base += "\n\n[REFERENCE MATERIAL - SYLLABUS/CONTENT]\n" + syllabus_text[:3000] + "\n[END REFERENCE MATERIAL]\n(Use the above material ONLY if the user asks about it.)"
        return base

    @staticmethod
    def generate_focus_plan(user: User) -> str:
        # Get pending tasks
        todos = Todo.query.filter_by(user_id=user.id, completed=False).limit(10).all()
        tasks_text = "\n".join([f"- {t.title} (Priority: {t.priority})" for t in todos])
        
        syllabus_text = SyllabusService.get_syllabus_text(user.id)
        
        prompt = (
            "You are a study coach. Based on the user's pending tasks and syllabus, "
            "create a short, actionable 3-step study plan for today. "
            "Format nicely with Markdown. Keep it encouraging.\n\n"
            f"Pending Tasks:\n{tasks_text}\n\n"
            f"Syllabus Context:\n{syllabus_text[:1000]}"
        )
        
        messages = [{'role': 'user', 'content': prompt}]
        return call_ai_api(messages)

    @staticmethod
    def generate_chat_response(user: User, message: str) -> str:
        # 1. Check Cache
        cached = ChatService._cache.get(message)
        if cached:
            return cached

        # 2. Get Context (Syllabus)
        syllabus_text = SyllabusService.get_syllabus_text(user.id)
        
        # 3. Build Prompt
        system_prompt = ChatService.build_system_prompt(user, syllabus_text)
        
        # We should ideally fetch recent chat history here for context window
        recent_chats = ChatMessage.query.filter_by(user_id=user.id, is_group=False).order_by(ChatMessage.created_at.desc()).limit(5).all()
        history = []
        for msg in reversed(recent_chats):
            history.append({'role': msg.role, 'content': msg.content})
            
        messages = history + [{'role': 'user', 'content': f"{system_prompt}\n\nUser Question: {message}"}]
        
        # 4. Call API
        try:
            response = call_ai_api(messages)
            # 5. Cache Result
            ChatService._cache.put(message, response)
            return response
        except Exception as e:
            return f"I'm having trouble connecting to my brain right now. Please try again later. (Error: {str(e)})"
            
    @staticmethod
    def personal_reply(user: User, message: str) -> str:
        """Wrapper for generate_chat_response for backward compatibility / keeping naming consistent in routes"""
        return ChatService.generate_chat_response(user, message)

# ============================================================================
# PWA ROUTES (Progressive Web App Support)
# ============================================================================

@app.route('/sw.js')
def service_worker():
    """Serve the Service Worker script from static/ with correct MIME type and scope header."""
    from flask import send_from_directory, make_response
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route('/offline')
def offline():
    """Offline fallback page shown by the Service Worker when network is unavailable."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudyVerse — Offline</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 20px;
        }
        .container { max-width: 400px; }
        .icon { font-size: 4rem; margin-bottom: 24px; }
        h1 { font-size: 1.8rem; font-weight: 700; margin-bottom: 12px; color: #0ea5e9; }
        p { color: #94a3b8; font-size: 1rem; line-height: 1.6; margin-bottom: 28px; }
        .btn {
            background: linear-gradient(135deg, #0ea5e9, #6366f1);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📚</div>
        <h1>You\'re Offline</h1>
        <p>No internet connection detected. Please reconnect to continue your study session on StudyVerse.</p>
        <a href="/dashboard" class="btn">Try Again</a>
    </div>
</body>
</html>''', 200, {'Content-Type': 'text/html'}


@app.route('/api/ai/plan', methods=['GET'])
@login_required
def ai_plan():
    try:
        plan = ChatService.generate_focus_plan(current_user)
        return jsonify({'status': 'success', 'plan': plan})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




# Routes
@app.route('/')
def index():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
    except:
        pass
    return render_template('landing.html')

@app.route('/auth')
def auth():
    # Check if user is authenticated
    if current_user.is_authenticated:
        print(f"Auth Check: User {current_user.id} is authenticated. Redirecting to dashboard.")
        return redirect(url_for('dashboard'))
    return render_template('auth.html')

@app.route('/guidelines')
def community_guidelines():
    """Public community guidelines page — no login required."""
    return render_template('guidelines.html')

@app.route('/signup', methods=['POST'])
def signup():
    """Create account using standard HTML form POST (no JSON)."""
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    referral_code = (
        request.form.get('ref', '').strip()
        or request.args.get('ref', '').strip()
        or session.pop('ref_code', None)  # Set by /invite/<code> redirect
        or ''
    )

    # ”€”€ 1. Basic required field check ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    if not email or not password:
        flash('Email and password are required.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 2. Name Validation ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    name_err = validate_name_field(first_name, 'First name')
    if name_err:
        flash(name_err, 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    name_err = validate_name_field(last_name, 'Last name')
    if name_err:
        flash(name_err, 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 3. Email Format Validation ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    email_regex = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        flash('Please enter a valid email address.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 4. Disposable / Fake Domain Blocklist ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    if is_blocked_email_domain(email):
        flash('Disposable or temporary email addresses are not allowed. Please use your real email.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 5. DNS MX Record Check  verify the email domain actually exists ”€”€”€”€”€”€”€
    if not email_domain_has_mx(email):
        flash('This email domain does not appear to exist or cannot receive emails. Please use a real email address.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 6. Password Strength Validation ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    if not re.search(r"[A-Z]", password):
        flash('Password must contain at least one uppercase letter.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    if not re.search(r"[0-9]", password):
        flash('Password must contain at least one number.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        flash('Password must contain at least one special character (!@#$%^&*).', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # ”€”€ 7. Check if email OR full name already exists ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    if User.query.filter_by(email=email).first():
        flash('Email is already registered. Please sign in.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # Prevent duplicate full names (same first + last name already in DB)
    duplicate_name = User.query.filter(
        db.func.lower(User.first_name) == first_name.lower(),
        db.func.lower(User.last_name)  == last_name.lower()
    ).first()
    if duplicate_name:
        flash(f'A user named "{first_name} {last_name}" already exists. Please use a different name or contact support if this is you.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)


    # ”€”€ 8. Generate OTP & Send Email ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    import random
    otp_code = str(random.randint(100000, 999999))
    
    # Store registration data temporarily in the session
    session['signup_data'] = {
        'email': email,
        'password': password,
        'first_name': first_name,
        'last_name': last_name,
        'referral_code': referral_code,
        'otp': otp_code,
        'otp_time': datetime.utcnow().timestamp()
    }

    # Send OTP
    success = send_otp_email(email, otp_code, first_name)
    if not success:
        session.pop('signup_data', None)
        flash('Failed to send verification email. Please try again later or check if the email is valid.', 'error')
        return render_template('auth.html', active_tab='signup', form_data=request.form)

    # Redirect to the page where they enter the 6-digit code
    return redirect(url_for('verify_otp'))

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Route where users enter the 6-digit OTP sent to their email."""
    signup_data = session.get('signup_data')
    if not signup_data:
        flash('Session expired or no signup in progress. Please sign up again.', 'error')
        return redirect(url_for('auth'))

    if request.method == 'POST':
        user_otp = request.form.get('otp', '').strip()
        
        # Check expiry (10 minutes = 600 seconds)
        otp_time = signup_data.get('otp_time', 0)
        current_time = datetime.utcnow().timestamp()
        
        if current_time - otp_time > 600:
            session.pop('signup_data', None)
            flash('Verification code expired (10 minutes). Please sign up again.', 'error')
            return redirect(url_for('auth'))
            
        # Check if code matches
        if user_otp != signup_data.get('otp'):
            flash('Invalid verification code. Please try again.', 'error')
            return render_template('otp_verify.html', email=signup_data.get('email'))
            
        # Success! Create the user in the database
        try:
            user = AuthService.create_user(
                signup_data['email'], 
                signup_data['password'], 
                signup_data['first_name'], 
                signup_data['last_name'], 
                referral_code=signup_data.get('referral_code') or None
            )
            
            # Clear session data now that we are done
            session.pop('signup_data', None)
            
            # Log in the user
            login_user(user, remember=True)
            session.permanent = True
            
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('auth'))

    # GET request  just show the form
    return render_template('otp_verify.html', email=signup_data.get('email'))

@app.route('/signin', methods=['POST'])
def signin():
    """Sign in using standard HTML form POST (no JSON)."""
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    # Check if user exists first
    user = User.query.filter_by(email=email).first()
    
    if user and not user.password_hash:
        # User signed up with Google OAuth
        flash('This account was created with Google Sign-In. Please use the "Sign in with Google" button.', 'error')
        return redirect(url_for('auth'))
    
    # Authenticate with password
    user = AuthService.authenticate(email, password)
    if not user:
        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth'))

    login_user(user, remember=True)  # Enable remember me for persistent sessions
    session.permanent = True
    


    return redirect(url_for('dashboard'))

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    print(f"Logging out user: {current_user.id}")
    # Set last_seen to past to ensure immediate offline status
    try:
        current_user.last_seen = datetime.utcnow() - timedelta(minutes=15)
        db.session.commit()
    except:
        pass
        
    logout_user()
    session.clear()
    
    # Create response to clear cookies explicitly
    response = redirect(url_for('auth'))
    
    # Clear Flask-Login 'remember me' cookie
    cookie_name = app.config.get('REMEMBER_COOKIE_NAME', 'remember_token')
    response.delete_cookie(cookie_name)
    
    # Clear session cookie
    response.delete_cookie('session')
    
    flash('You have been logged out.', 'success')
    return response

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    print(f"[GOOGLE AUTH] Initiating OAuth flow")
    print(f"[GOOGLE AUTH] Redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    print(f"[GOOGLE AUTH] Callback received")
    print(f"[GOOGLE AUTH] Request args: {request.args}")
    try:
        print(f"[GOOGLE AUTH] Attempting to authorize access token...")
        token = google.authorize_access_token()
        print(f"[GOOGLE AUTH] Token received successfully")
        user_info = google.parse_id_token(token, nonce=None)
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        name = user_info.get('name', '')
        picture = user_info.get('picture')

        # Check if user exists
        user = User.query.filter_by(email=email).first()
        is_new_user = False

        if not user:
            is_new_user = True
            # Create new user
            names = name.split(' ', 1) if name else ['', '']
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else ''
            
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                google_id=google_id,
                profile_image=picture,
                password_hash=None # No password for Google users
            )
            db.session.add(user)
            db.session.commit()
            
            # Email functionality removed
        else:
            # Update existing user info
            if not user.google_id:
                user.google_id = google_id
            if picture:
                user.profile_image = picture
            db.session.commit()

        # Log the user in
        login_user(user, remember=True)
        session.permanent = True
        
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=" * 80)
        print(f"ERROR during Google Auth:")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"Full Traceback:")
        print(error_details)
        print(f"=" * 80)
        flash(f"Google authentication failed: {str(e)}", "error")
        return redirect(url_for('auth'))

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Handle Google OAuth sign-in from Firebase."""
    import uuid
    
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    email = data.get('email')
    display_name = data.get('displayName', '')
    
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400
    
    # Check if user exists
    user = User.query.filter_by(email=email).first()
    is_new_user = False
    
    if not user:
        is_new_user = True
        # Create new user from Google account
        names = display_name.split(' ', 1) if display_name else ['', '']
        first_name = names[0] if names else ''
        last_name = names[1] if len(names) > 1 else ''
        
        user = User(
            email=email,
            password_hash=generate_password_hash(str(uuid.uuid4())),  # Random password for OAuth users
            first_name=first_name,
            last_name=last_name
        )
        db.session.add(user)
        db.session.commit()
        
        # Email functionality removed
    
    # Log in the user
    login_user(user, remember=True)
    session.permanent = True
    
    return jsonify({'status': 'success', 'message': 'Authentication successful'})



# ============================================================================
# LANDING PAGE (Public Homepage)
# ============================================================================

@app.route('/')
def landing():
    """
    Public landing page - shown to visitors who are not logged in.
    Showcases StudyVerse features and encourages sign-up.
    """
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    return render_template('landing.html')

# ============================================================================
# ADMIN PANEL - Decorator and Service
# ============================================================================

def admin_required(f):
    """Decorator to require admin access for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth'))
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# ONLINE USERS TRACKER - In-memory set of currently connected user IDs
# ============================================================================

# Tracks user IDs currently active (updated on every request, cleared on logout)
# Uses a simple set for O(1) add/remove/lookup  resets on server restart (ephemeral by design)
online_users = set()

# How many minutes of inactivity before a user is considered "offline"
ONLINE_THRESHOLD_MINUTES = 5

# ============================================================================
# BAN CHECK + LAST SEEN MIDDLEWARE
# ============================================================================

@app.before_request
def check_ban_status():
    """
    Runs on EVERY request:
    1. Updates user's last_seen timestamp (powers the admin activity tracker)
    2. Adds user to the in-memory online_users set
    3. Checks if user is banned †’ logs them out immediately if so
    """
    # Skip for static files and auth routes to avoid unnecessary DB hits
    if request.endpoint and (request.endpoint.startswith('static') or request.endpoint == 'auth'):
        return None

    if current_user.is_authenticated:
        # Reload user from DB to get the freshest ban status
        user = User.query.get(current_user.id)

        if user and user.is_banned:
            from flask_login import logout_user
            logout_user()
            flash(f'Your account has been banned. Reason: {user.ban_reason or "Violation of terms"}', 'error')
            return redirect(url_for('auth'))

        # ”€”€ Update last_seen + online set ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
        if user:
            try:
                user.last_seen = datetime.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()
            online_users.add(current_user.id)

    return None

class AdminService:
    """Admin operations and utilities"""
    
    @staticmethod
    def log_action(admin_id, action, target_type=None, target_id=None, details=None):
        """Log admin action for audit trail"""
        log = AdminAction(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        # Note: caller is responsible for committing
    
    @staticmethod
    def get_dashboard_stats():
        """Get statistics for admin dashboard"""
        total_users = User.query.count()
        active_users = User.query.filter(
            User.last_seen >= datetime.utcnow() - timedelta(days=7)
        ).count()
        total_pdfs = SyllabusDocument.query.count()
        total_groups = Group.query.count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_pdfs': total_pdfs,
            'total_groups': total_groups
        }
    
    @staticmethod
    def ban_user(user_id, reason, admin_id):
        """Ban a user"""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_banned = True
        user.ban_reason = reason
        user.banned_at = datetime.utcnow()
        user.banned_by = admin_id
        
        db.session.commit()
        
        AdminService.log_action(
            admin_id=admin_id,
            action='ban_user',
            target_type='user',
            target_id=user_id,
            details={'reason': reason}
        )
    
    @staticmethod
    def unban_user(user_id, admin_id):
        """Unban a user"""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.is_banned = False
        user.ban_reason = None
        user.banned_at = None
        user.banned_by = None
        
        db.session.commit()
        
        AdminService.log_action(
            admin_id=admin_id,
            action='unban_user',
            target_type='user',
            target_id=user_id
        )

    @staticmethod
    def delete_user(user_id, admin_id):
        """Permanently delete a user and all associated data"""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # 1. Habits (delete logs first)
        habits = Habit.query.filter_by(user_id=user_id).all()
        for habit in habits:
            HabitLog.query.filter_by(habit_id=habit.id).delete()
        Habit.query.filter_by(user_id=user_id).delete()
        
        # 2. Support Tickets (delete messages first)
        tickets = SupportTicket.query.filter_by(user_id=user_id).all()
        for ticket in tickets:
            SupportMessage.query.filter_by(ticket_id=ticket.id).delete()
            db.session.delete(ticket)
            
        # 3. Groups where user is admin (delete messages and members first)
        groups = Group.query.filter_by(admin_id=user_id).all()
        for group in groups:
            GroupMember.query.filter_by(group_id=group.id).delete()
            GroupChatMessage.query.filter_by(group_id=group.id).delete()
            db.session.delete(group)

        # 4. Standard one-to-many dependencies
        Todo.query.filter_by(user_id=user_id).delete()
        ChatMessage.query.filter_by(user_id=user_id).delete()
        StudySession.query.filter_by(user_id=user_id).delete()
        TopicProficiency.query.filter_by(user_id=user_id).delete()
        Event.query.filter_by(user_id=user_id).delete()
        SyllabusDocument.query.filter_by(user_id=user_id).delete()
        XPHistory.query.filter_by(user_id=user_id).delete()
        UserItem.query.filter_by(user_id=user_id).delete()
        ActivePowerUp.query.filter_by(user_id=user_id).delete()
        UserBadge.query.filter_by(user_id=user_id).delete()
        GroupMember.query.filter_by(user_id=user_id).delete()
        GroupChatMessage.query.filter_by(user_id=user_id).delete()
        UserFeedback.query.filter_by(user_id=user_id).delete()
        StudyStream.query.filter_by(user_id=user_id).delete()
        
        # 5. Many-to-many & other relationships
        Friendship.query.filter(db.or_(Friendship.user_id==user_id, Friendship.friend_id==user_id)).delete()
        ReferralReward.query.filter(db.or_(ReferralReward.referrer_id==user_id, ReferralReward.referred_id==user_id)).delete()
        AdminAction.query.filter_by(target_id=user_id, target_type='user').delete()
        
        # 6. Delete User
        db.session.delete(user)
        db.session.commit()
        
        # Log action after commit
        AdminService.log_action(
            admin_id=admin_id,
            action='delete_user',
            target_type='user',
            target_id=user_id
        )

class SupportService:
    """Service for handling support tickets and messages"""
    
    @staticmethod
    def create_ticket(user_id, subject, message, category='general', priority='normal'):
        """Create a new support ticket"""
        # Create ticket
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            category=category,
            priority=priority,
            status='open',
            user_unread_count=0,
            admin_unread_count=1  # Admin has 1 unread message
        )
        db.session.add(ticket)
        db.session.commit()
        
        # Create initial message
        msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=user_id,
            message=message,
            is_admin=False,
            read_by_user=True,
            read_by_admin=False
        )
        db.session.add(msg)
        db.session.commit()
        return ticket
    
    @staticmethod
    def send_admin_notification(user_id, admin_id, subject, message, category='system'):
        """Create a notification ticket from admin to user"""
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            category=category,
            priority='normal',
            status='open',  # 'open' so it shows prominently in inbox with green highlight
            user_unread_count=1,
            admin_unread_count=0
        )
        db.session.add(ticket)
        db.session.flush()  # Get ticket.id

        # Create initial message from Admin
        msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=admin_id,
            message=message,
            is_admin=True,
            read_by_user=False,
            read_by_admin=True
        )
        db.session.add(msg)
        db.session.commit()  # ← Persist to DB

        return ticket
    
    @staticmethod
    def add_message(ticket_id, sender_id, message, is_admin=False):
        """Add a message to an existing ticket"""
        ticket = SupportTicket.query.get(ticket_id)
        if not ticket:
            return None
            
        # Add message
        msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=sender_id,
            message=message,
            is_admin=is_admin,
            read_by_user=True, # Sender always reads their own message
            read_by_admin=True # Sender always reads their own message
        )
        
        # Override read status based on recipient
        if is_admin:
            # Admin sent it -> Admin read it (already True), User hasn't read it
            msg.read_by_user = False
            ticket.status = 'in_progress' # Admin replied
            ticket.user_unread_count += 1
            ticket.admin_unread_count = 0 # Admin read everything to reply (usually)
        else:
            # User sent it -> User read it (already True), Admin hasn't read it
            msg.read_by_admin = False
            ticket.status = 'open' # User replied, waiting for admin
            ticket.admin_unread_count += 1
            ticket.user_unread_count = 0 # User read everything to reply (usually)
            
        db.session.add(msg)
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        return msg

    @staticmethod
    def get_user_tickets(user_id):
        """Get all tickets for a user"""
        return SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.updated_at.desc()).all()
        
    @staticmethod
    def get_admin_tickets(status_filter=None, category_filter=None):
        """Get all tickets for admin panel"""
        query = SupportTicket.query
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)
        if category_filter:
            query = query.filter_by(category=category_filter)
        return query.order_by(SupportTicket.updated_at.desc()).all()


# ============================================================================
# CONTEXT PROCESSORS (Inject data into all templates)
# ============================================================================
@app.context_processor
def inject_support_notifications():
    unread_support = 0
    if current_user.is_authenticated:
        try:
            if current_user.is_admin:
                # Total unread tickets for admin
                # Count tickets where admin has unread messages
                unread_support = SupportTicket.query.filter(
                    SupportTicket.status.in_(['open', 'in_progress']),
                    SupportTicket.admin_unread_count > 0
                ).count()
            else:
                # Total unread tickets for user
                unread_support = SupportTicket.query.filter(
                    SupportTicket.user_id == current_user.id,
                    SupportTicket.user_unread_count > 0
                ).count()
        except:
            pass # Handle case where tables don't exist yet
            
    return dict(unread_support_count=unread_support)

# ============================================================================
# DASHBOARD (Main App Interface)
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect admins to admin panel
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    # Dashboard logic starts here
    total_todos = Todo.query.filter_by(user_id=current_user.id).count()
    completed_todos = Todo.query.filter_by(user_id=current_user.id, completed=True).count()
    remaining_todos = max(total_todos - completed_todos, 0)

    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_minutes = (
        db.session.query(db.func.coalesce(db.func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == current_user.id)
        .filter(StudySession.completed_at >= week_ago)
        .scalar()
    )
    weekly_hours = round((weekly_minutes or 0) / 60.0, 1)

    completion_percent = int((completed_todos / total_todos) * 100) if total_todos else 0

    topic_rows = (
        TopicProficiency.query
        .filter_by(user_id=current_user.id)
        .order_by(TopicProficiency.updated_at.desc())
        .limit(6)
        .all()
    )
    avg_proficiency = (
        db.session.query(db.func.coalesce(db.func.avg(TopicProficiency.proficiency), 0))
        .filter(TopicProficiency.user_id == current_user.id)
        .scalar()
    )
    avg_proficiency = int(round(avg_proficiency or 0))
    topics_covered = TopicProficiency.query.filter_by(user_id=current_user.id).count()

    recent_todos = (
        Todo.query
        .filter_by(user_id=current_user.id)
        .order_by(Todo.created_at.desc())
        .limit(5)
        .all()
    )
    upcoming_todos = (
        Todo.query
        .filter_by(user_id=current_user.id, completed=False)
        .order_by(Todo.id.desc())
        .limit(5)
        .all()
    )

    # -------------------------
    # COMPLETED PARENT TASKS
    # (Categories where every subtask is done)
    # -------------------------
    all_user_todos = Todo.query.filter_by(user_id=current_user.id).all()
    cat_map = {}
    for t in all_user_todos:
        cat = t.category if (t.category and t.category.strip()) else None
        if not cat: continue
        if cat not in cat_map:
            cat_map[cat] = []
        cat_map[cat].append(t)
    
    completed_parent_tasks = []
    today_utc = datetime.utcnow()
    start_of_week = today_utc - timedelta(days=today_utc.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    for cat, tasks in cat_map.items():
        if all(tk.completed for tk in tasks):
            # Check if at least one was completed this week
            # Or if it's a recently finished project
            recent_completion = any(tk.completed_at and tk.completed_at >= start_of_week for tk in tasks)
            if recent_completion:
                completed_parent_tasks.append(cat)

    # -------------------------
    # WEEKLY COMPLETED EVENTS
    # -------------------------
    today_date = datetime.utcnow().date()
    start_of_week_date = today_date - timedelta(days=today_date.weekday())
    week_date_strs = [(start_of_week_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    completed_events_week = (
        Event.query
        .filter_by(user_id=current_user.id, is_notified=True)
        .filter(Event.date.in_(week_date_strs))
        .order_by(Event.date.desc(), Event.time.desc())
        .all()
    )
    
    
    # Count online users (active in last 5 minutes)
    online_threshold = datetime.utcnow() - timedelta(minutes=5)
    online_users = User.query.filter(User.last_seen >= online_threshold).count()
    # Add at least 1 for current user
    if online_users < 1:
        online_users = 1
    
    # Daily Quests (simple example quests based on user activity)
    quests = []
    # Quest 1: Complete 3 tasks today
    today_completed = Todo.query.filter_by(user_id=current_user.id, completed=True).filter(
        db.func.date(Todo.created_at) == datetime.utcnow().date()
    ).count()
    quests.append({
        'description': 'Complete 3 tasks',
        'icon': 'fa-check-circle',
        'xp_reward': 50,
        'progress': min(today_completed, 3),
        'target': 3,
        'completed': today_completed >= 3
    })
    
    # Quest 2: Study for 30 minutes
    today_study_mins = (
        db.session.query(db.func.coalesce(db.func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == current_user.id)
        .filter(db.func.date(StudySession.completed_at) == datetime.utcnow().date())
        .scalar()
    ) or 0
    quests.append({
        'description': 'Study for 30 minutes',
        'icon': 'fa-clock',
        'xp_reward': 75,
        'progress': min(today_study_mins, 30),
        'target': 30,
        'completed': today_study_mins >= 30
    })
    
    # Quest 3: Log in daily (always complete if you're seeing this)
    # Quest 3: Log in daily (always complete if you're seeing this)
    quests.append({
        'description': 'Log in today',
        'icon': 'fa-door-open',
        'xp_reward': 25,
        'progress': 1,
        'target': 1,
        'completed': True
    })

    # -------------------------
    # WEEKLY STATS CALCULATION
    # -------------------------
    today = datetime.utcnow().date()
    # Align to current week (Monday - Sunday)
    start_of_week = today - timedelta(days=today.weekday()) 
    dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    daily_stats = []
    total_focus_week = 0
    total_tasks_week = 0
    total_goals_week = 0 
    
    for d in dates:
        # 1. Daily Focus Mins
        d_focus = db.session.query(db.func.sum(StudySession.duration)).filter(
            StudySession.user_id == current_user.id,
            db.func.date(StudySession.completed_at) == d
        ).scalar() or 0
        
        # 2. Daily Tasks Completed (Using real completed_at)
        d_tasks = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.completed == True,
            db.func.date(Todo.completed_at) == d
        ).count()
        
        # 3. Daily Goals (High Priority Completed)
        d_goals = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.completed == True,
            Todo.priority == 'high',
            db.func.date(Todo.completed_at) == d
        ).count()
        
        total_focus_week += d_focus
        total_tasks_week += d_tasks
        total_goals_week += d_goals
        
        # Normalize for chart (Max 4 hours focus = 100%, Max 5 tasks = 100%)
        focus_pct = min((d_focus / 240) * 100, 100) # 4 hours max bar
        task_pct = min((d_tasks / 5) * 100, 100)    # 5 tasks max bar
        
        daily_stats.append({
            'day': d.strftime('%a'),
            'focus_pct': int(focus_pct),
            'task_pct': int(task_pct),
            'focus_mins': d_focus,
            'task_count': d_tasks
        })

    weekly_stats = {
        'total_focus': total_focus_week,
        'total_tasks': total_tasks_week,
        'total_goals': total_goals_week,
        'chart': daily_stats
    }

    # -------------------------
    # HABIT TRACKER DATA
    # -------------------------
    # Get all active habits
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Get logged habits for today
    today_logs = HabitLog.query.filter(
        HabitLog.habit_id.in_([h.id for h in habits]),
        HabitLog.completed_date == datetime.utcnow().date()
    ).all()
    today_log_ids = {log.habit_id for log in today_logs}

    # Calculate Weekly Progress (Mon-Sun) - Habit Completion %
    habit_chart = []
    total_habits_count = len(habits)
    
    # -------------------------
    # IMPORTANT ITEMS (For Important Card)
    # -------------------------
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime('%Y-%m-%d')
    time_str = now_ist.strftime('%H:%M')

    # Next event today or in the future
    # Handle NULL time by assuming it's an all-day event (so '00:00')
    important_event = Event.query.filter(
        Event.user_id == current_user.id,
        Event.date >= today_str
    ).filter(
        # Logic: If date > today, any time is fine. If date == today, time must be >= now OR null (all day)
        db.or_(
            Event.date > today_str,
            db.and_(Event.date == today_str, db.or_(Event.time >= time_str, Event.time == None, Event.time == ''))
        )
    ).order_by(Event.date.asc(), Event.time.asc()).first()

    # High priority uncompleted task
    important_todo = Todo.query.filter_by(
        user_id=current_user.id,
        completed=False,
        priority='high'
    ).order_by(Todo.id.desc()).first()

    important_todo_label = "High Priority Task"
    
    # Fallback: If no high priority task, show next due task
    if not important_todo:
        important_todo = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.completed == False,
            Todo.due_date != None,
            Todo.due_date >= today_str
        ).order_by(Todo.due_date.asc()).first()
        
        if important_todo:
            important_todo_label = "Upcoming Task"

    return render_template(
        'dashboard.html',
        total_todos=total_todos,
        completed_todos=completed_todos,
        remaining_todos=remaining_todos,
        weekly_hours=weekly_hours,
        completion_percent=completion_percent,
        avg_proficiency=avg_proficiency,
        topics_covered=topics_covered,
        topic_rows=topic_rows,
        recent_todos=recent_todos,
        upcoming_todos=upcoming_todos,
        online_users=online_users,
        quests=quests,
        today_study_mins=today_study_mins,
        weekly_stats=weekly_stats,
        habits=habits,
        today_log_ids=today_log_ids,
        habit_chart=habit_chart,
        completed_parent_tasks=completed_parent_tasks,
        completed_events_week=completed_events_week,
        important_event=important_event,
        important_todo=important_todo,
        important_todo_label=important_todo_label
    )

@app.route('/chat')
@login_required
def chat():
    messages = ChatMessage.query.filter_by(user_id=current_user.id, is_group=False).order_by(ChatMessage.created_at.asc()).limit(50).all()
    return render_template('chat.html', chat_messages=messages)

@app.route('/chat/send', methods=['POST'])
@login_required
def chat_send():
    """Personal chat send (AJAX supported)."""
    
    # Handle JSON (AJAX)
    if request.is_json:
        data = request.get_json()
        content = data.get('message', '').strip()
        if not content:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
            
        # Store user message
        user_msg = ChatMessage(user_id=current_user.id, role='user', content=content, is_group=False)
        db.session.add(user_msg)
        db.session.commit()

        # Generate AI response (Context Aware)
        reply = ChatService.generate_chat_response(current_user, content)
        
        # Store AI response
        ai_msg = ChatMessage(user_id=current_user.id, role='assistant', content=reply, is_group=False)
        db.session.add(ai_msg)
        db.session.commit()
        
        # Return response with IST timestamps
        return jsonify({
            'status': 'success',
            'reply': reply,
            'user_timestamp': to_ist_time(user_msg.created_at),
            'ai_timestamp': to_ist_time(ai_msg.created_at)
        })


    # Legacy Form Post
    content = request.form.get('message', '').strip()
    if not content:
        return redirect(url_for('chat'))

    # Store user message
    db.session.add(ChatMessage(user_id=current_user.id, role='user', content=content, is_group=False))
    db.session.commit()

    db.session.commit()

    # Generate AI response
    reply = ChatService.personal_reply(current_user, content)
    db.session.add(ChatMessage(user_id=current_user.id, role='assistant', content=reply, is_group=False))
    db.session.commit()

    return redirect(url_for('chat'))

# ----------------------------------------------------
# CLEAR AI COACH CHAT HISTORY
# ----------------------------------------------------
@app.route('/chat/clear', methods=['POST'])
@login_required
def chat_clear():
    """Delete all personal AI Coach messages for the current user."""
    try:
        ChatMessage.query.filter_by(user_id=current_user.id, is_group=False).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Chat history cleared.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ----------------------------------------------------
# BAN APPEAL (public — no login required)
# ----------------------------------------------------
@app.route('/appeal', methods=['POST'])
def submit_appeal():
    """
    Public endpoint — banned users submit an unban appeal.
    No login required. Looks up user by email, verifies ban,
    then creates a high-priority 'ban_appeal' support ticket.
    """
    email   = (request.form.get('email', '') or '').strip().lower()
    reason  = (request.form.get('reason', '') or '').strip()

    if not email or not reason:
        return jsonify({'ok': False, 'msg': 'Email and appeal message are required.'}), 400
    if len(reason) < 20:
        return jsonify({'ok': False, 'msg': 'Please write a more detailed appeal (at least 20 characters).'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal whether the email exists — generic message
        return jsonify({'ok': True, 'msg': 'If an account with that email exists, your appeal has been submitted.'})
    if not user.is_banned:
        return jsonify({'ok': False, 'msg': 'This account is not currently banned.'}), 400

    # Check for duplicate open appeal
    existing = SupportTicket.query.filter_by(
        user_id=user.id, category='ban_appeal', status='open'
    ).first()
    if existing:
        return jsonify({'ok': False, 'msg': 'You already have an open ban appeal (#{}). Please wait for admin review.'.format(existing.id)}), 400

    ban_info = ''
    if user.ban_reason:
        ban_info = f'\n\n📋 Ban reason on record: "{user.ban_reason}"'

    ticket = SupportTicket(
        user_id=user.id,
        subject='🚫 Ban Appeal — ' + user.first_name + ' ' + user.last_name,
        category='ban_appeal',
        priority='high',
        status='open',
        user_unread_count=0,
        admin_unread_count=1
    )
    db.session.add(ticket)
    db.session.flush()

    msg = SupportMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        message=(
            f'📧 Appeal submitted from: {email}\n\n'
            f'📝 User\'s appeal:\n{reason}'
            f'{ban_info}'
        ),
        is_admin=False,
        read_by_user=True,
        read_by_admin=False
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({'ok': True, 'msg': f'Your appeal has been submitted (Ticket #{ticket.id}). The admin will review it and respond. Please check back after logging in once unbanned.'})


# ----------------------------------------------------
# USER SUPPORT CENTER
# ----------------------------------------------------
@app.route('/support')
@login_required
def support():
    """User support dashboard"""
    # Create support/list.html template later
    tickets = SupportService.get_user_tickets(current_user.id)
    return render_template('support/list.html', tickets=tickets)

@app.route('/support/create', methods=['POST'])
@login_required
def support_create():
    """Create a new support ticket"""
    subject = request.form.get('subject')
    message = request.form.get('message')
    # Default category to 'general' if not provided
    category = request.form.get('category', 'general') 
    priority = request.form.get('priority', 'normal')
    
    if not subject or not message:
        flash('Subject and message are required', 'error')
        return redirect(url_for('support'))
        
    ticket = SupportService.create_ticket(current_user.id, subject, message, category, priority)
    flash('Ticket created successfully! Support team will respond shortly.', 'success')
    return redirect(url_for('support_detail', ticket_id=ticket.id))

@app.route('/support/<int:ticket_id>')
@login_required
def support_detail(ticket_id):
    """View support ticket details"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Security check: User can only view their own tickets
    if ticket.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized access', 'error')
        return redirect(url_for('support'))
        
    # Mark messages as read if viewed by user
    if not current_user.is_admin:
        unread_msgs = SupportMessage.query.filter_by(
            ticket_id=ticket.id, 
            read_by_user=False,
            is_admin=True # Messages from admin
        ).all()
        for msg in unread_msgs:
            msg.read_by_user = True
        
        if unread_msgs:
            ticket.user_unread_count = 0
            db.session.commit()

    messages = SupportMessage.query.filter_by(ticket_id=ticket.id).order_by(SupportMessage.created_at.asc()).all()
    return render_template('support/detail.html', ticket=ticket, messages=messages)

@app.route('/support/<int:ticket_id>/reply', methods=['POST'])
@login_required
def support_reply(ticket_id):
    """User replies to a support ticket"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Security check: User can only reply to their own tickets
    if ticket.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('support'))
        
    message = request.form.get('message')
    if not message:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('support_detail', ticket_id=ticket_id))
        
    SupportService.add_message(ticket_id, current_user.id, message, is_admin=False)
    # flash('Reply sent!', 'success') # Optional, chat interface usually doesn't need flash
    return redirect(url_for('support_detail', ticket_id=ticket_id))

# ----------------------------------------------------
# XP SHOP / GAMIFICATION STORE
# ----------------------------------------------------
class UserItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.String(50), nullable=False) # e.g., 'theme_cyberpunk'
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False) # For themes/frames that need activation

class ActivePowerUp(db.Model):
    """Track active power-ups with duration and effects"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    power_up_id = db.Column(db.String(50), nullable=False)  # e.g., 'xp_boost', 'mega_xp_boost'
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)  # None for instant effects
    multiplier = db.Column(db.Float, default=1.0)  # For XP/time multipliers
    is_active = db.Column(db.Boolean, default=True)
    
    def is_expired(self):
        """Check if power-up has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

class ShopService:
    # Hardcoded catalog for now
    ITEMS = {
        # === THEMES ===
        'theme_neon_city': {
            'id': 'theme_neon_city',
            'name': 'Neon City Theme',
            'description': 'Urban neon lights cityscape.',
            'price': 3800,
            'icon': 'fa-city',
            'type': 'theme',
            'color': '#06b6d4'
        },
        'theme_sakura': {
            'id': 'theme_sakura',
            'name': 'Sakura Theme',
            'description': 'Cherry blossom pink serenity.',
            'price': 2800,
            'icon': 'fa-spa',
            'type': 'theme',
            'color': '#f9a8d4'
        },
        'theme_cyberpunk': {
            'id': 'theme_cyberpunk',
            'name': 'Cyberpunk Theme',
            'description': 'Neon purple visuals and glitch effects.',
            'price': 4000,
            'icon': 'fa-vr-cardboard',
            'type': 'theme',
            'color': '#d946ef'
        },
        'theme_synthwave': {
            'id': 'theme_synthwave',
            'name': 'Synthwave Theme',
            'description': '80s retro neon grid aesthetic.',
            'price': 3500,
            'icon': 'fa-compact-disc',
            'type': 'theme',
            'color': '#f472b6'
        },
        'theme_aurora': {
            'id': 'theme_aurora',
            'name': 'Aurora Theme',
            'description': 'Northern lights with flowing colors.',
            'price': 3000,
            'icon': 'fa-wand-magic-sparkles',
            'type': 'theme',
            'color': '#a78bfa'
        },

        # === FRAMES ===
        'frame_gold': {
            'id': 'frame_gold',
            'name': 'Golden Frame',
            'description': 'Shiny gold border with pulsing glow.',
            'price': 2500,
            'icon': 'fa-crown',
            'type': 'frame',
            'color': '#eab308'
        },
        'frame_diamond': {
            'id': 'frame_diamond',
            'name': 'Diamond Frame',
            'description': 'Sparkling diamond border with shimmer.',
            'price': 7500,
            'icon': 'fa-gem',
            'type': 'frame',
            'color': '#a78bfa'
        },
        'frame_fire': {
            'id': 'frame_fire',
            'name': 'Fire Frame',
            'description': 'Blazing flames surrounding your avatar.',
            'price': 4000,
            'icon': 'fa-fire',
            'type': 'frame',
            'color': '#f97316'
        },
        'frame_ice': {
            'id': 'frame_ice',
            'name': 'Ice Frame',
            'description': 'Frozen crystal border with frost effect.',
            'price': 3500,
            'icon': 'fa-snowflake',
            'type': 'frame',
            'color': '#38bdf8'
        },
        'frame_glitch': {
            'id': 'frame_glitch',
            'name': 'Glitched Frame',
            'description': 'Animated glitch effect with RGB split.',
            'price': 5000,
            'icon': 'fa-bug',
            'type': 'frame',
            'color': '#ef4444'
        }
    }

    @staticmethod
    def buy_item(user: User, item_id: str):
        item = ShopService.ITEMS.get(item_id)
        if not item:
            return {'status': 'error', 'message': 'Item not found.'}
        
        # Check ownership (unless consumable)
        if item['type'] != 'consumable':
            owned = UserItem.query.filter_by(user_id=user.id, item_id=item_id).first()
            if owned:
                return {'status': 'error', 'message': 'You already own this item!'}

        # Check funds
        if user.total_xp < item['price']:
            needed = item['price'] - user.total_xp
            return {'status': 'error', 'message': f"Short on funds! You need {needed} more XP to unlock this."}

        # Deduct XP
        user.total_xp -= item['price']
        
        # Handle Consumables (Power-Ups)
        if item['type'] == 'consumable':
            effect = item.get('effect')
            
            if effect == 'instant_level':
                # Instant Level Up - Add 500 XP to level up
                user.total_xp += 500
                old_level = user.level
                user.level = GamificationService.calculate_level(user.total_xp)
                db.session.commit()
                return {'status': 'success', 'message': f"Level Up! You are now level {user.level}! ‰", 'new_xp': user.total_xp}
            
            elif effect in ['xp_multiplier', 'mega_xp_multiplier', 'time_multiplier', 'xp_protection']:
                # Duration-based power-ups
                duration = item.get('duration', 86400)  # Default 24 hours
                expires_at = datetime.utcnow() + timedelta(seconds=duration)
                
                # Determine multiplier
                if effect == 'xp_multiplier':
                    multiplier = 2.0
                elif effect == 'mega_xp_multiplier':
                    multiplier = 5.0
                elif effect == 'time_multiplier':
                    multiplier = 2.0
                else:  # xp_protection
                    multiplier = 0.0  # Special case - prevents XP loss
                
                # Create active power-up
                power_up = ActivePowerUp(
                    user_id=user.id,
                    power_up_id=item_id,
                    activated_at=datetime.utcnow(),
                    expires_at=expires_at,
                    multiplier=multiplier,
                    is_active=True
                )
                db.session.add(power_up)
                db.session.commit()
                
                # Calculate hours remaining
                hours = duration / 3600
                return {'status': 'success', 'message': f"{item['name']} activated! Effect lasts for {int(hours)} hours. š¡", 'new_xp': user.total_xp}
            
            else:
                # Unknown effect - just store as item
                new_item = UserItem(user_id=user.id, item_id=item_id)
                db.session.add(new_item)
                db.session.commit()
                return {'status': 'success', 'message': f"Purchased {item['name']}!", 'new_xp': user.total_xp}
        
        # Handle Themes and Frames
        new_item = UserItem(user_id=user.id, item_id=item_id)
        db.session.add(new_item)
        db.session.commit()
        
        return {'status': 'success', 'message': f"Purchased {item['name']}!", 'new_xp': user.total_xp}

    @staticmethod
    def equip_item(user: User, item_id: str):
        item = ShopService.ITEMS.get(item_id)
        if not item:
            return {'status': 'error', 'message': 'Item not found.'}

        # Verify ownership
        owned = UserItem.query.filter_by(user_id=user.id, item_id=item_id).first()
        if not owned:
            return {'status': 'error', 'message': 'You do not own this item.'}

        # Handle Equipping based on type
        if item['type'] == 'theme':
            # Unequip other themes
            current_active = (
                db.session.query(UserItem)
                .filter(UserItem.user_id == user.id, UserItem.is_active == True)
                .all()
            )
            
            # Deactivate other themes
            for active_item in current_active:
                # check if it's a theme by looking up the ID in ITEMS (simplified)
                # In real app, we'd store type in DB or join with Item table.
                # Here we check the hardcoded catalog.
                cat_item = ShopService.ITEMS.get(active_item.item_id)
                if cat_item and cat_item['type'] == 'theme':
                    active_item.is_active = False
            
            # Activate new
            owned.is_active = True
            db.session.commit()
            return {'status': 'success', 'message': f"Equipped {item['name']}!"}

        if item['type'] == 'frame':
            # Unequip other frames
            current_active = (
                db.session.query(UserItem)
                .filter(UserItem.user_id == user.id, UserItem.is_active == True)
                .all()
            )
            
            # Deactivate other frames
            for active_item in current_active:
                cat_item = ShopService.ITEMS.get(active_item.item_id)
                if cat_item and cat_item['type'] == 'frame':
                    active_item.is_active = False
            
            # Activate new
            owned.is_active = True
            db.session.commit()
            return {'status': 'success', 'message': f"Equipped {item['name']}!"}

        return {'status': 'error', 'message': 'This item cannot be equipped.'}


@app.route('/shop')
@login_required
def shop():
    # Get user inventory
    inventory = UserItem.query.filter_by(user_id=current_user.id).all()
    owned_ids = {u.item_id for u in inventory}
    active_ids = {u.item_id for u in inventory if u.is_active}
    
    return render_template('shop.html', items=ShopService.ITEMS, owned_ids=owned_ids, active_ids=active_ids)

@app.route('/shop/buy/<item_id>', methods=['POST'])
@login_required
def shop_buy(item_id):
    result = ShopService.buy_item(current_user, item_id)
    if result['status'] == 'success':
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    return redirect(url_for('shop'))

@app.route('/shop/equip/<item_id>', methods=['POST'])
@login_required
def shop_equip(item_id):
    result = ShopService.equip_item(current_user, item_id)
    if result['status'] == 'success':
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    return redirect(url_for('shop'))

@app.route('/shop/unequip/<item_id>', methods=['POST'])
@login_required
def shop_unequip(item_id):
    # Find the user's item and deactivate it
    user_item = UserItem.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if user_item:
        user_item.is_active = False
        db.session.commit()
        flash(f'Item unequipped successfully!', 'success')
    else:
        flash('Item not found.', 'error')
    return redirect(url_for('shop'))

# ============================================================================
# GROUP ROUTES  Multi-Group System (max 5 groups per user)
# ============================================================================

@app.route('/group')
@login_required
def group_chat():
    """Groups Dashboard: lists all groups the user is in + create/join forms."""
    user_groups = GroupService.get_user_groups(current_user.id)
    now = datetime.utcnow()

    # Build enriched group cards
    group_cards = []
    for g in user_groups:
        members = (
            db.session.query(User)
            .join(GroupMember, GroupMember.user_id == User.id)
            .filter(GroupMember.group_id == g.id)
            .all()
        )
        online = sum(1 for m in members if m.last_seen and (now - m.last_seen).total_seconds() < 300)
        unread = GroupService.get_unread_count(g.id, current_user.id)
        is_admin = GroupService.is_admin(g.id, current_user.id)
        group_cards.append({
            'group': g,
            'member_count': len(members),
            'online_count': online,
            'unread': unread,
            'is_admin': is_admin,
        })

    can_create = len(user_groups) < GROUP_MEMBER_LIMIT
    return render_template(
        'groups_dashboard.html',
        group_cards=group_cards,
        can_create=can_create,
        group_limit=GROUP_MEMBER_LIMIT
    )


@app.route('/group/<int:group_id>')
@login_required
def group_room(group_id):
    """Single group chat room."""
    group = Group.query.get_or_404(group_id)

    # Must be a member
    membership = GroupService.get_membership(group_id, current_user.id)
    if not membership:
        flash('You are not a member of this group.', 'error')
        return redirect(url_for('group_chat'))

    # Mark as read
    GroupService.mark_read(group_id, current_user.id)

    # Load pinned messages
    pinned_messages = (
        GroupChatMessage.query
        .filter_by(group_id=group_id, is_pinned=True)
        .order_by(GroupChatMessage.created_at.desc())
        .limit(3)
        .all()
    )

    # Load last 100 messages
    messages = (
        GroupChatMessage.query
        .filter_by(group_id=group_id)
        .order_by(GroupChatMessage.created_at.asc())
        .limit(100)
        .all()
    )

    # Load members with online status
    now = datetime.utcnow()
    raw_members = (
        db.session.query(User, GroupMember)
        .join(GroupMember, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )
    members = []
    online_count = 0
    for u, mem in raw_members:
        u.is_online_status = bool(u.last_seen and (now - u.last_seen).total_seconds() < 300)
        u.member_role = mem.role
        if u.is_online_status:
            online_count += 1
        members.append(u)

    is_admin = GroupService.is_admin(group_id, current_user.id)

    return render_template(
        'group_chat.html',
        group=group,
        group_messages=messages,
        pinned_messages=pinned_messages,
        group_members=members,
        online_count=online_count,
        is_admin=is_admin,
        membership=membership
    )


@app.route('/group/create', methods=['POST'])
@login_required
def group_create():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        flash('Group name is required.', 'error')
        return redirect(url_for('group_chat'))
    if len(name) > 50:
        flash('Group name must be 50 characters or fewer.', 'error')
        return redirect(url_for('group_chat'))
    if contains_profanity(name):
        flash('Group name contains inappropriate language. Please choose a respectful name.', 'error')
        return redirect(url_for('group_chat'))
    try:
        group = GroupService.create_group(current_user.id, name, description)
        flash(f'Group "{group.name}" created! Share the invite code with friends.', 'success')
        return redirect(url_for('group_room', group_id=group.id))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('group_chat'))


@app.route('/group/join', methods=['POST'])
@login_required
def group_join():
    invite_code = request.form.get('invite_code', '').strip().upper()
    if not invite_code:
        flash('Invite code is required.', 'error')
        return redirect(url_for('group_chat'))
    try:
        group = GroupService.join_group(current_user.id, invite_code)
        flash(f'Joined "{group.name}"! Welcome!', 'success')
        return redirect(url_for('group_room', group_id=group.id))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('group_chat'))


@app.route('/group/<int:group_id>/leave', methods=['POST'])
@login_required
def group_leave(group_id):
    """Leave a specific group by its ID."""
    group = Group.query.get_or_404(group_id)
    GroupService.leave_group(group_id, current_user.id)
    flash(f'You left "{group.name}".', 'success')
    return redirect(url_for('group_chat'))


@app.route('/group/<int:group_id>/send', methods=['POST'])
@login_required
def group_send(group_id):
    """Send a message to a specific group."""
    membership = GroupService.get_membership(group_id, current_user.id)
    if not membership:
        return jsonify({'error': 'Not a member'}), 403

    content = request.form.get('message', '').strip()
    if not content:
        return redirect(url_for('group_room', group_id=group_id))

    db.session.add(GroupChatMessage(
        group_id=group_id,
        user_id=current_user.id,
        role='user',
        content=content
    ))
    db.session.commit()

    # AI trigger: @StudyVerse or @assistant
    if '@studyverse' in content.lower() or '@assistant' in content.lower():
        reply = ChatService.personal_reply(current_user, content)
        db.session.add(GroupChatMessage(
            group_id=group_id,
            user_id=None,
            role='assistant',
            content=reply
        ))
        db.session.commit()

    return redirect(url_for('group_room', group_id=group_id))


# ”€”€ ADMIN-ONLY ACTIONS ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€

@app.route('/group/<int:group_id>/kick/<int:target_user_id>', methods=['POST'])
@login_required
def group_kick(group_id, target_user_id):
    """Admin: remove a member from the group."""
    try:
        kicked_user = User.query.get(target_user_id)
        GroupService.kick_member(group_id, current_user.id, target_user_id)
        name = kicked_user.first_name if kicked_user else 'User'
        flash(f'{name} has been removed from the group.', 'success')
    except (PermissionError, ValueError) as e:
        flash(str(e), 'error')
    return redirect(url_for('group_room', group_id=group_id))


@app.route('/group/<int:group_id>/rename', methods=['POST'])
@login_required
def group_rename(group_id):
    """Admin: rename the group."""
    new_name = request.form.get('name', '').strip()
    try:
        GroupService.rename_group(group_id, current_user.id, new_name)
        flash('Group renamed successfully.', 'success')
    except (PermissionError, ValueError) as e:
        flash(str(e), 'error')
    return redirect(url_for('group_room', group_id=group_id))


@app.route('/group/<int:group_id>/delete', methods=['POST'])
@login_required
def group_delete(group_id):
    """Admin: permanently delete the group."""
    group = Group.query.get_or_404(group_id)
    group_name = group.name
    try:
        GroupService.delete_group(group_id, current_user.id)
        flash(f'Group "{group_name}" has been deleted.', 'success')
    except PermissionError as e:
        flash(str(e), 'error')
    return redirect(url_for('group_chat'))


@app.route('/group/<int:group_id>/regen-code', methods=['POST'])
@login_required
def group_regen_code(group_id):
    """Admin: regenerate invite code."""
    try:
        new_code = GroupService.regen_invite_code(group_id, current_user.id)
        flash(f'New invite code generated: {new_code}', 'success')
    except PermissionError as e:
        flash(str(e), 'error')
    return redirect(url_for('group_room', group_id=group_id))



@app.route('/group/<int:group_id>/pin/<int:message_id>', methods=['POST'])
@login_required
def group_pin_message(group_id, message_id):
    """Admin: pin/unpin a message."""
    if not GroupService.is_admin(group_id, current_user.id):
        flash('Only the admin can pin messages.', 'error')
        return redirect(url_for('group_room', group_id=group_id))
    msg = GroupChatMessage.query.filter_by(id=message_id, group_id=group_id).first_or_404()
    msg.is_pinned = not msg.is_pinned
    db.session.commit()
    flash('Message ' + ('pinned.' if msg.is_pinned else 'unpinned.'), 'success')
    return redirect(url_for('group_room', group_id=group_id))


@app.route('/group/<int:group_id>/messages')
@login_required
def get_group_messages(group_id):
    """Polling endpoint: new messages since a given message ID."""
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not membership:
        return jsonify({'error': 'Not a member'}), 403

    since_id = request.args.get('since', 0, type=int)
    messages = (
        GroupChatMessage.query
        .filter(GroupChatMessage.group_id == group_id)
        .filter(GroupChatMessage.id > since_id)
        .order_by(GroupChatMessage.created_at.asc())
        .limit(50)
        .all()
    )

    msg_list = []
    for m in messages:
        sender_name = 'Unknown'
        avatar = None
        if m.role == 'assistant':
            sender_name = 'AI Coach'
        elif m.user:
            sender_name = m.user.first_name
            avatar = m.user.get_avatar(64)
        msg_list.append({
            'id': m.id,
            'user_id': m.user_id,
            'username': sender_name,
            'avatar': avatar,
            'content': m.content,
            'file_path': m.file_path,
            'created_at': to_ist_time(m.created_at),
            'created_at_iso': m.created_at.isoformat() + 'Z' if m.created_at else None,
            'role': m.role,
            'is_pinned': m.is_pinned,
        })

    # Update last_read_at while polling
    GroupService.mark_read(group_id, current_user.id)
    return jsonify({'messages': msg_list})

@app.route('/todos')
@login_required
def todos():
    personal = Todo.query.filter_by(user_id=current_user.id, is_group=False).order_by(Todo.created_at.desc()).all()
    group = Todo.query.filter_by(user_id=current_user.id, is_group=True).order_by(Todo.created_at.desc()).all()
    return render_template('todos.html', personal_todos=personal, group_todos=group)

@app.route('/todos/add', methods=['POST'])
@login_required
def todos_add():
    title = request.form.get('title', '').strip()
    is_group = request.form.get('is_group') == '1'
    if not title:
        return redirect(url_for('todos'))

    todo = Todo(
        user_id=current_user.id,
        title=title,
        completed=False,
        priority=request.form.get('priority', 'medium'),
        due_date=request.form.get('due_date'),
        category=request.form.get('category'),
        is_group=is_group,
    )
    db.session.add(todo)
    db.session.commit()
    
    next_url = request.form.get('next') or request.args.get('next')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('todos'))

@app.route('/todos/add_batch', methods=['POST'])
@login_required
def todos_add_batch():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    category = data.get('category', '').strip()
    priority = data.get('priority', 'Medium')
    due_date = data.get('due_date')
    due_time = data.get('due_time') # NEW: Capture time
    is_group = data.get('is_group') == '1' or data.get('is_group') is True
    subtasks = data.get('subtasks', [])

    if not subtasks:
        return jsonify({'error': 'No subtasks provided'}), 400

    created_count = 0
    for sub_title in subtasks:
        sub_title = str(sub_title).strip()
        if not sub_title:
            continue
        
        todo = Todo(
            user_id=current_user.id,
            title=sub_title,
            completed=False,
            priority=priority,
            due_date=due_date,
            due_time=due_time,       # NEW: Save time
            is_notified=False,       # NEW: Reset notification status
            category=category, # The "Task Title" acts as the category/project name
            is_group=is_group,
        )
        db.session.add(todo)
        created_count += 1

    if created_count > 0:
        db.session.commit()
        return jsonify({'status': 'success', 'count': created_count})
    
    return jsonify({'status': 'no_tasks_created'})

@app.context_processor
def inject_gamification():
    if current_user.is_authenticated:
        rank_info = GamificationService.get_rank(current_user.level)
        # XP to next level = 500 * level (simplified based on formula floor(total/500))
        # actually formula is level = floor(total/500) + 1
        # so next level at: level * 500
        next_level_xp = current_user.level * 500
        progress_percent = int(((current_user.total_xp % 500) / 500) * 100)
        
        # Get active theme
        active_theme_item = (
            db.session.query(UserItem)
            .filter_by(user_id=current_user.id, is_active=True)
            .all()
        )
        
        active_theme = None
        active_frame = None
        for u_item in active_theme_item:
             # Find the first active item that is a 'theme'
             cat_item = ShopService.ITEMS.get(u_item.item_id)
             if cat_item and cat_item['type'] == 'theme':
                 active_theme = u_item.item_id
             elif cat_item and cat_item['type'] == 'frame':
                 active_frame = u_item.item_id

        return dict(
            rank_name=rank_info['name'],
            rank_icon=rank_info['icon'],
            rank_color=rank_info['color'],
            next_level_xp=next_level_xp,
            level_progress=progress_percent,
            xp_remaining=next_level_xp - current_user.total_xp,
            active_theme=active_theme,
            active_frame=active_frame
        )
    return dict()

@app.route('/todos/toggle/<int:todo_id>', methods=['POST'])
@login_required
def todos_toggle(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.completed = not todo.completed
    
    # Update timestamp
    if todo.completed:
        todo.completed_at = datetime.utcnow()
    else:
        todo.completed_at = None
    
    # Award XP if completing
    try:
        xp_action = None
        if todo.completed:
            GamificationService.add_xp(current_user.id, 'task', 10)
            xp_action = 'completed'
            
            # Update Topic Proficiency
            if todo.category:
                topic = TopicProficiency.query.filter_by(user_id=current_user.id, topic_name=todo.category).first()
                if not topic:
                    topic = TopicProficiency(user_id=current_user.id, topic_name=todo.category, proficiency=0)
                    db.session.add(topic)
                topic.proficiency += 10
                topic.updated_at = datetime.utcnow()
                
        else:
            # Deduct XP if unchecked
            GamificationService.add_xp(current_user.id, 'task_undo', -10, force_deduct=True)
            xp_action = 'unchecked'

            # Deduct Proficiency if unchecked
            if todo.category:
                topic = TopicProficiency.query.filter_by(user_id=current_user.id, topic_name=todo.category).first()
                if topic and topic.proficiency >= 10:
                    topic.proficiency -= 10

        db.session.commit()
        # Flash ONLY after successful commit
        if xp_action == 'completed':
            flash('Task completed! +10 XP', 'success')
        elif xp_action == 'unchecked':
            flash('Task unchecked. -10 XP', 'info')
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling todo {todo_id}: {e}")
        flash('Something went wrong. Please try again.', 'warning')
    
    next_url = request.form.get('next') or request.args.get('next')
    if next_url:
        return redirect(next_url)

    return redirect(url_for('todos'))

@app.route('/todos/delete/<int:todo_id>', methods=['POST'])
@login_required
def todos_delete(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # DS concept: push deleted item into undo stack stored in session
    undo_stack = session.get('todo_undo_stack', [])
    undo_stack.append({
        'title': todo.title,
        'priority': todo.priority,
        'due_date': todo.due_date,
        'category': todo.category,
        'is_group': bool(todo.is_group),
    })
    session['todo_undo_stack'] = undo_stack[-20:]  # cap stack size

    db.session.delete(todo)
    db.session.commit()

    next_url = request.form.get('next') or request.args.get('next')
    if next_url:
        return redirect(next_url)

    return redirect(url_for('todos'))

@app.route('/todos/undo', methods=['POST'])
@login_required
def todos_undo():
    undo_stack = Stack()
    for item in session.get('todo_undo_stack', []):
        undo_stack.push(item)

    last = undo_stack.pop()
    if last is None:
        return redirect(url_for('todos'))

    # Write the updated stack back to session
    remaining = []
    while not undo_stack.is_empty():
        remaining.append(undo_stack.pop())
    session['todo_undo_stack'] = list(reversed(remaining))

    db.session.add(Todo(
        user_id=current_user.id,
        title=last['title'],
        completed=False,
        priority=last.get('priority', 'medium'),
        due_date=last.get('due_date'),
        category=last.get('category'),
        is_group=last.get('is_group', False),
    ))
    db.session.commit()
    return redirect(url_for('todos'))

@app.route('/pomodoro')
@login_required
def pomodoro():
    return render_template('pomodoro.html')

@app.route('/pomodoro/sessions', methods=['POST'])
@login_required
def pomodoro_save_session():
    """Save completed Pomodoro session to database."""
    duration = request.form.get('duration', type=int)
    mode = request.form.get('mode', 'focus')
    
    if duration:
        study_session = StudySession(
            user_id=current_user.id,
            duration=duration,
            mode=mode,
            completed_at=datetime.utcnow()
        )
        db.session.add(study_session)
        
        # Award XP: 1 XP per minute of focus
        if mode == 'focus':
            # Check for Double Time power-up to adjust stored duration
            active_time_boost = ActivePowerUp.query.filter_by(
                user_id=current_user.id, 
                power_up_id='double_time',
                is_active=True
            ).first()
            
            if active_time_boost and not active_time_boost.is_expired():
                study_session.duration = duration * 2
                xp_amount = duration # add_xp will handle the multiplier
            else:
                xp_amount = duration
                
            result = GamificationService.add_xp(current_user.id, 'focus', xp_amount)
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Session saved'})
    
    return jsonify({'status': 'error', 'message': 'Invalid duration'}), 400

@app.route('/pomodoro/goals', methods=['GET'])
@login_required
def pomodoro_get_goals():
    """Fetch session goals (Todos with category='Session Goal')."""
    goals = Todo.query.filter_by(user_id=current_user.id, category='Session Goal').order_by(Todo.created_at.asc()).all()
    return jsonify([
        {
            'id': g.id,
            'title': g.title,
            'completed': g.completed
        } for g in goals
    ])

@app.route('/pomodoro/goals', methods=['POST'])
@login_required
def pomodoro_add_goal():
    """Add a new session goal."""
    data = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400

    goal = Todo(
        user_id=current_user.id,
        title=title,
        completed=False,
        category='Session Goal',
        priority='medium',
        is_group=False
    )
    db.session.add(goal)
    db.session.commit()
    
    return jsonify({
        'id': goal.id,
        'title': goal.title,
        'completed': goal.completed
    })

@app.route('/pomodoro/goals/<int:goal_id>/toggle', methods=['POST'])
@login_required
def pomodoro_toggle_goal(goal_id):
    """Toggle completion status of a session goal."""
    goal = Todo.query.filter_by(id=goal_id, user_id=current_user.id, category='Session Goal').first_or_404()
    goal.completed = not goal.completed
    
    if goal.completed:
        # Mini reward for session goals
        GamificationService.add_xp(current_user.id, 'session_goal', 5)
        
    db.session.commit()
    return jsonify({'status': 'success', 'completed': goal.completed})

@app.route('/pomodoro/goals/<int:goal_id>/update', methods=['POST'])
@login_required
def pomodoro_update_goal(goal_id):
    """Update title of a session goal."""
    goal = Todo.query.filter_by(id=goal_id, user_id=current_user.id, category='Session Goal').first_or_404()
    
    data = request.get_json()
    new_title = data.get('title', '').strip()
    
    if new_title:
        goal.title = new_title
        db.session.commit()
        return jsonify({'status': 'success', 'title': goal.title})
    
    return jsonify({'error': 'Empty title'}), 400

@app.route('/pomodoro/goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def pomodoro_delete_goal(goal_id):
    """Delete a session goal."""
    goal = Todo.query.filter_by(id=goal_id, user_id=current_user.id, category='Session Goal').first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({'status': 'success'})

# -------------------------
# HABIT TRACKER ROUTES
# -------------------------
@app.route('/habits/add', methods=['POST'])
@login_required
def habits_add():
    title = request.form.get('title', '').strip()
    if title:
        habit = Habit(user_id=current_user.id, title=title)
        db.session.add(habit)
        db.session.commit()
        flash('Habit added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/habits/toggle/<int:habit_id>', methods=['POST'])
@login_required
def habits_toggle(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    today = datetime.utcnow().date()
    
    # Check if logged for today
    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
    
    if log:
        # Uncheck
        db.session.delete(log)
        db.session.commit()
    else:
        # Check
        log = HabitLog(habit_id=habit.id, completed_date=today)
        db.session.add(log)
        db.session.commit()
        
        # Gamification: Small XP for habit
        GamificationService.add_xp(current_user.id, 'habit', 5)

    return redirect(url_for('dashboard'))

@app.route('/habits/delete/<int:habit_id>', methods=['GET'])
@login_required
def habits_delete(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    # Logs cascade delete would be better, but manual verify
    HabitLog.query.filter_by(habit_id=habit.id).delete()
    db.session.delete(habit)
    db.session.commit()
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/api/habits/stats', methods=['GET'])
@login_required
def api_habit_stats():
    """Return this week's habit completion for the chart."""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) # Monday
    
    # Get all user habits
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    total_habits = len(habits)
    
    stats = []
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    if total_habits == 0:
        # Return empty stats if no habits
        for i in range(7):
            stats.append({'day': days[i], 'pct': 0})
        return jsonify(stats)

    for i in range(7):
        date_obj = start_of_week + timedelta(days=i)
        date_only = date_obj.date()
        
        # Count logs on this day for user's habits
        # Join HabitLog with Habit to ensure it belongs to user
        logs_count = (
            HabitLog.query
            .join(Habit)
            .filter(Habit.user_id == current_user.id)
            .filter(HabitLog.completed_date == date_only)
            .count()
        )
        
        pct = int((logs_count / total_habits) * 100)
        stats.append({
            'day': days[i],
            'pct': pct,
            'date': date_only.isoformat()
        })
        
    return jsonify(stats)


@app.route('/habit-debugger')
@login_required
def habit_debugger():
    return render_template('habit-debugger.html')

@app.route('/syllabus')
@app.route('/syllabus/<int:view_id>')
@login_required
def syllabus(view_id=None):
    # Get all docs sorted by newest first
    all_docs = SyllabusDocument.query.filter_by(user_id=current_user.id).order_by(SyllabusDocument.created_at.desc()).all()
    
    if not all_docs:
        doc = None
        archived_docs = []
    else:
        # If view_id is provided, find that doc
        if view_id:
            doc = next((d for d in all_docs if d.id == view_id), None)
            # If not found (unauthorized?), fallback to newest
            if not doc:
                doc = all_docs[0]
        else:
            # Default to newest (Active)
            doc = all_docs[0]
            
        # Archived are all except the one currently being viewed? 
        # Or archived are purely the "non-newest" ones?
        # Let's say: Archived list contains ALL docs except the current one being viewed, to allow switching.
        archived_docs = [d for d in all_docs if d.id != doc.id]

    # TODO: We really should filter chapters/todos by the specific syllabus!
    # currently `build_chapters_from_todos` fetches ALL tasks.
    # We need to link tasks to a syllabus_id or category matching the syllabus filename.
    # For now, to keep it simple as requested:
    # We will assume "Categories" == "Syllabus Name" or just display all.
    # Since the user asked for "completed courses section", we might need to filter tasks.
    # Given the current simple data model where tasks are just "Todos" with categories:
    # We will just show the current state.
    # Pass the ID of the specific syllabus we are viewing
    current_view_id = doc.id if doc else None
    
    chapters = SyllabusService.build_chapters_from_todos(current_user.id, syllabus_id=current_view_id)
    total_topics = sum(c['total'] for c in chapters)
    completed_topics = sum(c['completed'] for c in chapters)
    avg_completion = int((completed_topics / total_topics) * 100) if total_topics else 0
    
    return render_template(
        'syllabus.html',
        syllabus_doc=doc,
        archived_docs=archived_docs,
        chapters=chapters,
        chapters_count=len(chapters),
        topics_count=total_topics,
        completed_count=completed_topics,
        avg_completion=avg_completion,
    )

@app.route('/syllabus/restore/<int:doc_id>', methods=['POST'])
@login_required
def syllabus_restore(doc_id):
    """Restore an archived syllabus by making it the most recent."""
    doc = SyllabusDocument.query.get_or_404(doc_id)
    if doc.user_id != current_user.id:
        flash('Unauthorized.', 'error')
        return redirect(url_for('syllabus'))
    
    # Update its created_at to now to make it 'current'
    doc.created_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Restored {doc.filename} as active syllabus.', 'success')
    return redirect(url_for('syllabus'))

@app.route('/syllabus/upload', methods=['POST'])
@login_required
def syllabus_upload():
    """Upload and extract PDF syllabus."""
    uploaded = request.files.get('pdf')
    if not uploaded:
        flash('Please select a PDF file.', 'error')
        return redirect(url_for('syllabus'))

    filename = uploaded.filename or 'syllabus.pdf'

    pdf_bytes = uploaded.read()
    if not pdf_bytes:
        flash('Uploaded PDF was empty.', 'error')
        return redirect(url_for('syllabus'))

    # AI: Extract tasks directly from the PDF using Gemini (real API).
    tasks = []
    try:
        tasks = SyllabusService.extract_tasks_from_pdf(pdf_bytes)
    except Exception as e:
        flash(f'AI task extraction failed: {str(e)}', 'error')

    # Extract text with PyPDF2 (used as context for chat). Some PDFs (scans) may yield no text.
    extracted = ""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            text = page.extract_text() or ''
            parts.append(text)
        extracted = "\n".join(parts).strip()
    except Exception:
        extracted = ""

    if not extracted:
        # Keep a non-empty placeholder because SyllabusDocument.extracted_text is NOT NULL.
        extracted = f"(No text could be extracted from this PDF. It may be a scanned document.)\nFilename: {filename}"
        flash('PDF uploaded, but no text could be extracted (might be scanned image). Tasks can still be generated by AI.', 'error')

    doc = SyllabusService.save_syllabus(current_user.id, filename, extracted)

    # Persist AI-generated tasks into real Todos.
    target_date_str = request.form.get('target_date')
    target_date = None
    days_diff = 1
    
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            today = datetime.now()
            days_diff = (target_date - today).days
            if days_diff <= 0:
                 days_diff = 1 # Minimum 1 day
        except ValueError:
            pass

    # Count total items to be created for distribution
    total_items = 0
    if tasks:
        for task in tasks:
            total_items += 1 # Chapter task
            total_items += len(task.get("subtasks", []))
            
    items_per_day = 1
    if total_items > 0 and days_diff > 0:
        import math
        items_per_day = math.ceil(total_items / days_diff)

    completed_items_count = 0
    created_count = 0
    
    if tasks:
        for task in tasks:
            chapter = str(task.get("title", "")).strip() or "Chapter"
            subtasks = task.get("subtasks", [])
            chapter_category = chapter[:50]

            # Calculate Due Date
            day_offset = completed_items_count // items_per_day
            due_date_obj = datetime.now() + timedelta(days=day_offset)
            due_date_str = due_date_obj.strftime('%Y-%m-%d') if target_date else None

            # Create a parent todo for the chapter
            chapter_title = chapter[:200]
            exists = Todo.query.filter_by(user_id=current_user.id, title=chapter_title, category=chapter_category, is_group=False).first()
            if not exists:
                db.session.add(Todo(
                    user_id=current_user.id,
                    title=chapter_title,
                    completed=False,
                    priority='high', # Chapters are main goals
                    due_date=due_date_str,
                    category=chapter_category,
                    is_group=False,
                    syllabus_id=doc.id  # Link to this syllabus
                ))
                created_count += 1
            
            completed_items_count += 1

            if isinstance(subtasks, list):
                for sub in subtasks:
                    sub_title = str(sub).strip()
                    if not sub_title:
                        continue
                    sub_title = sub_title[:200]
                    
                    # Recalculate due date for subtasks as well to distribute them
                    day_offset = completed_items_count // items_per_day
                    due_date_obj = datetime.now() + timedelta(days=day_offset)
                    due_date_str = due_date_obj.strftime('%Y-%m-%d') if target_date else None
                    
                    exists = Todo.query.filter_by(user_id=current_user.id, title=sub_title, category=chapter_category, is_group=False).first()
                    if exists:
                        continue
                    db.session.add(Todo(
                        user_id=current_user.id,
                        title=sub_title,
                        completed=False,
                        priority='medium',
                        due_date=due_date_str,
                        category=chapter_category,
                        is_group=False,
                        syllabus_id=doc.id  # Link to this syllabus
                    ))
                    created_count += 1
                    completed_items_count += 1

        db.session.commit()

    if created_count > 0:
        flash(f'Created {created_count} tasks from PDF using Gemini!', 'success')
    else:
        flash('PDF uploaded and processed successfully!', 'success')
    return redirect(url_for('syllabus'))


@app.route('/api/syllabus/upload-stream', methods=['POST'])
@login_required
def syllabus_upload_stream():
    """
    Progressive PDF upload via Server-Sent Events.
    Streams each chapter as it is committed to the DB so the
    frontend can render tasks one-by-one (like Topic Resolver).
    """
    from flask import stream_with_context, Response

    uploaded = request.files.get('pdf')
    if not uploaded:
        return jsonify({'error': 'No PDF provided'}), 400

    filename  = uploaded.filename or 'syllabus.pdf'
    pdf_bytes = uploaded.read()
    if not pdf_bytes:
        return jsonify({'error': 'Empty PDF'}), 400

    target_date_str = request.form.get('target_date', '')
    user_id = current_user.id          # capture before generator

    def generate():
        import math, io as _io, json as _json

        # ── 1. Detect page count ─────────────────────────────────
        page_count = 0
        extracted  = ''
        try:
            from PyPDF2 import PdfReader
            reader     = PdfReader(_io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            parts      = [p.extract_text() or '' for p in reader.pages]
            extracted  = '\n'.join(parts).strip()
        except Exception:
            pass

        if not extracted:
            extracted = f'(No text extracted)\nFilename: {filename}'

        yield f'data: {_json.dumps({"type": "pages", "count": page_count})}\n\n'

        # ── 2. Save the SyllabusDocument first ───────────────────
        with app.app_context():
            doc = SyllabusService.save_syllabus(user_id, filename, extracted)
            doc_id = doc.id

        yield f'data: {_json.dumps({"type": "status", "msg": "PDF saved. Asking AI to analyse..."})}\n\n'

        # ── 3. Call Gemini with retry on overload ──────────────────
        tasks = []
        import time as _t
        _RETRY_DELAYS = [5, 15, 30]
        _last_exc = None
        for _attempt in range(3):
            try:
                tasks = SyllabusService.extract_tasks_from_pdf(pdf_bytes)
                _last_exc = None
                break
            except Exception as _e:
                _last_exc = _e
                _es = str(_e).lower()
                _retriable = any(k in _es for k in ('503', '429', 'high demand', 'quota', 'overload', 'unavailable'))
                if _attempt < 2 and _retriable:
                    _w = _RETRY_DELAYS[_attempt]
                    yield 'data: ' + _json.dumps({'type': 'status', 'msg': f'AI is busy — retrying in {_w}s... ({_attempt+2}/3)'}) + '\n\n'
                    _t.sleep(_w)
                    yield 'data: ' + _json.dumps({'type': 'status', 'msg': 'Retrying AI analysis...'}) + '\n\n'
                else:
                    break

        if _last_exc is not None:
            _es = str(_last_exc).lower()
            if any(k in _es for k in ('high demand', '503', 'overload', 'unavailable')):
                _msg = 'Google AI is overloaded right now. Please wait a minute and try again.'
            elif any(k in _es for k in ('quota', '429')):
                _msg = 'AI quota reached. Please wait a moment and try again.'
            else:
                _msg = str(_last_exc)
            yield 'data: ' + _json.dumps({'type': 'error', 'msg': _msg}) + '\n\n'
            return

        if not tasks:
            yield 'data: ' + _json.dumps({'type': 'error', 'msg': 'AI could not find any chapters in this PDF.'}) + '\n\n'
            return

        total_chapters = len(tasks)
        yield f'data: {_json.dumps({"type": "total", "chapters": total_chapters})}\n\n'

        # ── 4. Distribute due dates ──────────────────────────────
        target_date = None
        days_diff   = 1
        if target_date_str:
            try:
                from datetime import datetime as _dt
                target_date = _dt.strptime(target_date_str, '%Y-%m-%d')
                days_diff   = max(1, (target_date - _dt.now()).days)
            except ValueError:
                pass

        total_items   = sum(1 + len(t.get('subtasks', [])) for t in tasks)
        items_per_day = max(1, math.ceil(total_items / days_diff)) if total_items else 1

        # ── 5. Stream each chapter ───────────────────────────────
        completed_items = 0
        created_count   = 0

        with app.app_context():
            for idx, task in enumerate(tasks, 1):
                chapter    = str(task.get('title', '')).strip() or f'Chapter {idx}'
                subtasks   = task.get('subtasks', [])
                chapter_cat = chapter[:50]

                day_off    = completed_items // items_per_day
                from datetime import datetime as _dt2, timedelta as _td
                due_str    = (_dt2.now() + _td(days=day_off)).strftime('%Y-%m-%d') if target_date else None

                # Save chapter parent todo
                ch_title = chapter[:200]
                exists   = Todo.query.filter_by(user_id=user_id, title=ch_title,
                                                 category=chapter_cat, is_group=False).first()
                if not exists:
                    db.session.add(Todo(
                        user_id=user_id, title=ch_title, completed=False,
                        priority='high', due_date=due_str,
                        category=chapter_cat, is_group=False, syllabus_id=doc_id
                    ))
                    created_count += 1
                completed_items += 1

                # Save subtasks
                sub_titles = []
                for sub in subtasks:
                    sub_title = str(sub).strip()[:200]
                    if not sub_title:
                        continue
                    day_off  = completed_items // items_per_day
                    due_str2 = (_dt2.now() + _td(days=day_off)).strftime('%Y-%m-%d') if target_date else None
                    ex2      = Todo.query.filter_by(user_id=user_id, title=sub_title,
                                                     category=chapter_cat, is_group=False).first()
                    if not ex2:
                        db.session.add(Todo(
                            user_id=user_id, title=sub_title, completed=False,
                            priority='medium', due_date=due_str2,
                            category=chapter_cat, is_group=False, syllabus_id=doc_id
                        ))
                        created_count += 1
                    sub_titles.append(sub_title)
                    completed_items += 1

                # Commit this chapter immediately
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                # Stream chapter event to frontend
                yield f'data: {_json.dumps({"type": "chapter", "index": idx, "total": total_chapters, "title": chapter, "subtasks": sub_titles})}\n\n'

        # ── 6. Done ──────────────────────────────────────────────
        yield f'data: {_json.dumps({"type": "done", "created": created_count, "doc_id": doc_id})}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',   # disable Nginx buffering on Render
        }
    )

@app.route('/api/update_proficiency', methods=['POST'])
@login_required
def update_proficiency():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400
        
    topic_name = data.get('topic_name')
    score = data.get('score') # 0-100 or 1-10
    
    if not topic_name or score is None:
        return jsonify({'error': 'Missing fields'}), 400
        
    # Scale 1-10 to 0-100 if needed, assuming input might be 1-10 slider
    try:
        score = int(score)
        if score <= 10:
             score = score * 10
    except:
        return jsonify({'error': 'Invalid score'}), 400

    topic = TopicProficiency.query.filter_by(user_id=current_user.id, topic_name=topic_name).first()
    if not topic:
        topic = TopicProficiency(user_id=current_user.id, topic_name=topic_name, proficiency=score)
        db.session.add(topic)
    else:
        # Simple moving average or just overwrite?
        # User explicitly sets "Confidence", so overwrite or weighted average is best.
        # Let's do a weighted update: current*0.7 + new*0.3
        # Actually, if the user says "I am 8/10 confident", that is the current state. Overwrite.
        topic.proficiency = score
        topic.updated_at = datetime.utcnow()
        
    db.session.commit()
    return jsonify({'status': 'success', 'new_score': topic.proficiency})


@app.route('/api/syllabus_graph')
@login_required
def syllabus_graph():
    """Return JSON data for 3D Force Graph."""
    chapters = SyllabusService.build_chapters_from_todos(current_user.id)
    
    nodes = []
    links = []
    
    # Root Node
    nodes.append({'id': 'My Galaxy', 'group': 0, 'val': 30, 'color': '#ffffff'})
    
    for chapter in chapters:
        cat_name = chapter['name']
        # Chapter Node
        nodes.append({
            'id': cat_name,
            'group': 1,
            'val': 15,
            'color': '#60a5fa' # Blue
        })
        links.append({
            'source': 'My Galaxy',
            'target': cat_name
        })
        
        # Topic Nodes
        for t in chapter['todos']:
            t_title = t.title[:30] + '...' if len(t.title) > 30 else t.title
            
            # Helper to avoid ID collisions if same topic name exists in multiple chapters (unlikely but possible)
            node_id = f"{cat_name} || {t_title}" 
            
            color = '#4ade80' if t.completed else '#f43f5e' # Green or Red
            
            nodes.append({
                'id': node_id,
                # We want to display the clean title, 3d-force-graph uses 'id' as label by default but we can change accessors
                'name': t_title, 
                'group': 2,
                'val': 5,
                'color': color
            })
            links.append({
                'source': cat_name,
                'target': node_id
            })
            
    return jsonify({'nodes': nodes, 'links': links})

@app.route('/progress')
@login_required
def progress():
    total_todos = Todo.query.filter_by(user_id=current_user.id).count()
    completed_todos = Todo.query.filter_by(user_id=current_user.id, completed=True).count()
    completion_percent = int((completed_todos / total_todos) * 100) if total_todos else 0

    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_minutes = (
        db.session.query(db.func.coalesce(db.func.sum(StudySession.duration), 0))
        .filter(StudySession.user_id == current_user.id)
        .filter(StudySession.completed_at >= week_ago)
        .scalar()
    )
    weekly_hours = round((weekly_minutes or 0) / 60.0, 2)
    sessions_week = StudySession.query.filter_by(user_id=current_user.id).filter(StudySession.completed_at >= week_ago).count()

    # Consecutive-day streak based on completed sessions.
    streak = 0
    # Calculate Monday of the current week
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday()) # Monday = 0
    
    daily = []
    max_hours = 0.0
    
    # Iterate Mon (0) to Sun (6)
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        start_dt = datetime.combine(day, datetime.min.time())
        end_dt = datetime.combine(day, datetime.max.time())
        
        minutes = (
            db.session.query(db.func.coalesce(db.func.sum(StudySession.duration), 0))
            .filter(StudySession.user_id == current_user.id)
            .filter(StudySession.completed_at >= start_dt)
            .filter(StudySession.completed_at <= end_dt)
            .scalar()
        )
        hours = round((minutes or 0) / 60.0, 2)
        max_hours = max(max_hours, hours)
        
        # Format label (e.g. "1.5h" or "45m")
        total_minutes = int(minutes or 0)
        display_val = ""
        if total_minutes > 0:
            if total_minutes < 60:
                display_val = f"{total_minutes}m"
            else:
                h = total_minutes // 60
                m = total_minutes % 60
                display_val = f"{h}h {m}m" if m > 0 else f"{h}h"
                
        daily.append({
            'label': day.strftime('%a'),
            'hours': hours,
            'minutes': total_minutes,
            'display': display_val,
            'is_future': day > today
        })

    for d in daily:
        # Use minutes for more precise percentage relative to max
        max_minutes = max([x['minutes'] for x in daily]) if daily else 0
        
        if max_minutes > 0:
            d['percent'] = int((d['minutes'] / max_minutes) * 100)
            if d['minutes'] > 0 and d['percent'] < 5:
                d['percent'] = 5
        else:
            d['percent'] = 0

    top_topics = (
        TopicProficiency.query
        .filter_by(user_id=current_user.id)
        .order_by(TopicProficiency.proficiency.desc())
        .limit(5)
        .all()
    )
    
    # Fetch user inventory count for streak freezes
    streak_freezes = UserItem.query.filter_by(user_id=current_user.id, item_id='streak_freeze').count()

    # Category Distribution for Pie Chart
    categories = db.session.query(Todo.category, db.func.count(Todo.id))\
        .filter(Todo.user_id == current_user.id)\
        .group_by(Todo.category).all()
    category_data = {cat or 'Uncategorized': count for cat, count in categories}

    return render_template(
        'progress.html',
        total_todos=total_todos,
        completed_todos=completed_todos,
        completion_percent=completion_percent,
        weekly_hours=weekly_hours,
        sessions_week=sessions_week,
        day_streak=streak,
        daily_hours=daily,
        top_topics=top_topics,
        streak_freezes=streak_freezes,
        category_distribution=category_data
    )

@app.route('/leaderboard')
@login_required
def leaderboard():
    """Global leaderboard based on level and XP - Excludes admins."""
    # Get top 50 users ordered by level (desc), then by total_xp (desc)
    # EXCLUDE ADMINS from leaderboard
    top_users = (
        User.query
        .filter(
            User.is_public_profile == True,
            User.is_admin == False,
            User.is_banned == False
        )
        .order_by(User.level.desc(), User.total_xp.desc(), User.id.asc())
        .limit(50)
        .all()
    )
    
    # Calculate display ranks handling ties (Standard Competition Ranking like 1, 2, 2, 4)
    for i, user in enumerate(top_users):
        if i == 0:
            user.display_rank = 1
        else:
            prev = top_users[i-1]
            # Check for tie
            if user.total_xp == prev.total_xp and user.level == prev.level:
                user.display_rank = prev.display_rank
            else:
                user.display_rank = i + 1
    
    # Calculate current user's rank much more efficiently
    # Rank is 1 + number of users who have more level OR same level but more XP
    # EXCLUDE ADMINS from rank calculation
    my_rank = User.query.filter(
        User.is_public_profile == True,
        User.is_admin == False,
        User.is_banned == False,
        db.or_(
            User.level > current_user.level,
            db.and_(
                User.level == current_user.level,
                User.total_xp > current_user.total_xp
            )
        )
    ).count() + 1
    
    return render_template(
        'leaderboard.html',
        leaderboard=top_users,
        my_rank=my_rank
    )

@app.route('/settings')
@login_required
def settings():
    return profile(current_user.id)

@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)
    
    # Ensure badges are up to date
    GamificationService.check_badges(user)
    db.session.commit()
    
    badges = UserBadge.query.filter_by(user_id=user.id).all()
    # Calculate stats for the target user
    total_focus_minutes = db.session.query(db.func.sum(StudySession.duration))\
        .filter(StudySession.user_id == user.id).scalar() or 0
    total_focus_hours = round(total_focus_minutes / 60, 1)

    # Fetch tasks for Calendar (only if viewing own profile)
    calendar_events = []
    if current_user.is_authenticated and user.id == current_user.id:
        calendar_events = Todo.query.filter_by(user_id=user.id, completed=False)\
            .filter(Todo.due_date.isnot(None))\
            .filter(Todo.due_date != '')\
            .order_by(Todo.due_date.asc())\
            .all()

    # Get Active Frame
    active_frame = None
    active_items = UserItem.query.filter_by(user_id=user.id, is_active=True).all()
    for u_item in active_items:
        cat_item = ShopService.ITEMS.get(u_item.item_id)
        if cat_item and cat_item['type'] == 'frame':
            active_frame = cat_item
            break

    return render_template('profile.html', user=user, badges=badges, total_focus_hours=total_focus_hours, calendar_events=calendar_events, active_frame=active_frame)

@app.route('/calendar')
@login_required
def calendar_view():
    # Only show uncompleted tasks with due dates for the calendar
    calendar_events = Todo.query.filter_by(user_id=current_user.id, completed=False)\
        .filter(Todo.due_date.isnot(None))\
        .filter(Todo.due_date != '')\
        .order_by(Todo.due_date.asc())\
        .all()
    
    return render_template('calendar.html', calendar_events=calendar_events)

@app.route('/settings/public-profile', methods=['POST'])
@login_required
def update_public_profile():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    is_public = data.get('is_public', True)
    current_user.is_public_profile = bool(is_public)
    db.session.commit()
    return jsonify({'status': 'success'})

@socketio.on('connect')
def on_connect():
    """Join personal notification room on every socket connect."""
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')

@socketio.on('join')
def on_join(data):
    group_id = data.get('group_id')
    if group_id:
        room_name = str(group_id)
        join_room(room_name)
        emit('joined_room', {'room': room_name})
    # Also join personal room for DM call notifications
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')

# ── Group Call Socket Events ────────────────────────────────
@socketio.on('start_group_call')
def handle_start_group_call(data):
    """Broadcast to all group members that a call has started."""
    if not current_user.is_authenticated:
        return
    group_id = data.get('group_id')
    if not group_id:
        return
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not membership:
        return
    caller_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.first_name or 'Someone'
    emit('group_call_started', {
        'caller_id': current_user.id,
        'caller_name': caller_name,
        'caller_avatar': current_user.get_avatar(64),
        'group_id': group_id,
    }, room=str(group_id), broadcast=True)

@socketio.on('end_group_call')
def handle_end_group_call(data):
    """Broadcast to all group members that the call has ended."""
    if not current_user.is_authenticated:
        return
    group_id = data.get('group_id')
    if group_id:
        emit('group_call_ended', {'group_id': group_id}, room=str(group_id), broadcast=True)

# ── DM Call Socket Events ───────────────────────────────────
@socketio.on('start_dm_call')
def handle_start_dm_call(data):
    """Send incoming call notification to a specific user."""
    if not current_user.is_authenticated:
        return
    target_user_id = data.get('target_user_id')
    if not target_user_id:
        return
    caller_name = f"{current_user.first_name} {current_user.last_name}".strip() or 'Someone'
    # Emit to target user's personal room (they join this on connect)
    socketio.emit('dm_call_incoming', {
        'caller_id': current_user.id,
        'caller_name': caller_name,
        'caller_avatar': current_user.get_avatar(64),
    }, room=f'user_{target_user_id}')

@socketio.on('dm_call_response')
def handle_dm_call_response(data):
    """Forward the accept/decline response back to the original caller."""
    if not current_user.is_authenticated:
        return
    caller_id = data.get('caller_id')
    accepted = data.get('accepted', False)
    responder_name = current_user.first_name or 'Friend'
    if caller_id:
        socketio.emit('dm_call_result', {
            'accepted': accepted,
            'responder_name': responder_name,
            'responder_id': current_user.id,
        }, room=f'user_{caller_id}')

@app.route('/settings/update', methods=['POST'])
@login_required
def settings_update():
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip().lower()

    if not first_name or not email:
        return jsonify({'status': 'error', 'message': 'First Name and Email are required'}), 400

    # Profanity check on names
    name_err = validate_name_field(first_name, 'First name')
    if name_err:
        return jsonify({'status': 'error', 'message': name_err}), 400
    name_err = validate_name_field(last_name, 'Last name')
    if name_err:
        return jsonify({'status': 'error', 'message': name_err}), 400

    current_user.first_name = first_name
    current_user.last_name = last_name

    # Check if email is being changed and if it's taken
    if email != current_user.email:
        existing = User.query.filter_by(email=email).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 400
        current_user.email = email

    # Profanity check on bio
    about_me = data.get('about_me', current_user.about_me)
    if about_me and contains_profanity(about_me):
        return jsonify({'status': 'error', 'message': 'Bio contains inappropriate language. Please keep it respectful.'}), 400
    current_user.about_me = about_me

    try:
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# NOTE: We intentionally avoid JSON-based API endpoints for this semester project.






# ------------------------------
# SocketIO & Real-time Logic
# ------------------------------

@socketio.on('join')
def on_join(data):
    group_id = data.get('group_id')
    if group_id:
        room_name = str(group_id)
        join_room(room_name)
        print(f"œ“ User {current_user.id if current_user.is_authenticated else 'Unknown'} joined room {room_name}")
        # Send confirmation back to THIS client only
        emit('joined_room', {'room': room_name})

@socketio.on('send_message')
def handle_message(data):
    group_id = data.get('group_id')
    content = data.get('content', '')
    file_path = data.get('file_path')
    
    if not group_id or not current_user.is_authenticated:
        return

    # Check membership
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=current_user.id).first()
    if not membership:
        return

    msg = GroupChatMessage(
        group_id=group_id,
        user_id=current_user.id,
        role='user',
        content=content,
        file_path=file_path
    )
    db.session.add(msg)
    db.session.commit()

    # Convert timestamp to IST
    ist_time = to_ist_time(msg.created_at)
    
    message_data = {
        'id': msg.id,
        'user_id': current_user.id,
        'username': current_user.first_name or 'User',
        'avatar': current_user.get_avatar(64),
        'content': msg.content,
        'file_path': msg.file_path,
        'created_at': ist_time,
        'created_at_iso': msg.created_at.isoformat() + 'Z' if msg.created_at else None,
        'role': 'user'
    }

    # Broadcast to everyone in the room
    print(f"“¤ Broadcasting message to room {group_id}: {msg.content[:50]}")
    emit('receive_message', message_data, room=str(group_id), broadcast=True)
    print(f" Message broadcasted")

    
    # AI Logic (Simple mention check)
    if '@StudyVerse' in content.lower() or '@assistant' in content.lower():
        reply = ChatService.personal_reply(current_user, content)
        ai_msg = GroupChatMessage(group_id=group_id, user_id=None, role='assistant', content=reply)
        db.session.add(ai_msg)
        db.session.commit()
        
        # Convert AI message timestamp to IST
        ai_ist_time = to_ist_time(ai_msg.created_at)
        
        socketio.emit('receive_message', {
            'id': ai_msg.id,
            'user_id': None,
            'username': 'StudyVerse',
            'content': ai_msg.content,
            'created_at': ai_ist_time,
            'role': 'assistant'
        }, room=str(group_id), include_self=True)


@app.route('/group/upload', methods=['POST'])
@login_required
def group_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Allowed file types for group chat (images, PDFs, ZIP archives, and Code/Web files)
    ALLOWED_EXTENSIONS = {
        'png', 'jpg', 'jpeg', 'gif', 'webp',   # Images
        'pdf', 'txt', 'pptx',                  # Documents
        'zip', 'rar', '7z', 'tar', 'gz',         # Archives (ZIP etc.)
        'html', 'css', 'js', 'java', 'ejs',    # Code/Web/Template files
        'py', 'ipynb',                         # Python/Data files
        'jsx', 'tsx', 'ts', 'cjs', 'mjs', 'json' # React/Node/Express files
    }
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'File type .{ext} is not allowed. Allowed: images, PDF, ZIP archives, Web, Python, JS/TS code.'}), 400

    # ZIP size cap: 50 MB
    if ext in {'zip', 'rar', '7z', 'tar', 'gz'}:
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Rewind
        if file_size > 50 * 1024 * 1024:
            return jsonify({'error': 'ZIP/archive files cannot exceed 50 MB.'}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(save_path)

    return jsonify({
        'url': url_for('static', filename=f'uploads/{unique_filename}'),
        'filename': filename,
        'file_type': ext  # Let frontend know the type for icon rendering
    })

@app.route('/profile/upload_cover', methods=['POST'])
@login_required
def profile_upload_cover():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # Use timestamp to avoid caching issues
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"cover_{current_user.id}_{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(save_path)
        
        # Update user profile
        current_user.cover_image = f"uploads/{unique_filename}"
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'url': url_for('static', filename=f'uploads/{unique_filename}')
        })
    
    return jsonify({'error': 'Upload failed'}), 500

# ------------------------------
# BYTE BATTLE LOGIC (1v1 AI Referee)
# ------------------------------

@app.route('/battle')
@login_required
def battle():
    return render_template('battle.html')

# In-memory battle state
battles = {}

def generate_room_code(length=4):
    import random, string
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(length))
        if code not in battles:
            return code

@socketio.on('battle_create')
def on_battle_create(data):
    if not current_user.is_authenticated:
        return
    
    room_code = generate_room_code()
    battles[room_code] = {
        'host': current_user.id,
        'players': {
            current_user.id: {
                'name': current_user.first_name or 'Player 1',
                'sid': request.sid,
                'joined_at': datetime.utcnow()
            }
        },
        'state': 'waiting', # waiting, setup, battle, judging, result
        'config': {'difficulty': None, 'language': None},
        'problem': None,
        'submissions': {},
        'rematch_votes': {}, # player_id: "yes"/"no"
        'pending_join': None # Stores info about player requesting to join
    }
    
    join_room(room_code)
    emit('battle_created', {'room_code': room_code, 'player_id': current_user.id})
    print(f"Battle created: {room_code} by {current_user.first_name}")

@socketio.on('battle_rejoin_attempt')
def on_battle_rejoin_attempt(data):
    if not current_user.is_authenticated:
        return
        
    room_code = data.get('room_code', '').strip().upper()
    if room_code not in battles:
        emit('battle_error', {'message': 'Room invalid or expired.'})
        return
        
    room = battles[room_code]
    
    # Verify user is actually in the room
    if current_user.id in room['players']:
        # UPDATE SID (Critical for refresh)
        room['players'][current_user.id]['sid'] = request.sid
        
        join_room(room_code)
        
        # Determine if host
        is_host = (room['host'] == current_user.id)
        
        emit('battle_rejoined', {
            'state': room['state'], 
            'room_code': room_code,
            'is_host': is_host,
            'players': [{'id': p, 'name': v['name']} for p,v in room['players'].items()]
        })
        print(f"User {current_user.first_name} re-joined room {room_code}")
    else:
        # User thinks they are in room, but server disagrees (restart)
        emit('battle_error', {'message': 'You are not in this room.'})

@socketio.on('battle_join_request')
def on_battle_join_request(data):
    if not current_user.is_authenticated:
        return
        
    room_code = data.get('room_code', '').strip().upper()
    if room_code not in battles:
        emit('battle_error', {'message': 'Invalid room code.'})
        return
        
    room = battles[room_code]
    if len(room['players']) >= 2:
        emit('battle_error', {'message': 'Room is full.'})
        return

    # Check if already in (re-join)
    if current_user.id in room['players']:
        room['players'][current_user.id]['sid'] = request.sid
        join_room(room_code)
        emit('battle_rejoined', {'state': room['state'], 'room_code': room_code})
        return

    # Store pending request
    room['pending_join'] = {
        'id': current_user.id,
        'name': current_user.first_name or 'Opponent',
        'sid': request.sid
    }
    
    # Notify Host - Broadcast to room AND specifically to host's SID
    # This ensures the notification reaches the host even after page refresh
    host_sid = room['players'][room['host']]['sid']
    
    # Emit to host's specific session
    socketio.emit('battle_join_request_notify', {
        'player_name': room['pending_join']['name']
    }, room=host_sid)
    
    # Also broadcast to entire room as backup
    socketio.emit('battle_join_request_notify', {
        'player_name': room['pending_join']['name']
    }, room=room_code)

@socketio.on('battle_join_response')
def on_battle_join_response(data):
    room_code = data.get('room_code')
    accepted = data.get('accepted')
    
    if not room_code or room_code not in battles:
        return
    
    room = battles[room_code]
    # Only host can accept
    if current_user.id != room['host']:
        return
        
    pending = room.get('pending_join')
    if not pending:
        return
        
    if accepted:
        # Add player
        room['players'][pending['id']] = {
            'name': pending['name'],
            'sid': pending['sid'],
            'joined_at': datetime.utcnow()
        }
        
        # Manually join the socket room for the new player
        # Note: In Flask-SocketIO, we can't easily force another SID to join a room 
        # unless we are in that context or use a specific manager. 
        # Easier approach: Emit 'join_accepted' to the pending player, they emit 'battle_confirm_join'.
        socketio.emit('join_accepted', {'room_code': room_code}, room=pending['sid'])
        room['pending_join'] = None
    else:
        socketio.emit('battle_error', {'message': 'Host rejected your request.'}, room=pending['sid'])
        room['pending_join'] = None

@socketio.on('battle_confirm_join')
def on_battle_confirm_join(data):
    room_code = data.get('room_code')
    if room_code in battles and current_user.id in battles[room_code]['players']:
        join_room(room_code)
        
        # Room is full, move to SETUP immediately
        room = battles[room_code]
        room['state'] = 'setup'
        
        # Notify both to open UI
        emit('battle_entered', {'room_code': room_code}, room=room_code)
        
        # AI Welcome Message
        socketio.emit('battle_chat_message', {
            'sender': 'ByteBot',
            'message': (
                "Welcome to Byte Battle š”\n"
                "Both players are connected.\n\n"
                f"Host ({room['players'][room['host']]['name']}), please select:\n"
                "- Difficulty: Easy / Medium / Hard\n"
                "- Language: Python / JS / Java / C"
            ),
            'type': 'system'
        }, room=room_code)

@socketio.on('battle_chat_send')
def on_battle_chat_send(data):
    room_code = data.get('room_code')
    message = data.get('message', '').strip()
    
    if not room_code or room_code not in battles:
        return
        
    room = battles[room_code]
    player = room['players'].get(current_user.id)
    if not player:
        return

    # Broadcast user message
    emit('battle_chat_message', {
        'sender': player['name'],
        'message': message,
        'type': 'user'
    }, room=room_code)
    
    # Handle Setup Logic via Chat
    if room['state'] == 'setup':
        if current_user.id == room['host']:
            # Parse settings
            msg_lower = message.lower()
            
            # Difficulty
            if 'easy' in msg_lower: room['config']['difficulty'] = 'Easy'
            elif 'medium' in msg_lower: room['config']['difficulty'] = 'Medium'
            elif 'hard' in msg_lower: room['config']['difficulty'] = 'Hard'
            
            # Language
            if 'python' in msg_lower: room['config']['language'] = 'Python'
            elif 'javascript' in msg_lower or 'js' in msg_lower: room['config']['language'] = 'JavaScript'
            elif 'java' in msg_lower: room['config']['language'] = 'Java'
            elif 'c++' in msg_lower or 'cpp' in msg_lower: room['config']['language'] = 'C++'
            elif 'c' in msg_lower: room['config']['language'] = 'C'
            
            # Check if done
            config = room['config']
            if config['difficulty'] and config['language']:
                room['state'] = 'generating'
                emit('battle_chat_message', {
                    'sender': 'ByteBot',
                    'message': f"Configuration locked: {config['difficulty']} | {config['language']}.\nGenerating problem...",
                    'type': 'system'
                }, room=room_code)
                
                # Start Battle
                socketio.start_background_task(start_battle_task, room_code)
            else:
                 # Feedback on what's missing
                 missing = []
                 if not config['difficulty']: missing.append("Difficulty")
                 if not config['language']: missing.append("Language")
                 if missing:
                      # Only reply if it looked like an attempt (optional, to avoid spam)
                      pass 

def start_battle_task(room_code):
    with app.app_context():
        room = battles[room_code]
        config = room['config']
        
        problem = generate_battle_problem(config['difficulty'], config['language'])
        room['problem'] = problem
        room['state'] = 'battle'
        room['start_time'] = datetime.utcnow().timestamp()
        
        # Announce problem
        socketio.emit('battle_chat_message', {
            'sender': 'ByteBot',
            'message': "Here is your challenge.\nTimer has started.",
            'type': 'system'
        }, room=room_code)
        
        socketio.emit('battle_started', {
            'problem': problem,
            'duration': 600, # 10 mins
            'language': config['language']
        }, room=room_code)

@socketio.on('battle_submit')
def on_battle_submit(data):
    room_code = data.get('room_code')
    code = data.get('code')
    
    if not room_code or room_code not in battles:
        return
        
    room = battles[room_code]
    if room['state'] != 'battle':
        return
        
    # Store submission
    submission_time = datetime.utcnow().timestamp()
    time_taken = submission_time - room.get('start_time', submission_time)
    
    room['submissions'][current_user.id] = {
        'code': code,
        'time_taken': time_taken,
        'player_name': room['players'][current_user.id]['name']
    }
    
    # Notify others
    emit('battle_notification', {'message': f"”” {room['players'][current_user.id]['name']} has submitted their solution."}, room=room_code)
    emit('battle_chat_message', {'sender': 'ByteBot', 'message': f"”” {room['players'][current_user.id]['name']} has submitted their solution.", 'type': 'system'}, room=room_code)
    
    # Check if all submitted
    if len(room['submissions']) == len(room['players']):
        room['state'] = 'judging'
        emit('battle_state_change', {'state': 'judging'}, room=room_code)
        socketio.start_background_task(judge_battle, room_code)

def generate_battle_problem(difficulty, language):
    prompt = (
        f"Generate a single {difficulty} difficulty coding interview problem suitable for {language}. "
        "Return ONLY valid JSON with this structure: "
        "{ \"title\": \"Problem Title\", \"description\": \"Clear problem statement...\", "
        "\"input_format\": \"Input description...\", \"output_format\": \"Output description...\", "
        "\"example_input\": \"...\", \"example_output\": \"...\" }"
    )
    
    try:
        response = call_ai_api([{'role': 'user', 'content': prompt}])
        # Cleanup JSON
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
            
        return json.loads(response.strip())
    except Exception as e:
        print(f"Error generating problem: {e}")
        return {
            "title": "Palindrome Check",
            "description": "Write a program to check if a string is a palindrome.",
            "input_format": "A single string S.",
            "output_format": "Print 'YES' if palindrome, else 'NO'.",
            "example_input": "racecar",
            "example_output": "YES"
        }

def judge_battle(room_code):
    """Background task to judge the battle"""
    with app.app_context():
        room = battles.get(room_code)
        if not room:
            return

        submissions = list(room['submissions'].values())
        if not submissions:
            return

        problem_desc = json.dumps(room['problem'])
        subs_text = ""
        for i, sub in enumerate(submissions):
            subs_text += f"\nPlayer ({sub['player_name']}) Code [Time: {round(sub['time_taken'],1)}s]:\n{sub['code']}\n"

        prompt = (
            f"You are the referee of a coding battle. Problem: {problem_desc}\n"
            f"Submissions: {subs_text}\n"
            "Evaluate based on: 1. Correctness (Passes all edge cases?) 2. Logic quality 3. Time Taken.\n"
            "Return ONLY valid JSON: "
            "{ \"winner\": \"Player Name\" (or 'Draw'), \"reason\": \"Why they won...\", "
            "\"winner_id\": 123 (user id or null if draw), "
            "\"scores\": { \"Player 1 Name\": 90, \"Player 2 Name\": 85 } }"
        )
        
        # Helper to find user ID by name (AI might not return ID perfectly, so we map names)
        # Actually better to ask AI for index or just rely on name matching?
        # Let's map names to IDs first.
        name_to_id = { p['name']: pid for pid, p in room['players'].items() }
        
        try:
            response = call_ai_api([{'role': 'user', 'content': prompt}])
             # Cleanup JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            result = json.loads(response.strip())
            
            # Award XP
            difficulty = room['config'].get('difficulty', 'Easy')
            xp_map = {'Easy': 100, 'Medium': 500, 'Hard': 1000}
            base_xp = xp_map.get(difficulty, 100)
            
            winner_name = result.get('winner')
            winner_id = name_to_id.get(winner_name)
            
            if winner_id:
                # Winner gets full XP
                GamificationService.add_xp(winner_id, 'battle_win', base_xp)
                result['xp_awarded'] = {winner_name: base_xp}
            elif winner_name == 'Draw':
                # Both get 50%
                half_xp = int(base_xp * 0.5)
                xp_dict = {}
                for pid in room['players']:
                    GamificationService.add_xp(pid, 'battle_draw', half_xp)
                    pname = room['players'][pid]['name']
                    xp_dict[pname] = half_xp
                result['xp_awarded'] = xp_dict
            
            socketio.emit('battle_result', result, room=room_code)
            
            # Trigger Rematch Question
            socketio.emit('battle_chat_message', {
                'sender': 'ByteBot',
                'message': "Do you want another round? (yes / no)",
                'type': 'system'
            }, room=room_code)
            
        except Exception as e:
            print(f"Judging error: {e}")
            socketio.emit('battle_error', {'message': 'AI Referee failed to judge. It\'s a draw!'}, room=room_code)

@socketio.on('battle_rematch_vote')
def on_battle_rematch_vote(data):
    room_code = data.get('room_code')
    vote = data.get('vote') # 'yes' or 'no'
    
    if not room_code or room_code not in battles:
        return
        
    room = battles[room_code]
    room['rematch_votes'][current_user.id] = vote
    
    player_name = room['players'][current_user.id]['name']
    
    # Notify about the vote
    emit('battle_chat_message', {'sender': 'ByteBot', 'message': f"{player_name} voted: {vote.upper()}", 'type': 'system'}, room=room_code)
    
    # If someone votes NO, end immediately (don't wait for both votes)
    if vote == 'no':
        emit('battle_chat_message', {
            'sender': 'ByteBot', 
            'message': f"{player_name} declined rematch. Battle concluded. Thanks for playing! ‘‹",
            'type': 'system'
        }, room=room_code)
        
        # Send event to close modal and return both players to entry screen
        emit('battle_rematch_declined', {}, room=room_code)
        
        # Clean up room from server state
        if room_code in battles:
            del battles[room_code]
        return
    
    # If this person voted YES, notify the other player
    emit('battle_chat_message', {
        'sender': 'ByteBot', 
        'message': f"{player_name} wants a rematch! Waiting for opponent's response...",
        'type': 'system'
    }, room=room_code)
    
    # Check if everyone voted (both said yes)
    if len(room['rematch_votes']) == 2:
        votes = list(room['rematch_votes'].values())
        if all(v == 'yes' for v in votes):
            # Restart
            room['state'] = 'setup'
            room['submissions'] = {}
            room['problem'] = None
            room['config'] = {'difficulty': None, 'language': None}
            room['rematch_votes'] = {}
            
            emit('battle_restart', {}, room=room_code)
            emit('battle_chat_message', {
                'sender': 'ByteBot', 
                'message': "Rematch accepted! ”¥ Host, please choose settings again (Easy/Medium/Hard and Python/Java/C/JavaScript).",
                'type': 'system'
            }, room=room_code)

@socketio.on('battle_heartbeat')
def on_battle_heartbeat(data):
    """Handle heartbeat to keep connection alive and prevent disconnections"""
    if not current_user.is_authenticated:
        return
        
    room_code = data.get('room_code', '').strip().upper()
    if room_code not in battles:
        return
        
    room = battles[room_code]
    if current_user.id in room['players']:
        # Update SID to latest (handles reconnections/refreshes)
        room['players'][current_user.id]['sid'] = request.sid
        print(f"Heartbeat from {current_user.first_name} in {room_code}")

@socketio.on('battle_leave')
def on_battle_leave(data):
    """Host or player leaves - expire room, kick everyone out"""
    if not current_user.is_authenticated:
        return

    room_code = data.get('room_code', '').strip().upper()
    if room_code not in battles:
        return

    room = battles[room_code]
    player_name = room['players'].get(current_user.id, {}).get('name', 'A player')

    # Notify all players in the room that it's closing
    socketio.emit('battle_room_closed', {
        'reason': f"{player_name} left the battle. Room expired."
    }, room=room_code)

    # Delete the room from server state
    del battles[room_code]
    print(f"[Battle] Room {room_code} expired because {player_name} left.")


# Profile management can be extended later (kept simple for this semester project).

# ------------------------------
# FRIENDS & PROFILE LOGIC
# ------------------------------

@app.context_processor
def inject_user_context():
    if current_user.is_authenticated:
        # 1. Focus Buddies
        friends = []
        try:
            friendships = Friendship.query.filter(
                ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)) & 
                (Friendship.status == 'accepted')
            ).all()
            
            for f in friendships:
                fid = f.friend_id if f.user_id == current_user.id else f.user_id
                friend = User.query.get(fid)
                if friend:
                    # Check online status (within 5 mins)
                    is_online = (datetime.utcnow() - (friend.last_seen or datetime.min)) < timedelta(minutes=5)
                    friends.append({
                        'id': friend.id,
                        'name': f"{friend.first_name} {friend.last_name}",
                        'avatar': friend.get_avatar(64),
                        'is_online': is_online,
                        'is_public': friend.is_public_profile,
                        'rank': GamificationService.get_rank(friend.level) if friend.is_public_profile else None,
                        'stats': {'level': friend.level, 'xp': friend.total_xp} if friend.is_public_profile else None
                    })
        except Exception:
            pass # Fail gracefully if table doesn't exist yet
        
        # 2. Sidebar Stats (Rank, Level Progress)
        current_rank = GamificationService.get_rank(current_user.level)
        # XP per level is 500 (from GamificationService)
        xp_per_level = 500
        current_xp_in_level = current_user.total_xp % xp_per_level
        level_progress = int((current_xp_in_level / xp_per_level) * 100)
        xp_remaining = xp_per_level - current_xp_in_level
        
        return dict(
            focus_buddies=friends,
            rank_name=current_rank['name'],
            rank_icon=current_rank['icon'],
            rank_color=current_rank['color'],
            level_progress=level_progress,
            xp_remaining=xp_remaining
        )
    return dict(focus_buddies=[])

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        try:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
        except Exception:
            db.session.rollback()
            pass # Fail silently to prevent request crash

@app.route('/settings/public-profile', methods=['POST'])
@login_required
def toggle_public_profile():
    data = request.get_json()
    current_user.is_public_profile = data.get('is_public', True)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/friends')
@login_required
def friends_page():
    # Helper to format user
    def format_user(u):
        return {
            'id': u.id,
            'name': f"{u.first_name} {u.last_name}",
            'email': u.email,
            'avatar': u.get_avatar(100),
            'level': u.level,
            'rank': GamificationService.get_rank(u.level),
            'is_public': u.is_public_profile
        }

    # 1. My Friends
    accepted = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)) & 
        (Friendship.status == 'accepted')
    ).all()
    my_friends = []
    for f in accepted:
        fid = f.friend_id if f.user_id == current_user.id else f.user_id
        friend = User.query.get(fid)
        if friend:
            my_friends.append(format_user(friend))

    # 2. Friend Requests (Received)
    requests = Friendship.query.filter_by(friend_id=current_user.id, status='pending').all()
    friend_requests = []
    for r in requests:
        sender = User.query.get(r.user_id)
        if sender:
            friend_requests.append({
                'request_id': r.id,
                **format_user(sender)
            })

    return render_template('friends.html', my_friends=my_friends, friend_requests=friend_requests)

@app.route('/call')
@login_required
def call_page():
    room = request.args.get('room')
    if not room:
        return redirect(url_for('friends_page'))
    return render_template('call.html', room=room)

@app.route('/api/users/search')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    # Search by name or email
    users = User.query.filter(
        (User.id != current_user.id) & 
        (
            (User.email.ilike(f"%{query}%")) | 
            (User.first_name.ilike(f"%{query}%")) | 
            (User.last_name.ilike(f"%{query}%"))
        )
    ).limit(10).all()
    
    results = []
    for u in users:
        # Check friendship status
        friendship = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == u.id)) |
            ((Friendship.user_id == u.id) & (Friendship.friend_id == current_user.id))
        ).first()
        
        status = 'none'
        if friendship:
            status = friendship.status
            if status == 'pending' and friendship.friend_id == current_user.id:
                status = 'received' # Request received from this user
            elif status == 'pending' and friendship.user_id == current_user.id:
                status = 'sent' # Request sent to this user
        
        results.append({
            'id': u.id,
            'name': f"{u.first_name} {u.last_name}",
            'email': u.email,
            'avatar': u.get_avatar(64),
            'status': status
        })
        
    return jsonify(results)

@app.route('/friends/request/<int:user_id>', methods=['POST'])
@login_required
def send_friend_request(user_id):
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot add self'}), 400
        
    target = User.query.get(user_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404
        
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)) |
        ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if existing:
        return jsonify({'error': 'Friendship or request already exists'}), 400
        
    req = Friendship(user_id=current_user.id, friend_id=user_id, status='pending')
    db.session.add(req)
    db.session.commit()

    # ”” Notify the target user in real-time via Socket.IO
    try:
        socketio.emit('friend_request_received', {
            'from_id':   current_user.id,
            'from_name': f"{current_user.first_name} {current_user.last_name or ''}".strip(),
            'avatar':    current_user.get_avatar(64),
            'request_id': req.id
        }, room=f"user_{user_id}")
    except Exception:
        pass  # Never break the friend-request flow over a notification error

    return jsonify({'status': 'success'})

@app.route('/friends/accept/<int:request_id>', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    req = Friendship.query.get(request_id)
    if not req or req.friend_id != current_user.id:
        return jsonify({'error': 'Invalid request'}), 404
        
    req.status = 'accepted'
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/friends/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_friend_request(request_id):
    req = Friendship.query.get(request_id)
    if not req or req.friend_id != current_user.id:
        return jsonify({'error': 'Invalid request'}), 404
        
    db.session.delete(req)
    db.session.commit()
    return jsonify({'status': 'success'})

# ------------------------------
# QUIZ SERVICE
# ------------------------------
class QuizService:
    @staticmethod
    def generate_weakness_quiz(user_id: int, **kwargs):
        import random
        
        # 1. Identify Active Syllabus (Context Awareness)
        # By default, use the most recent (Active) syllabus.
        # IF syllabus_id is passed specifically, use that!
        requested_syllabus_id = kwargs.get('syllabus_id')
        
        if requested_syllabus_id:
             active_syllabus_id = requested_syllabus_id
        else:
             active_doc = SyllabusDocument.query.filter_by(user_id=user_id).order_by(SyllabusDocument.created_at.desc()).first()
             active_syllabus_id = active_doc.id if active_doc else None

        # 2. Get Topics from Active Syllabus Tasks
        topics_list = []
        
        if active_syllabus_id:
            # Plan A: Get categories from Todos linked to this syllabus
            # Efficient query for distinct categories in this syllabus
            relevant_todos = (
                db.session.query(Todo.category)
                .filter(Todo.user_id == user_id)
                .filter(Todo.syllabus_id == active_syllabus_id)
                .filter(Todo.category != None)
                .distinct()
                .limit(20)
                .all()
            )
            
            syllabus_categories = [r[0] for r in relevant_todos if r[0]]
            
            # Now, from these categories, which ones are "Weak"?
            if syllabus_categories:
                # Find proficiencies for these specific categories
                prof_records = (
                    TopicProficiency.query
                    .filter_by(user_id=user_id)
                    .filter(TopicProficiency.topic_name.in_(syllabus_categories))
                    .order_by(TopicProficiency.proficiency.asc()) # Lowest first
                    .limit(5)
                    .all()
                )
                
                # Add the weakest ones first
                topics_list.extend([p.topic_name for p in prof_records])
                
                # If we need more, just add random ones from the syllabus
                if len(topics_list) < 3:
                    remaining = list(set(syllabus_categories) - set(topics_list))
                    random.shuffle(remaining)
                    topics_list.extend(remaining[:3])
        
        # Fallback (If no active syllabus or no topics found in it)
        if not topics_list:
            # Fallback to old behavior: Global Weakness
            weak_topics = (
                TopicProficiency.query
                .filter_by(user_id=user_id)
                .filter(TopicProficiency.proficiency < 70)
                .order_by(TopicProficiency.proficiency.asc())
                .limit(5)
                .all()
            )
            topics_list = [t.topic_name for t in weak_topics]

        # Final Fill (if still empty)
        if len(topics_list) < 3:
             if active_syllabus_id:
                  # Force find ANY tasks from this syllabus
                  some_todos = Todo.query.filter_by(user_id=user_id, syllabus_id=active_syllabus_id).limit(20).all()
                  cats = list(set([t.category for t in some_todos if t.category]))
                  topics_list.extend(cats)
             else:
                  topics_list = ["General Study Skills", "Time Management", "Focus"]
        
        # Deduplicate and Limit
        topics_list = list(set(topics_list))[:5]
        if not topics_list:
             topics_list = ["General Knowledge"]

        num_questions = kwargs.get('num_questions', 5)
        difficulty = kwargs.get('difficulty', 'medium')
        
        # 2. Call AI
        # Minimal prompt to save tokens and ensure JSON
        topic_str = ", ".join(topics_list[:3]) # Limit to 3 topics for context
        prompt = (
            f"Create a {num_questions}-question multiple choice quiz testing knowledge on: {topic_str}. "
            f"Difficulty level: {difficulty}. "
            "Focus on identifying weaknesses. "
            "Output strictly valid JSON (no markdown formatting) in this specific format: "
            '{"questions": [{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "topic": "..."}]}'
        )

        messages = [{'role': 'user', 'content': prompt}]
        response_text = call_ai_api(messages)
        
        # 3. Parse JSON
        # Clean potential markdown codes
        clean_text = response_text.replace('```json', '').replace('```', '').strip()
        try:
            data = json.loads(clean_text)
            return data.get('questions', [])
        except json.JSONDecodeError:
            # Fallback or retry? For now, return error or mock
            print(f"Quiz JSON Parse Error: {clean_text}")
            return []

# ------------------------------
# MATCHMAKING SERVICE
# ------------------------------
class MatchmakingService:
    @staticmethod
    def find_matches(user):
        # 1. Get candidates (not self, not already friends)
        subq = db.session.query(Friendship.friend_id).filter(Friendship.user_id == user.id)
        subq2 = db.session.query(Friendship.user_id).filter(Friendship.friend_id == user.id)
        
        candidates = User.query.filter(
            User.id != user.id,
            ~User.id.in_(subq),
            ~User.id.in_(subq2),
            User.is_public_profile == True
        ).limit(50).all()
        
        matches = []
        user_proficiencies = {p.topic_name for p in TopicProficiency.query.filter_by(user_id=user.id).all()}
        
        for candidate in candidates:
            score = 0
            
            # Level Compatibility
            level_diff = abs(user.level - candidate.level)
            if level_diff <= 5:
                score += 20
            elif level_diff <= 10:
                score += 10
                
            # Topic Overlap
            cand_prof = {p.topic_name for p in TopicProficiency.query.filter_by(user_id=candidate.id).all()}
            overlap = user_proficiencies.intersection(cand_prof)
            score += len(overlap) * 10
            
            # Recency
            if candidate.last_seen: 
                 delta = datetime.utcnow() - candidate.last_seen
                 if delta < timedelta(days=1):
                    score += 30 
                 elif delta < timedelta(days=7):
                    score += 10
            
            # Random jitter to keep list fresh if scores are tie
            score += random.randint(0, 5)

            matches.append({
                'user': candidate,
                'score': score,
                'common_topics': list(overlap)[:3]
            })
            
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:5]

@app.route('/api/matches')
@login_required
def get_matches():
    raw_matches = MatchmakingService.find_matches(current_user)
    results = []
    for m in raw_matches:
        u = m['user']
        current_rank = GamificationService.get_rank(u.level)
        results.append({
            'id': u.id,
            'name': f"{u.first_name} {u.last_name}",
            'avatar': u.get_avatar(64),
            'level': u.level,
            'match_score': m['score'],
            'common_topics': m['common_topics'],
            'rank': current_rank
        })
    return jsonify(results)

@app.route('/quiz')
@login_required
def quiz_page():
    return render_template('quiz.html')

@app.route('/api/quiz/generate', methods=['POST'])
@login_required
def quiz_generate():
    data = request.json or {}
    num_questions = int(data.get('num_questions', 5))
    difficulty = data.get('difficulty', 'medium')
    syllabus_id = data.get('syllabus_id') # New field
    
    # Check if user has uploaded any PDF
    has_pdf = SyllabusDocument.query.filter_by(user_id=current_user.id).first()
    if not has_pdf:
        return jsonify({'status': 'error', 'message': 'Please first upload a PDF document in the Syllabus section to generate a quiz.'}), 400
    
    questions = QuizService.generate_weakness_quiz(current_user.id, num_questions=num_questions, difficulty=difficulty, syllabus_id=syllabus_id)
    if not questions:
        # Fallback Mock if AI fails
        questions = [
            {
                "question": "Which technique helps most with procrastination?", 
                "options": ["Pomodoro Technique", "Doom Scrolling", "Multitasking", "Sleeping"], 
                "correct_index": 0, 
                "topic": "Study Skills"
            }
        ]
        # return jsonify({'status': 'error', 'message': 'AI failed to generate quiz.'}), 500
    
    return jsonify({'status': 'success', 'questions': questions})

@app.route('/api/quiz/submit', methods=['POST'])
@login_required
def quiz_submit():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400
        
    answers = data.get('answers', [])
    # answers: [{topic: 'Math', correct: true}, ...]
    
    xp_earned = 0
    correct_count = 0
    
    import random
    
    try:
        for ans in answers:
            is_correct = ans.get('correct', False)
            topic_name = ans.get('topic')
            
            if is_correct:
                correct_count += 1
                xp_earned += 20 # 20 XP per correct answer
                
                # Boost proficiency
                if topic_name:
                    prof = TopicProficiency.query.filter_by(user_id=current_user.id, topic_name=topic_name).first()
                    if not prof:
                        prof = TopicProficiency(user_id=current_user.id, topic_name=topic_name, proficiency=20)
                        db.session.add(prof)
                    else:
                        prof.proficiency = min(100, prof.proficiency + 5)
                        prof.updated_at = datetime.utcnow()
            else:
                 # Lower proficiency slightly?
                 if topic_name:
                    prof = TopicProficiency.query.filter_by(user_id=current_user.id, topic_name=topic_name).first()
                    if prof and prof.proficiency > 5:
                        prof.proficiency = max(0, prof.proficiency - 2)
                        prof.updated_at = datetime.utcnow()

        # Bonus for perfect score
        if correct_count == len(answers) and correct_count > 0:
            xp_earned += 50
            GamificationService.award_badge(current_user, 'Quiz Master')

        # Save XP
        if xp_earned > 0:
            GamificationService.add_xp(current_user.id, 'quiz', xp_earned)
            
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"[quiz_submit] DB error (non-fatal): {e}")
        # Still return success — quiz results are calculated in memory,
        # XP save failure is non-critical (don't crash the user experience)
        xp_earned = 0  # Reset so we don't show incorrect XP

    return jsonify({
        'status': 'success',
        'score': correct_count,
        'xp_earned': xp_earned
    })


# ------------------------------
# WHITEBOARD SOCKET EVENTS
# ------------------------------
@socketio.on('wb_draw')
def handle_wb_draw(data):
    room = data.get('room')
    if room:
        # Broadcast to all in room except sender
        emit('wb_draw', data, room=str(room), broadcast=True, skip_sid=request.sid)

@socketio.on('wb_clear')
def handle_wb_clear(data):
    room = data.get('room')
    if room:
        emit('wb_clear', data, room=str(room), broadcast=True, include_self=True)

@socketio.on('wb_snapshot')
def handle_wb_snapshot(data):
    """Relay a full canvas snapshot (PNG dataURL) to all group members.
    Used by Verse AI to broadcast drawn shapes to collaborators."""
    room = data.get('room')
    if room:
        # Relay to everyone in room EXCEPT the sender (they already have it)
        emit('wb_snapshot', {'snap': data.get('snap', '')},
             room=str(room), broadcast=True, skip_sid=request.sid)

@socketio.on('join')
def on_join(data):
    username = data.get('username')
    room = data.get('room')
    if room:
        join_room(room)

# -----------------
# EVENT API
# -----------------

@app.route('/api/events', methods=['GET', 'POST'])
@login_required
def handle_events():
    if request.method == 'POST':
        data = request.json
        new_event = Event(
            user_id=current_user.id,
            title=data.get('title'),
            description=data.get('description', ''),
            date=data.get('date'),
            time=data.get('time', '')
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Event created successfully!', 'id': new_event.id})

    date_filter = request.args.get('date')
    query = Event.query.filter_by(user_id=current_user.id)
    if date_filter:
        query = query.filter_by(date=date_filter)
    events = query.order_by(Event.date.asc(), Event.time.asc()).all()
    
    return jsonify({
        'status': 'success',
        'events': [{
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'date': e.date,
            'time': e.time,
            'is_notified': e.is_notified
        } for e in events]
    })

@app.route('/api/events/<int:event_id>', methods=['PUT', 'DELETE'])
@login_required
def single_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
        
    if request.method == 'DELETE':
        db.session.delete(event)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Event deleted'})
        
    if request.method == 'PUT':
        data = request.json
        event.title = data.get('title', event.title)
        event.description = data.get('description', event.description)
        event.date = data.get('date', event.date)
        event.time = data.get('time', event.time)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Event updated'})

@app.route('/api/events/check-warnings', methods=['GET'])
@login_required
def check_event_warnings():
    # Get current IST time
    now_ist = datetime.now(IST)
    today_str = now_ist.strftime('%Y-%m-%d')
    current_time_str = now_ist.strftime('%H:%M')
    
    # Find active events for today that have arrived but not notified
    # We check if event.time <= current_time_str
    active_event = Event.query.filter_by(user_id=current_user.id, date=today_str, is_notified=False)\
        .filter(Event.time <= current_time_str)\
        .order_by(Event.time.desc()).first()
    
    return jsonify({
        'status': 'success',
        'has_warning': bool(active_event),
        'event': {
            'id': active_event.id,
            'title': active_event.title,
            'description': active_event.description,
            'time': active_event.time
        } if active_event else None
    })

@app.route('/api/events/<int:event_id>/dismiss', methods=['POST'])
@login_required
def dismiss_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    event.is_notified = True
    db.session.commit()
    return jsonify({'status': 'success'})

def init_db_schema():
    from sqlalchemy import text, inspect
    
    with app.app_context():
        db.create_all()
        
        # Auto-migration for schema updates
        try:
            inspector = inspect(db.engine)
            with db.engine.connect() as conn:
                # 1. Check for file_path in group_chat_message
                if 'group_chat_message' in inspector.get_table_names():
                    columns = [c['name'] for c in inspector.get_columns('group_chat_message')]
                    if 'file_path' not in columns:
                        print("Running migration: Adding file_path to group_chat_message table...")
                        conn.execute(text("ALTER TABLE group_chat_message ADD COLUMN file_path VARCHAR(255)"))
                
                # 2. Check for columns in user table
                if 'user' in inspector.get_table_names():
                    columns = [c['name'] for c in inspector.get_columns('user')]
                    
                    # New Features (Friends/Public Profile)
                    if 'is_public_profile' not in columns:
                        print("Running migration: Adding is_public_profile to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN is_public_profile BOOLEAN DEFAULT TRUE'))
                    if 'last_seen' not in columns:
                        print("Running migration: Adding last_seen to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN last_seen TIMESTAMP'))
                    
                    # Existing checks
                    if 'cover_image' not in columns:
                        print("Running migration: Adding cover_image to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN cover_image VARCHAR(255)'))
                    if 'google_id' not in columns:
                        print("Running migration: Adding google_id to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN google_id VARCHAR(100)'))
                    if 'profile_image' not in columns:
                        print("Running migration: Adding profile_image to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN profile_image VARCHAR(255)'))
                    
                    # Gamification Migrations
                    if 'total_xp' not in columns:
                        print("Running migration: Adding total_xp to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN total_xp INTEGER DEFAULT 0'))
                    if 'level' not in columns:
                        print("Running migration: Adding level to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN level INTEGER DEFAULT 1'))
                    if 'current_streak' not in columns:
                        print("Running migration: Adding current_streak to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN current_streak INTEGER DEFAULT 0'))
                    if 'longest_streak' not in columns:
                        print("Running migration: Adding longest_streak to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN longest_streak INTEGER DEFAULT 0'))
                    if 'last_activity_date' not in columns:
                        print("Running migration: Adding last_activity_date to user table...")
                        conn.execute(text('ALTER TABLE "user" ADD COLUMN last_activity_date DATE'))
                    
                # 3. Check for Todo table updates
                if 'todo' in inspector.get_table_names():
                    columns = [c['name'] for c in inspector.get_columns('todo')]
                    if 'completed_at' not in columns:
                         print("Running migration: Adding completed_at to todo table...")
                         conn.execute(text("ALTER TABLE todo ADD COLUMN completed_at TIMESTAMP"))
                    if 'is_group' not in columns:
                         print("Running migration: Adding is_group to todo table...")
                         conn.execute(text("ALTER TABLE todo ADD COLUMN is_group BOOLEAN DEFAULT FALSE"))
                    if 'category' not in columns:
                         print("Running migration: Adding category to todo table...")
                         conn.execute(text("ALTER TABLE todo ADD COLUMN category VARCHAR(50)"))
                    if 'due_time' not in columns:
                         print("Running migration: Adding due_time to todo table...")
                         conn.execute(text("ALTER TABLE todo ADD COLUMN due_time VARCHAR(20)"))
                    if 'is_notified' not in columns:
                         print("Running migration: Adding is_notified to todo table...")
                         conn.execute(text("ALTER TABLE todo ADD COLUMN is_notified BOOLEAN DEFAULT FALSE"))

                # 4. Check for SyllabusDocument updates
                if 'syllabus_document' in inspector.get_table_names():
                    columns = [c['name'] for c in inspector.get_columns('syllabus_document')]
                    if 'extracted_text' not in columns:
                        print("Running migration: Adding extracted_text to syllabus_document table...")
                        conn.execute(text("ALTER TABLE syllabus_document ADD COLUMN extracted_text TEXT"))
                
                # 4. Create Habit tables if missing (Standard approach)
                # Since we use db.create_all() at startup, this is mainly for verification or alter
                if 'habit' not in inspector.get_table_names():
                    print("Creating habit table...")
                    print("Creating habit table...")
                    db.create_all() 
                        
                conn.commit()
            print("Migration checks completed.")
        except Exception as e:
            print(f"Migration check failed (safe to ignore if new DB): {e}")


# Global scheduler flag to prevent duplicates
SCHEDULER_STARTED = False

def check_task_reminders():
    """
    Background job to check for due tasks and send emails.
    Check every 60 seconds.
    """
    while True:
        try:
            with app.app_context():
                now_utc = datetime.utcnow()
                # IST = UTC + 5:30
                now_ist = now_utc + timedelta(hours=5, minutes=30)
                
                # Format for comparison
                current_date_str = now_ist.strftime('%Y-%m-%d')
                current_time_str = now_ist.strftime('%H:%M')
                
                # Check for tasks due TODAY that haven't been notified
                # Logic: Due Date is today AND (Time is approaching OR Time is null)
                # Specific logic: Notify if Due Time is within next 1 hour
                
                # Query all un-notified tasks due today
                upcoming_tasks = Todo.query.filter(
                    Todo.due_date == current_date_str,
                    Todo.completed == False,
                    Todo.is_notified == False
                ).all()
                
                for task in upcoming_tasks:
                    should_notify = False
                    
                    if not task.due_time:
                        # All-day task: Notify at 9 AM or immediately if created later
                        # For simplicity, we can notify immediately if it's today
                        should_notify = True 
                    else:
                        # Time-specific task
                        # Convert due_time (HH:MM) to numeric or simplified compare
                        # Simple compare: Notify if Current Time < Due Time <= Current Time + 1 Hour
                         try:
                            # Simple string comparison works for HH:MM 24h format
                            # Notify if we are past the time or close to it?
                            # Users asked for: "due date is now due" -> alert
                            
                            # Let's alert if current time is >= due time (it's due!)
                            # OR slightly before? Lets say 15 mins before or ON time.
                            # For robustness: Alert if Current Time >= Due Time
                            
                            if current_time_str >= task.due_time:
                                should_notify = True
                                
                         except Exception:
                             pass
                             
                    if should_notify:
                        # Fetch user manually if needed, or use relationship
                        user = User.query.get(task.user_id)
                        if user and user.email:
                            print(f"Sending reminder for task {task.id} to {user.email}")
                            sent = send_task_reminder_email(
                                user.email, 
                                user.first_name, 
                                task.title, 
                                task.due_date, 
                                task.due_time
                            )
                            if sent:
                                task.is_notified = True
                                db.session.commit()
                                
        except Exception as e:
            print(f"Scheduler Error: {e}")
            
        # Sleep for 60 seconds
        socketio.sleep(60)

# IMPORTANT: Order matters. Define logic, THEN run schema check and updates.
try:
    init_db_schema()
    print(" DB schema initialized successfully.")
except Exception as _db_init_err:
    print(f"š  DB init warning (app will still start): {_db_init_err}")

@app.route('/fix-db-schema')
def fix_db_schema():
    """Manual trigger to fix DB schema in production."""
    try:
        from sqlalchemy import text
        with db.engine.connect(
            
        ) as conn:
            # Postgres specific: Try adding the column directly
            try:
                conn.execute(text("ALTER TABLE todo ADD COLUMN IF NOT EXISTS syllabus_id INTEGER REFERENCES syllabus_document(id)"))
                conn.commit()
                return "Schema updated safely (Added syllabus_id)."
            except Exception as e:
                return f"Error executing ALTER: {str(e)}"
    except Exception as e:
        return f"Database connection error: {str(e)}"


# ============================================================================
# ADMIN PANEL ROUTES
# ============================================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with overview statistics"""
    # Calculate stats manually to safely exclude admins
    
    # 1. Total Users (excluding admins)
    total_users = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).count()
    
    # 2. Active Users (excluding admins AND banned users)
    active_users = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com',
        User.is_banned == False
    ).count()
    
    # 3. Total XP Awarded (from non-admin users)
    total_xp = db.session.query(db.func.sum(User.total_xp)).filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).scalar() or 0
    
    # Helper to format large numbers
    def format_number(num):
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        if num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
        
    # 4. Open Tickets
    open_tickets = SupportTicket.query.filter(SupportTicket.status.in_(['open', 'in_progress'])).count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'xp_awarded': format_number(int(total_xp)),
        'open_tickets': open_tickets
    }
    
    # Recent activity
    recent_users = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users)

# ============================================================================
# ADMIN - USER MANAGEMENT
# ============================================================================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """List all users with search and filter"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    filter_type = request.args.get('filter', 'all')
    
    # Filter base query - exclude admins
    # Filter base query - exclude admins
    query = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    )
    
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    
    if filter_type == 'active':
        query = query.filter(User.last_seen >= datetime.utcnow() - timedelta(days=7))
    elif filter_type == 'banned':
        query = query.filter(User.is_banned == True)
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/users/list.html', users=users, search=search, filter_type=filter_type)

@app.route('/admin/user-activity')
@login_required
@admin_required
def admin_user_activity():
    """Admin view for user presence and recent activity."""
    # Define threshold for "offline"
    threshold = datetime.utcnow() - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    
    # Fetch actually online users (in set AND seen recently)
    active_users = []
    if online_users:
        active_users = User.query.filter(
            User.id.in_(online_users), 
            User.last_seen >= threshold,
            User.is_admin == False
        ).all()
        # Prune stale IDs from set
        active_ids = {u.id for u in active_users}
        online_users.intersection_update(active_ids)
        
    # Format current time to IST helper
    def format_ist(dt):
        if not dt: return "Never"
        if dt.tzinfo is None:
            dt = utc.localize(dt)
        ist_dt = dt.astimezone(IST)
        
        # If it was today, just show time. If yesterday, "Yesterday at ...". Else "DD MMM at ..."
        now = datetime.now(IST)
        if ist_dt.date() == now.date():
            return f"Today at {ist_dt.strftime('%I:%M %p')}"
        elif (now.date() - ist_dt.date()).days == 1:
            return f"Yesterday at {ist_dt.strftime('%I:%M %p')}"
        return ist_dt.strftime('%d %b at %I:%M %p')

    # All regular users sorted by last_seen
    page = request.args.get('page', 1, type=int)
    all_users = User.query.filter(User.is_admin == False).order_by(db.desc(User.last_seen)).paginate(page=page, per_page=30, error_out=False)
    
    unread_support_count = SupportTicket.query.filter_by(status='open').count()
    
    return render_template('admin/user_activity.html', 
                          active_users=active_users, 
                          all_users=all_users,
                          format_ist=format_ist,
                          unread_support_count=unread_support_count)

@app.route('/admin/users/<int:user_id>')
@login_required
@admin_required
def admin_user_detail(user_id):
    """View detailed user information"""
    user = User.query.get_or_404(user_id)
    
    # Get user statistics
    total_tasks = Todo.query.filter_by(user_id=user.id).count()
    completed_tasks = Todo.query.filter_by(user_id=user.id, completed=True).count()
    total_pdfs = SyllabusDocument.query.filter_by(user_id=user.id).count()
    
    # Recent XP activity
    recent_xp = XPHistory.query.filter_by(user_id=user.id).order_by(XPHistory.timestamp.desc()).limit(10).all()
    
    return render_template('admin/users/detail.html',
                         user=user,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         total_pdfs=total_pdfs,
                         recent_xp=recent_xp)

@app.route('/admin/users/<int:user_id>/ban', methods=['POST'])
@login_required
@admin_required
def admin_ban_user(user_id):
    """Ban a user - Prevents admin from banning himself"""
    # PREVENT ADMIN FROM BANNING HIMSELF
    if user_id == current_user.id:
        flash('You cannot ban yourself!', 'error')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    
    reason = request.form.get('reason', 'No reason provided')
    
    try:
        AdminService.ban_user(user_id, reason, current_user.id)
        flash('User banned successfully', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/users/<int:user_id>/unban', methods=['POST'])
@login_required
@admin_required
def admin_unban_user(user_id):
    """Unban a user"""
    try:
        AdminService.unban_user(user_id, current_user.id)
        flash('User unbanned successfully', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin_user_detail', user_id=user_id))


@app.route('/admin/users/<int:user_id>/alert', methods=['POST'])
@login_required
@admin_required
def admin_alert_user(user_id):
    """Send an admin alert/warning message to a user's support inbox."""
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    if not subject or not message:
        flash('Subject and message are required.', 'error')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    try:
        SupportService.send_admin_notification(
            user_id=user_id,
            admin_id=current_user.id,
            subject=subject,
            message=message,
            category='admin_alert'
        )
        flash(f'Alert sent to user successfully.', 'success')
    except Exception as e:
        flash(f'Error sending alert: {str(e)}', 'error')
    return redirect(url_for('admin_user_detail', user_id=user_id))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Permanently delete a user"""
    if user_id == current_user.id:
        flash('You cannot delete yourself!', 'error')
        return redirect(url_for('admin_users'))
        
    try:
        AdminService.delete_user(user_id, current_user.id)
        flash('User account permanently deleted', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
        
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/adjust-xp', methods=['POST'])
@login_required
@admin_required
def admin_adjust_xp(user_id):
    """Manually adjust user XP"""
    amount = request.form.get('amount', type=int)
    reason = request.form.get('reason', 'Admin adjustment')
    
    if not amount:
        flash('Invalid XP amount', 'error')
        return redirect(url_for('admin_user_detail', user_id=user_id))
    
    try:
        user = User.query.get_or_404(user_id)
        user.total_xp = max(0, user.total_xp + amount)
        user.level = GamificationService.calculate_level(user.total_xp)
        
        # Log XP change
        xp_log = XPHistory(user_id=user.id, source='admin', amount=amount)
        db.session.add(xp_log)
        
        # Log admin action (no commit inside)
        AdminService.log_action(
            admin_id=current_user.id,
            action='adjust_xp',
            target_type='user',
            target_id=user_id,
            details={'amount': amount, 'reason': reason}
        )
        
        # Notify user via Support System (no commit inside)
        action_type = "added" if amount > 0 else "removed"
        try:
            SupportService.send_admin_notification(
                user_id=user.id,
                admin_id=current_user.id,
                subject="System Notification: XP Adjusted",
                message=f"Admin has {action_type} {abs(amount)} XP {'to' if amount > 0 else 'from'} your account.\n\nReason given: {reason}"
            )
        except Exception as notify_err:
            print(f"XP notification error (non-critical): {notify_err}")
        
        # Single commit for everything
        db.session.commit()
        flash(f'XP adjusted by {amount:+d}', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error adjusting XP for user {user_id}: {e}")
        flash(f'Error adjusting XP: {str(e)}', 'error')
    
    return redirect(url_for('admin_user_detail', user_id=user_id))

# ============================================================================
# ADMIN - SUPPORT TICKETS
# ============================================================================

@app.route('/admin/support')
@login_required
@admin_required
def admin_support():
    """List all support tickets for admin"""
    status   = request.args.get('status', 'all')
    category = request.args.get('category', None)
    # When filtering by category, fetch all statuses unless status also specified
    tickets = SupportService.get_admin_tickets(
        status_filter=status if not category else None,
        category_filter=category
    )
    return render_template('admin/support/list.html',
                           tickets=tickets,
                           current_status=status,
                           current_category=category)

@app.route('/admin/support/<int:ticket_id>')
@login_required
@admin_required
def admin_support_detail(ticket_id):
    """View and respond to support ticket"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    user = User.query.get(ticket.user_id)
    
    # Mark as read by admin
    unread_msgs = SupportMessage.query.filter_by(
        ticket_id=ticket.id, 
        read_by_admin=False,
        is_admin=False # Messages from user
    ).all()
    for msg in unread_msgs:
        msg.read_by_admin = True
    
    if unread_msgs:
        ticket.admin_unread_count = 0
        db.session.commit()
    
    messages = SupportMessage.query.filter_by(ticket_id=ticket.id).order_by(SupportMessage.created_at.asc()).all()
    return render_template('admin/support/detail.html', ticket=ticket, user=user, messages=messages)

@app.route('/admin/support/<int:ticket_id>/reply', methods=['POST'])
@login_required
@admin_required
def admin_support_reply(ticket_id):
    """Admin replies to a support ticket"""
    message = request.form.get('message')
    if not message:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('admin_support_detail', ticket_id=ticket_id))
        
    SupportService.add_message(ticket_id, current_user.id, message, is_admin=True)
    return redirect(url_for('admin_support_detail', ticket_id=ticket_id))

@app.route('/admin/support/<int:ticket_id>/close', methods=['POST'])
@login_required
@admin_required
def admin_support_close(ticket_id):
    """Close a support ticket"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    ticket.status = 'closed'
    ticket.closed_at = datetime.utcnow()
    db.session.commit()
    flash('Ticket closed successfully', 'success')
    return redirect(url_for('admin_support'))

# ============================================================================


# ============================================================================
# ADMIN - AUDIT LOGS
# ============================================================================

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """View admin action audit logs"""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', 'all')
    
    query = AdminAction.query
    
    if action_filter != 'all':
        query = query.filter(AdminAction.action == action_filter)
    
    logs = query.order_by(AdminAction.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/logs/list.html', logs=logs, action_filter=action_filter)


# ============================================================================
# ADMIN - GAMIFICATION MANAGEMENT
# ============================================================================

@app.route('/admin/gamification')
@login_required
@admin_required
def admin_gamification():
    """Manage gamification settings"""
    # Get XP stats
    total_xp = db.session.query(db.func.sum(User.total_xp)).scalar() or 0
    avg_xp = db.session.query(db.func.avg(User.total_xp)).scalar() or 0
    max_level = db.session.query(db.func.max(User.level)).scalar() or 0
    avg_level = db.session.query(db.func.avg(User.level)).scalar() or 0
    
    # Top users by XP (excluding admins)
    # Top users by XP (excluding admins)
    top_users = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).order_by(User.total_xp.desc()).limit(10).all()
    
    # Recent XP transactions
    recent_xp = XPHistory.query.order_by(XPHistory.timestamp.desc()).limit(20).all()
    
    # Badge statistics
    total_badges = Badge.query.count()
    total_earned = UserBadge.query.count()
    
    # Most earned badges
    from sqlalchemy import func
    popular_badges = db.session.query(
        Badge, func.count(UserBadge.id).label('count')
    ).join(UserBadge).group_by(Badge.id).order_by(func.count(UserBadge.id).desc()).limit(5).all()
    
    stats = {
        'total_xp': int(total_xp),
        'avg_xp': round(avg_xp, 1),
        'max_level': max_level,
        'avg_level': round(avg_level, 1),
        'total_badges': total_badges,
        'total_earned': total_earned,
        'top_users': top_users,
        'recent_xp': recent_xp,
        'popular_badges': popular_badges
    }
    
    return render_template('admin/gamification/dashboard.html', stats=stats)


# ============================================================================
# ADMIN - SHOP MANAGEMENT
# ============================================================================

@app.route('/admin/shop')
@login_required
@admin_required
def admin_shop():
    """Manage shop items and themes"""
    # Get all purchased items
    purchased_items = UserItem.query.all()
    
    # Group by item_id to get counts
    from sqlalchemy import func
    item_stats = db.session.query(
        UserItem.item_id,
        func.count(UserItem.id).label('purchase_count')
    ).group_by(UserItem.item_id).order_by(func.count(UserItem.id).desc()).all()
    
    # Total purchases
    total_purchases = UserItem.query.count()
    unique_items = len(item_stats)
    active_items = UserItem.query.filter_by(is_active=True).count()
    
    # Recent purchases
    recent_purchases = UserItem.query.order_by(UserItem.purchased_at.desc()).limit(20).all()
    
    stats = {
        'total_purchases': total_purchases,
        'unique_items': unique_items,
        'active_items': active_items,
        'item_stats': item_stats,
        'recent_purchases': recent_purchases
    }
    
    return render_template('admin/shop/dashboard.html', stats=stats)





# ============================================================================
# ADMIN - BATTLES MANAGEMENT (Study Sessions)
# ============================================================================

@app.route('/admin/battles')
@login_required
@admin_required
def admin_battles():
    """Manage study sessions (battles)"""
    page = request.args.get('page', 1, type=int)
    
    # Use study sessions as "battles"
    sessions = StudySession.query.order_by(StudySession.completed_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # Get stats
    total_sessions = StudySession.query.count()
    total_focus_time = db.session.query(db.func.sum(StudySession.duration)).filter_by(mode='focus').scalar() or 0
    total_break_time = db.session.query(db.func.sum(StudySession.duration)).filter(StudySession.mode.in_(['shortBreak', 'longBreak'])).scalar() or 0
    
    # Top studiers
    from sqlalchemy import func
    top_studiers = db.session.query(
        User, func.sum(StudySession.duration).label('total_time')
    ).join(StudySession).filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).group_by(User.id).order_by(func.sum(StudySession.duration).desc()).limit(10).all()
    
    stats = {
        'total_sessions': total_sessions,
        'total_focus_hours': round(total_focus_time / 60, 1),
        'total_break_hours': round(total_break_time / 60, 1),
        'top_studiers': top_studiers
    }
    
    return render_template('admin/battles/list.html', sessions=sessions, stats=stats)


# ============================================================================
# ADMIN - ANALYTICS
# ============================================================================

@app.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    """View system analytics"""
    from datetime import timedelta
    
    # User growth (excluding admins to match total users)
    new_users_30d = User.query.filter(
        User.is_admin == False,
        User.email != 'admin@studyverse.com',
        User.email != 'admin@studyversefinal.com'
    ).count()
    
    # Activity stats
    total_messages = ChatMessage.query.count() + GroupChatMessage.query.count()
    total_tasks = Todo.query.count()
    completed_tasks = Todo.query.filter_by(completed=True).count()
    
    # Study sessions
    total_sessions = StudySession.query.count()
    total_study_time = db.session.query(db.func.sum(StudySession.duration)).scalar() or 0
    
    # Group activity
    total_groups = Group.query.count()
    total_group_members = GroupMember.query.count()
    
    # XP activity
    total_xp_earned = db.session.query(db.func.sum(XPHistory.amount)).filter(XPHistory.amount > 0).scalar() or 0
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = User.query.filter(User.created_at >= seven_days_ago).count()
    recent_sessions = StudySession.query.filter(StudySession.completed_at >= seven_days_ago).count()
    recent_tasks = Todo.query.filter(Todo.created_at >= seven_days_ago).count()
    
    stats = {
        'new_users_30d': new_users_30d,
        'total_messages': total_messages,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0,
        'total_sessions': total_sessions,
        'total_study_hours': round(total_study_time / 60, 1),
        'total_groups': total_groups,
        'total_group_members': total_group_members,
        'total_xp_earned': int(total_xp_earned),
        'recent_users_7d': recent_users,
        'recent_sessions_7d': recent_sessions,
        'recent_tasks_7d': recent_tasks
    }
    
    return render_template('admin/analytics/dashboard.html', stats=stats)



# ============================================================================
# ONE-TIME MIGRATION ROUTE (For Render Deployment)
# ============================================================================

@app.route('/setup-admin-panel-once')
def setup_admin_panel_once():
    """
    ONE-TIME SETUP ROUTE for Render deployment
    
    This route runs the database migration and creates the admin account.
    Visit this URL ONCE after deploying to Render, then it will be disabled.
    
    IMPORTANT: This route is protected and will only work if no admin exists yet.
    """
    try:
        # Check if admin already exists
        existing_admin = User.query.filter_by(email='admin@studyversefinal.com').first()
        
        if existing_admin and existing_admin.is_admin:
            return """
            <html>
            <head>
                <title>Admin Panel Already Setup</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 600px; margin: 100px auto; padding: 20px; background: #0f172a; color: #e2e8f0; }
                    .container { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
                    h1 { color: #10b981; margin-bottom: 20px; }
                    .info { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 16px; border-radius: 8px; margin: 20px 0; }
                    a { color: #3b82f6; text-decoration: none; font-weight: 600; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1> Admin Panel Already Setup!</h1>
                    <div class="info">
                        <p><strong>Admin account already exists and is ready to use.</strong></p>
                        <p>Email: <code>admin@studyversefinal.com</code></p>
                    </div>
                    <p>You can now:</p>
                    <ol>
                        <li><a href="/">Go to homepage</a></li>
                        <li>Login with admin credentials</li>
                        <li><a href="/admin">Access admin panel</a></li>
                    </ol>
                    <p style="margin-top: 30px; color: #94a3b8; font-size: 14px;">
                        This setup route is now disabled since admin already exists.
                    </p>
                </div>
            </body>
            </html>
            """
        
        # Run migration
        migration_log = []
        
        # Add columns to User table
        with db.engine.connect() as conn:
            try:
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"))
                migration_log.append(" Added is_admin column")
            except Exception as e:
                migration_log.append(f"š  is_admin: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE"))
                migration_log.append(" Added is_banned column")
            except Exception as e:
                migration_log.append(f"š  is_banned: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS ban_reason TEXT"))
                migration_log.append(" Added ban_reason column")
            except Exception as e:
                migration_log.append(f"š  ban_reason: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS banned_at TIMESTAMP"))
                migration_log.append(" Added banned_at column")
            except Exception as e:
                migration_log.append(f"š  banned_at: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS banned_by INTEGER"))
                migration_log.append(" Added banned_by column")
            except Exception as e:
                migration_log.append(f"š  banned_by: {str(e)[:50]}")
            
            conn.commit()
        
        # Add columns to SyllabusDocument table
        with db.engine.connect() as conn:
            try:
                conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN IF NOT EXISTS file_path VARCHAR(255)"))
                migration_log.append(" Added file_path column")
            except Exception as e:
                migration_log.append(f"š  file_path: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN IF NOT EXISTS file_size INTEGER"))
                migration_log.append(" Added file_size column")
            except Exception as e:
                migration_log.append(f"š  file_size: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(20) DEFAULT 'pending'"))
                migration_log.append(" Added extraction_status column")
            except Exception as e:
                migration_log.append(f"š  extraction_status: {str(e)[:50]}")
            
            try:
                conn.execute(db.text("ALTER TABLE syllabus_document ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
                migration_log.append(" Added is_active column")
            except Exception as e:
                migration_log.append(f"š  is_active: {str(e)[:50]}")
            
            conn.commit()
        
        # Create AdminAction table
        try:
            db.create_all()
            migration_log.append(" Created AdminAction table")
        except Exception as e:
            migration_log.append(f"š  AdminAction table: {str(e)[:50]}")
        
        # Create admin account
        from werkzeug.security import generate_password_hash
        
        admin_user = User(
            email='admin@studyversefinal.com',
            password_hash=generate_password_hash('adminfinal@12345'),
            first_name='Admin',
            last_name='User',
            is_admin=True,
            total_xp=0,
            level=1
        )
        db.session.add(admin_user)
        db.session.commit()
        
        migration_log.append(" Created admin account")
        
        # Return success page
        return f"""
        <html>
        <head>
            <title>Admin Panel Setup Complete</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #0f172a; color: #e2e8f0; }}
                .container {{ background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }}
                h1 {{ color: #10b981; margin-bottom: 20px; }}
                .success {{ background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 16px; border-radius: 8px; margin: 20px 0; }}
                .credentials {{ background: #334155; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .log {{ background: #1e293b; padding: 16px; border-radius: 8px; font-family: monospace; font-size: 13px; margin: 20px 0; max-height: 300px; overflow-y: auto; }}
                code {{ background: #334155; padding: 4px 8px; border-radius: 4px; color: #3b82f6; }}
                a {{ color: #3b82f6; text-decoration: none; font-weight: 600; }}
                a:hover {{ text-decoration: underline; }}
                .warning {{ background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; padding: 16px; border-radius: 8px; margin: 20px 0; color: #f59e0b; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>‰ Admin Panel Setup Complete!</h1>
                
                <div class="success">
                    <strong> Database migration successful!</strong><br>
                    <strong> Admin account created!</strong>
                </div>
                
                <div class="credentials">
                    <h3 style="margin-top: 0; color: #e2e8f0;">Admin Credentials:</h3>
                    <p><strong>Email:</strong> <code>admin@studyversefinal.com</code></p>
                    <p><strong>Password:</strong> <code>adminfinal@12345</code></p>
                </div>
                
                <div class="warning">
                    <strong>š  IMPORTANT:</strong> Change your admin password after first login for security!
                </div>
                
                <h3>Next Steps:</h3>
                <ol>
                    <li><a href="/">Go to homepage</a></li>
                    <li>Click "Sign In"</li>
                    <li>Login with admin credentials above</li>
                    <li><a href="/admin">Access admin panel</a></li>
                </ol>
                
                <h3>Migration Log:</h3>
                <div class="log">
                    {'<br>'.join(migration_log)}
                </div>
                
                <p style="margin-top: 30px; color: #94a3b8; font-size: 14px;">
                    This setup route will be disabled on next visit since admin account now exists.
                </p>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        return f"""
        <html>
        <head>
            <title>Setup Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #0f172a; color: #e2e8f0; }}
                .container {{ background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }}
                h1 {{ color: #ef4444; margin-bottom: 20px; }}
                .error {{ background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; padding: 16px; border-radius: 8px; margin: 20px 0; }}
                pre {{ background: #0f172a; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Œ Setup Error</h1>
                <div class="error">
                    <strong>An error occurred during setup:</strong>
                    <pre>{str(e)}</pre>
                </div>
                <h3>Full Error Trace:</h3>
                <pre>{error_trace}</pre>
                <p>Please contact support or try running the migration manually using Render Shell.</p>
            </div>
        </body>
        </html>
        """



# ============================================================================
# AI TOPIC RESOLVER  Routes
# ============================================================================

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

@app.route('/topic-resolver')
@login_required
def topic_resolver():
    """Main AI Topic Resolver page  shows weak topics as quick picks."""
    # Fetch user's weak topics (proficiency < 60) ordered by lowest first
    weak_topics = TopicProficiency.query.filter_by(
        user_id=current_user.id
    ).filter(
        TopicProficiency.proficiency < 60
    ).order_by(TopicProficiency.proficiency.asc()).limit(6).all()

    return render_template('topic_resolver.html', weak_topics=weak_topics)


@app.route('/api/topic-resolver/explain', methods=['POST'])
@login_required
def topic_resolver_explain():
    """
    AI Explanation endpoint  uses Gemini to generate a structured deep-dive.
    Returns: explanation, key_points, common_mistakes, memory_trick, youtube_query, summary
    """
    data = request.get_json()
    topic = (data or {}).get('topic', '').strip()
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    if not GEMINI_AVAILABLE or not AI_API_KEY:
        return jsonify({'error': 'AI service not configured'}), 503

    try:
        prompt = f"""You are an expert tutor. A student is struggling with: "{topic}"

Generate a structured learning breakdown in JSON format:

{{
  "subtitle": "A one-line description of the topic",
  "explanation": "A clear, friendly 3-4 sentence explanation of the concept. Use simple analogies.",
  "key_points": ["Key point 1", "Key point 2", "Key point 3", "Key point 4"],
  "common_mistakes": "The most common mistake students make with this topic in 1-2 sentences.",
  "memory_trick": "A memorable trick, mnemonic, or analogy to remember this concept.",
  "youtube_query": "A specific YouTube search query to find the best tutorial video on this topic",
  "summary": "A 10-word summary of the topic for image generation"
}}

Return ONLY valid JSON. No markdown, no extra text."""

        resp = gemini_rotator.generate_content(AI_MODEL, prompt)
        raw = resp.text.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]

        result = json.loads(raw.strip())
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'explanation': f'This topic covers important concepts that require careful study. Break it down into smaller parts and practice regularly.',
            'key_points': ['Understand the core definition', 'Practice with examples', 'Review related concepts', 'Test yourself regularly'],
            'common_mistakes': 'Students often rush through this topic without building a solid foundation.',
            'memory_trick': 'Connect this concept to something you already know well.',
            'youtube_query': topic + ' explained tutorial',
            'summary': topic,
            'subtitle': 'AI-powered deep dive - YouTube curated videos - Visual diagram'
        })


@app.route('/api/topic-resolver/videos', methods=['POST'])
@login_required
def topic_resolver_videos():
    """
    YouTube video search endpoint  returns top educational videos for a topic.
    Uses YouTube Data API v3.
    """
    data = request.get_json()
    topic = (data or {}).get('topic', '').strip()
    search_query = (data or {}).get('search_query', topic).strip()

    if not topic:
        return jsonify({'videos': [], 'error': 'Topic required'}), 400

    if not YOUTUBE_API_KEY:
        return jsonify({'videos': [], 'error': 'YouTube API not configured'}), 200

    try:
        # Build optimised search query (educational focus)
        educational_query = f"{search_query} explained tutorial"

        # YouTube Data API v3 search
        yt_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': educational_query,
            'type': 'video',
            'maxResults': 5,
            'relevanceLanguage': 'en',
            'videoDuration': 'medium',        # 4€“20 min (ideal for tutorials)
            'videoDefinition': 'high',
            'key': YOUTUBE_API_KEY,
            'safeSearch': 'strict',
        }

        resp = requests.get(yt_url, params=params, timeout=8)
        resp.raise_for_status()
        yt_data = resp.json()

        video_ids = [item['id']['videoId'] for item in yt_data.get('items', [])]

        # Fetch video statistics (view count) and content details (duration)
        videos_info = []
        if video_ids:
            details_url = "https://www.googleapis.com/youtube/v3/videos"
            detail_params = {
                'part': 'contentDetails,statistics',
                'id': ','.join(video_ids),
                'key': YOUTUBE_API_KEY,
            }
            detail_resp = requests.get(details_url, params=detail_params, timeout=8)
            detail_resp.raise_for_status()
            detail_data = {v['id']: v for v in detail_resp.json().get('items', [])}

            for item in yt_data.get('items', []):
                vid_id = item['id']['videoId']
                snippet = item['snippet']
                details = detail_data.get(vid_id, {})

                # Parse ISO 8601 duration (PT4M13S †’ 4:13)
                duration_raw = details.get('contentDetails', {}).get('duration', '')
                duration_str = _parse_yt_duration(duration_raw)

                # Format view count
                view_count = details.get('statistics', {}).get('viewCount', '')
                views_str = _format_view_count(view_count)

                # Best thumbnail
                thumbs = snippet.get('thumbnails', {})
                thumb = (thumbs.get('high') or thumbs.get('medium') or thumbs.get('default') or {}).get('url', '')

                videos_info.append({
                    'id': vid_id,
                    'title': snippet.get('title', ''),
                    'channel': snippet.get('channelTitle', ''),
                    'thumbnail': thumb,
                    'duration': duration_str,
                    'views': views_str,
                })

        return jsonify({'videos': videos_info})

    except Exception as e:
        print(f"YouTube API error: {e}")
        return jsonify({'videos': [], 'error': str(e)}), 200


def _parse_yt_duration(iso_duration):
    """Convert ISO 8601 duration PT4M13S to 4:13"""
    if not iso_duration:
        return ''
    import re as _re
    match = _re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return ''
    h, m, s = match.groups()
    h = int(h or 0); m = int(m or 0); s = int(s or 0)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_view_count(count_str):
    """Format raw view count: 1234567 †’ 1.2M"""
    try:
        n = int(count_str)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M views"
        if n >= 1_000:
            return f"{n/1_000:.0f}K views"
        return f"{n} views"
    except Exception:
        return ''


@app.route('/api/topic-resolver/diagram', methods=['POST'])
@login_required
def topic_resolver_diagram():
    """
    AI Diagram generation endpoint.
    Uses Gemini to generate an educational visual description or image.
    Falls back to Gemini text diagram if image unavailable.
    """
    data = request.get_json()
    topic = (data or {}).get('topic', '').strip()
    description = (data or {}).get('description', topic).strip()

    if not topic:
        return jsonify({'error': 'Topic required'}), 400

    if not GEMINI_AVAILABLE or not AI_API_KEY:
        return jsonify({'description': 'AI diagram service not available.'}), 200

    try:
        # Try Gemini image generation model (rotator handles quota failover)
        image_prompt = (
            f"Create a clean, educational diagram or concept map for the topic: '{topic}'. "
            f"The diagram should be: labeled clearly, use arrows and boxes, show relationships, "
            f"use a dark background with colourful labels, academic style, no text clutter. "
            f"Similar to a textbook figure or Khan Academy illustration."
        )
        image_response = gemini_rotator.generate_content(
            'gemini-2.0-flash-preview-image-generation',
            image_prompt,
            generation_config={"response_modalities": ["image", "text"]}
        )

        # Extract image from response
        for part in image_response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                import base64 as _b64
                image_data = part.inline_data.data
                mime = part.inline_data.mime_type or 'image/png'
                data_uri = f"data:{mime};base64,{_b64.b64encode(image_data).decode()}"
                return jsonify({'image_url': data_uri})

    except Exception as img_err:
        print(f"Image generation failed: {img_err}")

    # Fallback: use Gemini to generate a text-based ASCII/structured diagram description
    try:
        fallback_prompt = f"""Create a clear structured text diagram or concept map for: "{topic}"



IMPORTANT: Use ONLY plain ASCII characters (no Unicode, no special symbols).

Allowed: letters, digits, spaces, + - | / \\ > < ^ v = _ ( ) [ ] and newlines.

Use + for corners, - for horizontal lines, | for vertical lines.

Use --> or -> or the letter v for downward arrows.

Do NOT use any Unicode box-drawing or arrow characters.



Example format:

+--------------------+

|       TOPIC        |

+--------------------+

         |

         v

+----------+    +----------+

| Concept A|    | Concept B|

+----------+    +----------+

    |                |

    v                v

[Detail 1]       [Detail 2]



Make it educational and concise. Max 30 lines."""

        fb_resp = gemini_rotator.generate_content(AI_MODEL, fallback_prompt)
        return jsonify({'description': fb_resp.text.strip()})
    except Exception as fb_err:
        return jsonify({'description': f'Diagram generation unavailable for: {topic}'}), 200


@app.route('/api/topic-resolver/award-xp', methods=['POST'])
@login_required
def topic_resolver_award_xp():
    """Award XP for using the Topic Resolver feature."""
    try:
        result = GamificationService.add_xp(current_user.id, 'topic_resolver', 15)
        GamificationService.update_streak(current_user.id)
        earned = (result or {}).get('earned', 15) if result else 15
        return jsonify({'earned': earned if earned > 0 else 15})
    except Exception:
        return jsonify({'earned': 0})


# ============================================================================

# ============================================================================
# AI PHOTO QUESTION SOLVER  Routes
# ============================================================================

@app.route('/photo-solver')
@login_required
def photo_solver():
    """AI Photo Question Solver page."""
    return render_template('photo_solver.html')


@app.route('/api/photo-solver/solve', methods=['POST'])
@login_required
def photo_solver_solve():
    """
    Solve a question from an uploaded image using Gemini Vision (multimodal).
    Accepts: multipart/form-data with 'image' field.
    Returns: JSON with steps, final_answer, subject, topic, difficulty, concepts.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    img_file = request.files['image']
    if img_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    # Read image bytes and determine MIME type
    img_bytes = img_file.read()
    mime_type = img_file.content_type or 'image/jpeg'
    # Limit to 10 MB
    if len(img_bytes) > 10 * 1024 * 1024:
        return jsonify({'error': 'Image too large. Maximum 10MB.'}), 400

    if not GEMINI_AVAILABLE or not AI_API_KEY:
        return jsonify({'error': 'AI service not configured'}), 503

    try:
        import base64 as _b64

        # Encode image for Gemini multimodal input
        image_data = {
            'mime_type': mime_type,
            'data': _b64.b64encode(img_bytes).decode('utf-8')
        }

        prompt = """You are an expert academic tutor. Carefully look at this image which contains a question or problem.

Analyse and solve it completely. Return your response as valid JSON with this EXACT structure:

{
  "question_preview": "A short 1-sentence description of what the question is about",
  "subject": "Subject name (e.g. Mathematics, Physics, Chemistry, Biology, History, etc.)",
  "topic": "Specific topic (e.g. Integration by Parts, Newton's Laws, Organic Chemistry)",
  "difficulty": "Easy / Medium / Hard",
  "steps": [
    {
      "title": "Step title (e.g. Identify the formula)",
      "detail": "Clear explanation of this step in simple language",
      "formula": "Optional: the formula or equation used in this step (omit if not applicable)"
    }
  ],
  "final_answer": "The final answer clearly stated",
  "concepts": ["Concept 1", "Concept 2", "Concept 3"],
  "pro_tip": "A useful tip or shortcut for this type of problem"
}

IMPORTANT:
- If the image is unclear or not a question, return {"error": "Could not read a clear question from this image. Try a clearer photo."}
- Return ONLY valid JSON. No markdown, no extra text.
- Be thorough with steps  explain each one clearly for a student.
- Use simple, friendly language."""

        response = gemini_rotator.generate_content(
            AI_MODEL,
            contents=[
                {'role': 'user', 'parts': [
                    {'inline_data': image_data},
                    {'text': prompt}
                ]}
            ]
        )

        raw = response.text.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]

        result = json.loads(raw.strip())

        # If Gemini returned an error key inside JSON
        if 'error' in result and len(result) == 1:
            return jsonify(result), 422

        return jsonify(result)

    except json.JSONDecodeError:
        # Try to return raw text as explanation if JSON parse fails
        try:
            return jsonify({
                'question_preview': 'Question detected',
                'subject': 'General',
                'topic': 'Mixed',
                'difficulty': 'Medium',
                'steps': [{'title': 'AI Solution', 'detail': response.text, 'formula': ''}],
                'final_answer': '',
                'concepts': [],
                'pro_tip': ''
            })
        except Exception:
            return jsonify({'error': 'AI returned an unexpected response. Please try again.'}), 500
    except Exception as e:
        print(f"Photo solver error: {e}")
        return jsonify({'error': f'Could not solve: {str(e)}'}), 500



@app.route('/api/photo-solver/solve-stream', methods=['POST'])
@login_required
def photo_solver_solve_stream():
    """
    Progressive SSE version of photo-solver/solve.
    Streams each result section as it becomes available so the
    frontend can render them one-by-one with animations.
    Events: question_preview, meta, step (×N), concepts, pro_tip, final_answer, done, error
    """
    from flask import stream_with_context, Response

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    img_file = request.files['image']
    if img_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    img_bytes  = img_file.read()
    mime_type  = img_file.content_type or 'image/jpeg'

    if len(img_bytes) > 10 * 1024 * 1024:
        return jsonify({'error': 'Image too large. Maximum 10MB.'}), 400

    if not GEMINI_AVAILABLE or not AI_API_KEY:
        return jsonify({'error': 'AI service not configured'}), 503

    def generate():
        import base64 as _b64, json as _json, time as _time

        yield f'data: {_json.dumps({"type": "status", "msg": "🔍 Reading your image..."})}\n\n'
        _time.sleep(0.1)

        image_data = {
            'mime_type': mime_type,
            'data': _b64.b64encode(img_bytes).decode('utf-8')
        }

        prompt = """You are an expert academic tutor. Carefully look at this image which contains a question or problem.

Analyse and solve it completely. Return your response as valid JSON with this EXACT structure:

{
  "question_preview": "A short 1-sentence description of what the question is about",
  "subject": "Subject name (e.g. Mathematics, Physics, Chemistry, Biology, History, etc.)",
  "topic": "Specific topic (e.g. Integration by Parts, Newton's Laws, Organic Chemistry)",
  "difficulty": "Easy / Medium / Hard",
  "steps": [
    {
      "title": "Step title (e.g. Identify the formula)",
      "detail": "Clear explanation of this step in simple language",
      "formula": "Optional: the formula or equation used in this step (omit if not applicable)"
    }
  ],
  "final_answer": "The final answer clearly stated",
  "concepts": ["Concept 1", "Concept 2", "Concept 3"],
  "pro_tip": "A useful tip or shortcut for this type of problem"
}

IMPORTANT:
- If the image is unclear or not a question, return {"error": "Could not read a clear question from this image. Try a clearer photo."}
- Return ONLY valid JSON. No markdown, no extra text.
- Be thorough with steps — explain each one clearly for a student.
- Use simple, friendly language."""

        # ── Direct Gemini call: gemini-1.5-flash is the fastest vision model ──
        try:
            yield f'data: {_json.dumps({"type": "status", "msg": "🤖 Analysing with AI..."})}\n\n'

            response = gemini_rotator.generate_content(
                AI_MODEL,  # gemini-2.5-flash — only model on Google AI Studio v1beta keys
                contents=[{
                    'role': 'user',
                    'parts': [
                        {'inline_data': image_data},
                        {'text': prompt}
                    ]
                }]
            )

            raw = response.text.strip()
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]

            result = _json.loads(raw.strip())

        except _json.JSONDecodeError:
            try:
                result = {
                    'question_preview': 'Question detected',
                    'subject': 'General', 'topic': 'Mixed', 'difficulty': 'Medium',
                    'steps': [{'title': 'AI Solution', 'detail': response.text, 'formula': ''}],
                    'final_answer': '', 'concepts': [], 'pro_tip': ''
                }
            except Exception:
                yield f'data: {_json.dumps({"type": "error", "msg": "AI returned an unexpected response. Please try again."})}\n\n'
                return
        except Exception as e:
            yield f'data: {_json.dumps({"type": "error", "msg": str(e)})}\n\n'
            return

        if 'error' in result and len(result) == 1:
            yield f'data: {_json.dumps({"type": "error", "msg": result["error"]})}\n\n'
            return

        # ── Stream each section with a tiny pause for drama ──────
        # 1. Question preview
        yield f'data: {_json.dumps({"type": "question_preview", "text": result.get("question_preview", "")})}\n\n'
        _time.sleep(0.15)

        # 2. Meta (subject / topic / difficulty)
        yield f'data: {_json.dumps({"type": "meta", "subject": result.get("subject",""), "topic": result.get("topic",""), "difficulty": result.get("difficulty","")})}\n\n'
        _time.sleep(0.15)

        # 3. Steps — one at a time
        steps = result.get('steps', [])
        for i, step in enumerate(steps, 1):
            yield f'data: {_json.dumps({"type": "step", "index": i, "total": len(steps), "title": step.get("title",""), "detail": step.get("detail",""), "formula": step.get("formula","")})}\n\n'
            _time.sleep(0.12)

        # 4. Concepts
        yield f'data: {_json.dumps({"type": "concepts", "items": result.get("concepts", [])})}\n\n'
        _time.sleep(0.12)

        # 5. Pro tip
        if result.get('pro_tip'):
            yield f'data: {_json.dumps({"type": "pro_tip", "text": result["pro_tip"]})}\n\n'
            _time.sleep(0.12)

        # 6. Final answer
        yield f'data: {_json.dumps({"type": "final_answer", "text": result.get("final_answer", "")})}\n\n'
        _time.sleep(0.1)

        # 7. Done — pass back full result so XP / quiz still work
        yield f'data: {_json.dumps({"type": "done", "result": result})}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':     'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/api/photo-solver/award-xp', methods=['POST'])
@login_required
def photo_solver_award_xp():
    """Award XP for using the Photo Solver feature."""
    try:
        result = GamificationService.add_xp(current_user.id, 'photo_solver', 20)
        GamificationService.update_streak(current_user.id)
        earned = (result or {}).get('earned', 20) if result else 20
        return jsonify({'earned': earned if earned > 0 else 20})
    except Exception:
        return jsonify({'earned': 0})


@app.route('/api/photo-solver/generate-quiz', methods=['POST'])
@login_required
def photo_solver_generate_quiz():
    """
    Generate 5 contextual MCQ quiz questions for the topic just solved.
    Accepts JSON: { "topic": "...", "subject": "..." }
    Returns JSON: { "questions": [ { "question", "options": ["A","B","C","D"], "answer": 0, "explanation" } ] }
    """
    data = request.get_json() or {}
    topic = data.get('topic', '').strip()
    subject = data.get('subject', '').strip()

    if not topic:
        return jsonify({'error': 'Topic is required'}), 400

    if not GEMINI_AVAILABLE or not AI_API_KEY:
        return jsonify({'error': 'AI service not configured'}), 503

    try:
        prompt = f"""You are an expert tutor creating a short practice quiz.
Topic: "{topic}"
Subject: "{subject or 'General'}"

Generate exactly 5 multiple-choice questions to test a student's understanding of this topic.

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0,
      "explanation": "Brief explanation of why this answer is correct."
    }}
  ]
}}

Rules:
- "answer" is the 0-based index of the correct option (0, 1, 2, or 3)
- Questions should test real understanding, not just memorisation
- Mix easy and medium difficulty
- Keep questions concise and clear
- Explanations should be 1-2 sentences
- Return ONLY JSON, nothing else"""

        resp = gemini_rotator.generate_content(AI_MODEL, prompt)
        raw = resp.text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]

        result = json.loads(raw.strip())
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({'error': 'AI returned an unexpected response. Please try again.'}), 500
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return jsonify({'error': f'Could not generate quiz: {str(e)}'}), 500


# ============================================================================


# ============================================================================
# “¡ LIVE STUDY STREAMS  Routes + SocketIO Events
# ============================================================================

# In-memory registry: stream_id †’ {user_id, topic, subject, timer_min, watchers: set()}
# This resets on server restart  that's fine; streams are ephemeral by nature
_live_streams = {}   # key = stream_id (str(user_id))


# ”€”€ HTTP Routes ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€

@app.route('/live')
@login_required
def live_streams_page():
    """Discovery page: shows all currently live friends."""
    # Get current user's accepted friends
    friend_ids = [
        f.friend_id if f.user_id == current_user.id else f.user_id
        for f in Friendship.query.filter(
            ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
            Friendship.status == 'accepted'
        ).all()
    ]
    # Find which friends are currently live
    live_friends = []
    for sid, info in _live_streams.items():
        uid = info.get('user_id')
        if uid in friend_ids or uid == current_user.id:
            user = User.query.get(uid)
            if user:
                live_friends.append({
                    'stream_id': sid,
                    'user_id': uid,
                    'name': f"{user.first_name} {user.last_name}".strip(),
                    'avatar': user.get_avatar(64),
                    'topic': info.get('topic', 'Studying'),
                    'subject': info.get('subject', ''),
                    'timer_min': info.get('timer_min', 25),
                    'watcher_count': len(info.get('watchers', set())),
                    'elapsed': info.get('elapsed', 0),
                })
    # Check if the current user is already streaming
    user_sid = str(current_user.id)
    user_is_live = user_sid in _live_streams
    own_stream = None
    if user_is_live:
        own_info = _live_streams[user_sid]
        own_stream = {
            'stream_id': user_sid,
            'user_id': current_user.id,
            'topic': own_info.get('topic', 'Studying'),
            'subject': own_info.get('subject', ''),
            'watcher_count': len(own_info.get('watchers', set())),
        }

    return render_template('live_streams.html',
        live_friends=live_friends,
        user_is_live=user_is_live,
        own_stream=own_stream
    )


@app.route('/stream/<int:streamer_id>')
@login_required
def watch_stream(streamer_id):
    """Watcher view for a specific user's live stream."""
    streamer = User.query.get_or_404(streamer_id)
    sid = str(streamer_id)
    stream_info = _live_streams.get(sid)
    if not stream_info:
        return redirect(url_for('live_streams_page'))
    return render_template('watch_stream.html',
        streamer=streamer,
        stream_info=stream_info,
        is_own_stream=(streamer_id == current_user.id)
    )


@app.route('/api/streams/live')
@login_required
def api_live_streams():
    """JSON API: returns all live streams from user's friends."""
    friend_ids = [
        f.friend_id if f.user_id == current_user.id else f.user_id
        for f in Friendship.query.filter(
            ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
            Friendship.status == 'accepted'
        ).all()
    ]
    result = []
    for sid, info in _live_streams.items():
        uid = info.get('user_id')
        if uid in friend_ids or uid == current_user.id:
            user = User.query.get(uid)
            if user:
                result.append({
                    'stream_id': sid,
                    'user_id': uid,
                    'name': f"{user.first_name} {user.last_name}".strip(),
                    'avatar': user.get_avatar(48),
                    'topic': info.get('topic', 'Studying'),
                    'subject': info.get('subject', ''),
                    'watcher_count': len(info.get('watchers', set())),
                    'elapsed': info.get('elapsed', 0),
                })
    return jsonify({'streams': result})


@app.route('/api/streams/history')
@login_required
def api_stream_history():
    """Return current user's past study streams."""
    streams = StudyStream.query.filter_by(
        user_id=current_user.id, status='ended'
    ).order_by(StudyStream.ended_at.desc()).limit(10).all()
    return jsonify({'history': [{
        'topic': s.topic, 'subject': s.subject,
        'duration_min': s.duration_min,
        'peak_watchers': s.peak_watchers,
        'solidarity_count': s.solidarity_count,
        'ended_at': s.ended_at.isoformat() if s.ended_at else None,
    } for s in streams]})


# ”€”€ SocketIO Events ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€

from flask_socketio import leave_room

@socketio.on('go_live')
def handle_go_live(data):
    """Streamer goes live. Creates stream entry; notifies friends."""
    if not current_user.is_authenticated:
        return
    uid = current_user.id
    sid = str(uid)
    topic = (data.get('topic') or 'Studying')[:200]
    subject = (data.get('subject') or 'General')[:100]
    timer_min = int(data.get('timer_min', 25))

    # Register in memory
    _live_streams[sid] = {
        'user_id': uid,
        'topic': topic,
        'subject': subject,
        'timer_min': timer_min,
        'watchers': set(),
        'elapsed': 0,
        'started_at': datetime.utcnow(),
        'messages': [],   # stores last 50 chat messages for replay on refresh
    }

    # Save to DB
    try:
        with app.app_context():
            stream = StudyStream(
                user_id=uid, topic=topic, subject=subject,
                timer_minutes=timer_min, status='live'
            )
            db.session.add(stream)
            db.session.commit()
            _live_streams[sid]['db_id'] = stream.id
    except Exception as e:
        print(f"Stream DB save error: {e}")

    # Streamer joins their own room
    join_room(f"stream_{sid}")

    # Notify all friends
    friend_ids = [
        f.friend_id if f.user_id == uid else f.user_id
        for f in Friendship.query.filter(
            ((Friendship.user_id == uid) | (Friendship.friend_id == uid)),
            Friendship.status == 'accepted'
        ).all()
    ]
    notification = {
        'user_id': uid,
        'stream_id': sid,
        'name': f"{current_user.first_name} {current_user.last_name}".strip(),
        'avatar': current_user.get_avatar(48),
        'topic': topic,
        'subject': subject,
    }
    for fid in friend_ids:
        emit('friend_went_live', notification, room=f"user_{fid}")

    emit('stream_started', {'stream_id': sid, 'topic': topic})


@socketio.on('join_stream')
def handle_join_stream(data):
    """Watcher joins a live stream room."""
    if not current_user.is_authenticated:
        return
    sid = str(data.get('stream_id', ''))
    if sid not in _live_streams:
        emit('stream_not_found', {})
        return

    join_room(f"stream_{sid}")
    uid = current_user.id

    # Don't count the streamer as a watcher  only real spectators
    if uid == _live_streams[sid]['user_id']:
        # Streamer re-joining their own page: just send state, no watcher count change
        started_at = _live_streams[sid].get('started_at')
        server_elapsed = int((datetime.utcnow() - started_at).total_seconds()) if started_at else 0
        emit('stream_state', {
            'topic': _live_streams[sid]['topic'],
            'subject': _live_streams[sid]['subject'],
            'timer_min': _live_streams[sid]['timer_min'],
            'elapsed': server_elapsed,
            'watcher_count': len(_live_streams[sid]['watchers']),
            'recent_messages': _live_streams[sid].get('messages', []),
        })
        return

    # Add to watchers set
    _live_streams[sid]['watchers'].add(uid)
    watcher_count = len(_live_streams[sid]['watchers'])

    # Update peak
    db_id = _live_streams[sid].get('db_id')
    if db_id and watcher_count > _live_streams[sid].get('peak', 0):
        _live_streams[sid]['peak'] = watcher_count
        try:
            with app.app_context():
                s = StudyStream.query.get(db_id)
                if s:
                    s.peak_watchers = watcher_count
                    db.session.commit()
        except Exception:
            pass

    # Tell everyone in room someone joined
    emit('watcher_joined', {
        'name': f"{current_user.first_name}".strip(),
        'avatar': current_user.get_avatar(32),
        'watcher_count': watcher_count,
    }, room=f"stream_{sid}")

    # Compute live elapsed time from when stream started
    started_at = _live_streams[sid].get('started_at')
    server_elapsed = int((datetime.utcnow() - started_at).total_seconds()) if started_at else _live_streams[sid].get('elapsed', 0)

    # Send current stream state + recent messages to new watcher
    emit('stream_state', {
        'topic': _live_streams[sid]['topic'],
        'subject': _live_streams[sid]['subject'],
        'timer_min': _live_streams[sid]['timer_min'],
        'elapsed': server_elapsed,
        'watcher_count': watcher_count,
        'recent_messages': _live_streams[sid].get('messages', []),
    })



@socketio.on('leave_stream')
def handle_leave_stream(data):
    """Watcher leaves a stream."""
    if not current_user.is_authenticated:
        return
    sid = str(data.get('stream_id', ''))
    leave_room(f"stream_{sid}")
    if sid in _live_streams:
        _live_streams[sid]['watchers'].discard(current_user.id)
        watcher_count = len(_live_streams[sid]['watchers'])
        emit('watcher_left', {
            'name': current_user.first_name,
            'watcher_count': watcher_count,
        }, room=f"stream_{sid}")


@socketio.on('timer_tick')
def handle_timer_tick(data):
    """Streamer broadcasts timer state every 5 seconds to watchers."""
    if not current_user.is_authenticated:
        return
    sid = str(current_user.id)
    if sid not in _live_streams:
        return
    elapsed = data.get('elapsed', 0)
    remaining = data.get('remaining', '25:00')
    mode = data.get('mode', 'focus')
    _live_streams[sid]['elapsed'] = elapsed
    # Broadcast to watchers only (not back to streamer)
    emit('timer_update', {
        'remaining': remaining,
        'elapsed': elapsed,
        'mode': mode,
    }, room=f"stream_{sid}", include_self=False)


@socketio.on('stream_reaction')
def handle_stream_reaction(data):
    """Someone sends an emoji reaction in a stream."""
    if not current_user.is_authenticated:
        return
    sid = str(data.get('stream_id', ''))
    emoji = data.get('emoji', '”¥')[:4]
    emit('new_reaction', {
        'emoji': emoji,
        'name': current_user.first_name,
        'avatar': current_user.get_avatar(24),
    }, room=f"stream_{sid}")


@socketio.on('stream_message')
def handle_stream_message(data):
    """Someone sends a cheer/comment message in a stream."""
    if not current_user.is_authenticated:
        return
    sid = str(data.get('stream_id', ''))
    message = (data.get('message') or '')[:200].strip()
    if not message:
        return
    msg_obj = {
        'name': current_user.first_name,
        'avatar': current_user.get_avatar(28),
        'message': message,
        'user_id': current_user.id,
        'type': 'chat',
    }
    # Store for replay (keep last 50)
    if sid in _live_streams:
        msgs = _live_streams[sid].setdefault('messages', [])
        msgs.append(msg_obj)
        if len(msgs) > 50:
            _live_streams[sid]['messages'] = msgs[-50:]
    emit('new_stream_message', msg_obj, room=f"stream_{sid}")


@socketio.on('solidarity_join')
def handle_solidarity_join(data):
    """A watcher starts their own Pomodoro in solidarity."""
    if not current_user.is_authenticated:
        return
    sid = str(data.get('stream_id', ''))
    if sid not in _live_streams:
        return
    # Track it
    db_id = _live_streams[sid].get('db_id')
    if db_id:
        try:
            with app.app_context():
                s = StudyStream.query.get(db_id)
                if s:
                    s.solidarity_count = (s.solidarity_count or 0) + 1
                    db.session.commit()
        except Exception:
            pass
    emit('solidarity_joined', {
        'name': f"{current_user.first_name}",
        'avatar': current_user.get_avatar(28),
    }, room=f"stream_{sid}")


@socketio.on('end_stream')
def handle_end_stream(data):
    """Streamer ends their live session."""
    if not current_user.is_authenticated:
        return
    sid = str(current_user.id)
    info = _live_streams.pop(sid, {})
    duration_min = int(data.get('duration_min', 0))
    # Update DB
    db_id = info.get('db_id')
    if db_id:
        try:
            with app.app_context():
                s = StudyStream.query.get(db_id)
                if s:
                    s.status = 'ended'
                    s.ended_at = datetime.utcnow()
                    s.duration_min = duration_min
                    db.session.commit()
        except Exception:
            pass

    # XP reward: base + watcher bonus
    watcher_bonus = min(len(info.get('watchers', set())) * 5, 50)
    try:
        with app.app_context():
            GamificationService.add_xp(current_user.id, 'study_stream', 25 + watcher_bonus)
    except Exception:
        pass

    emit('stream_ended', {
        'duration_min': duration_min,
        'watchers': len(info.get('watchers', set())),
        'xp_earned': 25 + watcher_bonus,
    }, room=f"stream_{sid}")
    leave_room(f"stream_{sid}")


@socketio.on('join_user_room')
def handle_join_user_room(data):
    """Every connected user joins their personal notification room."""
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")


# ============================================================================
# FEEDBACK ROUTES
# ============================================================================

@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Save user feedback to DB."""
    try:
        data = request.get_json() or {}
        rating   = data.get('rating', 'neutral')
        message  = (data.get('message') or '').strip()[:1000]
        category = data.get('category', 'general')
        page_url = (data.get('page_url') or '')[:200]

        fb = UserFeedback(
            user_id  = current_user.id,
            rating   = rating,
            message  = message or None,
            category = category,
            page_url = page_url or None
        )
        db.session.add(fb)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Thanks for your feedback! ¤'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    """Admin view for all user feedback."""
    page     = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    rating   = request.args.get('rating', '')

    query = UserFeedback.query.order_by(UserFeedback.created_at.desc())
    if category:
        query = query.filter_by(category=category)
    if rating:
        query = query.filter_by(rating=rating)

    feedbacks  = query.limit(100).all()
    total      = UserFeedback.query.count()

    # Sentiment summary
    rating_counts = {}
    for r in ['love','happy','neutral','sad','awful']:
        rating_counts[r] = UserFeedback.query.filter_by(rating=r).count()

    unread_support_count = SupportTicket.query.filter_by(status='open').count()

    return render_template('admin/feedback/list.html',
        feedbacks=feedbacks,
        total=total,
        rating_counts=rating_counts,
        unread_support_count=unread_support_count
    )


# ============================================================================
# REFERRAL ROUTES
# ============================================================================

@app.route('/api/referral/info')
@login_required
def referral_info():
    """Get current user's referral code, link, and stats."""
    total_referrals = ReferralReward.query.filter_by(referrer_id=current_user.id).count()
    total_xp_earned = db.session.query(db.func.sum(ReferralReward.xp_awarded))\
        .filter_by(referrer_id=current_user.id).scalar() or 0

    # Ensure user has a referral code (for existing users who signed up before this feature)
    if not current_user.referral_code:
        import random, string
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=8))
        while User.query.filter_by(referral_code=code).first():
            code = ''.join(random.choices(chars, k=8))
        current_user.referral_code = code
        db.session.commit()

    base_url = request.host_url.rstrip('/')
    referral_link = f"{base_url}/invite/{current_user.referral_code}"

    return jsonify({
        'status': 'success',
        'referral_code': current_user.referral_code,
        'referral_link': referral_link,
        'total_referrals': total_referrals,
        'total_xp_earned': total_xp_earned
    })


@app.route('/invite/<code>')
def referral_landing(code):
    """Referral link landing  stores ref code in session and redirects to signup."""
    # Verify the code is valid
    referrer = User.query.filter_by(referral_code=code).first()
    if referrer:
        # Store in session so signup page can pick it up
        session['ref_code'] = code
        flash(f' You were invited by {referrer.first_name}! Sign up to give them 500 XP.', 'success')
    return redirect(url_for('auth') + f'?ref={code}')


# ============================================================================
# VERSE  AI VOICE ASSISTANT API
# ============================================================================

@app.route('/api/voice-assistant', methods=['POST'])
@login_required
def voice_assistant():
    """
    Verse Voice Assistant  Natural Language Full-UI Control Engine.
    Returns { action, params, reply, dom_actions[] } where dom_actions
    are executed directly by the JS DOM automation engine.
    This function is fully wrapped in a try/except so we NEVER leak a raw 500 HTML response
    to the frontend (which breaks the JSON contract expected by verse_assistant.js).
    """
    try:
        if not gemini_rotator.available:
            return jsonify({'action': 'none', 'params': {}, 'reply': "I'm not set up yet.", 'dom_actions': []})

        data       = request.get_json(silent=True) or {}
        transcript = (data.get('text') or '').strip()
        page       = data.get('page', '/')

        if not transcript:
            return jsonify({'action': 'none', 'params': {}, 'reply': "I didn't catch that.", 'dom_actions': []})

        # ”€”€ Live context (safe defaults on any DB error) ”€”€”€”€”€”€”€”€”€”€”€”€”€”€
        user_name     = current_user.first_name or 'there'
        streak        = 0
        xp            = 0
        level         = 1
        pending_count = 0
        todo_list_str = 'none'
        upcoming_count = 0
        friends_str   = 'none'

        try:
            streak        = current_user.current_streak or 0
            xp            = current_user.total_xp or 0
            level         = current_user.level or 1
            pending_count = Todo.query.filter_by(user_id=current_user.id, completed=False).count()

            pending_todos = Todo.query.filter_by(user_id=current_user.id, completed=False)\
                                      .order_by(Todo.created_at.desc()).limit(5).all()
            todo_list_str = ', '.join([f'"{t.title}" ({t.priority})' for t in pending_todos]) or 'none'
        except Exception as _e:
            print(f"[Verse] Todo context error: {_e}")

        try:
            upcoming_count = Event.query.filter(
                Event.user_id == current_user.id,
                Event.date >= datetime.utcnow().date()
            ).count()
        except Exception:
            pass

        try:
            accepted = Friendship.query.filter(
                ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
                Friendship.status == 'accepted'
            ).all()
            friends_names = []
            for f in accepted[:10]:
                fid = f.friend_id if f.user_id == current_user.id else f.user_id
                friend = User.query.filter_by(id=fid).first()  # always works
                if friend:
                    name = f"{friend.first_name or ''} {friend.last_name or ''}".strip()
                    if name:
                        friends_names.append(name)
            friends_str = ', '.join(friends_names) if friends_names else 'none'
        except Exception as _e:
            print(f"[Verse] Friends context error: {_e}")

        # ”€”€ Leaderboard context ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
        my_rank = 999
        rank_1_user = 'unknown'
        rank_1_xp   = 0
        try:
            # User model does not have is_public_profile, is_admin, or is_banned,
            # so we rely on standard filtering
            my_rank = User.query.filter(
                db.or_(User.level > current_user.level,
                       db.and_(User.level == current_user.level, User.total_xp > current_user.total_xp))
            ).count() + 1
            top_users = User.query.order_by(User.level.desc(), User.total_xp.desc()).limit(5).all()
            if top_users:
                rank_1_user = f"{top_users[0].first_name} {top_users[0].last_name or ''}".strip()
                rank_1_xp   = top_users[0].total_xp or 0
            # Build top 5 summary string
            top5_parts = []
            for i, u in enumerate(top_users, 1):
                n = f"{u.first_name} {u.last_name or ''}".strip()
                top5_parts.append(f"#{i} {n} ({u.total_xp} XP)")
            top5_str = " | ".join(top5_parts) if top5_parts else 'unknown'
        except Exception as _e:
            print(f"[Verse] Leaderboard context error: {_e}")
            top5_str = 'unknown'

        # ”€”€ Group context ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
        groups_str = 'none'
        try:
            my_groups = getattr(GroupService, 'get_user_groups')(current_user.id)
            if my_groups:
                groups_str = ', '.join([f"'{g.name}' (ID: {g.id})" for g in my_groups])
        except Exception as _e:
            pass

        # ”€”€ System prompt with FULL DOM knowledge ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
        system_prompt = f"""You are Verse, the AI voice assistant that FULLY CONTROLS the StudyVerse app.
You can navigate pages AND directly interact with any UI element on the current page.

=== LIVE USER DATA ===
Name: {user_name} | Streak: {streak} days | XP: {xp} | Level: {level}
Pending todos ({pending_count}): {todo_list_str}
Upcoming events: {upcoming_count}
Friends: {friends_str}
Groups: {groups_str}
Your rank: #{my_rank} globally
Top 5 leaderboard: {top5_str}
Current page: {page}

=== YOUR PERSONALITY ===
Friendly, brief (2 sentences max), motivating. You speak out loud (TTS) so be natural.

=== DOMAIN: WHAT YOU CAN DO ===

”€”€”€”€ NAVIGATION ”€”€”€”€
navigate_dashboard, navigate_pomodoro, navigate_todos, navigate_quiz,
navigate_syllabus, navigate_leaderboard, navigate_friends, navigate_shop,
navigate_progress, navigate_chat, navigate_battle, navigate_profile,
navigate_settings, navigate_calendar, navigate_topic_resolver, navigate_photo_solver,
navigate_support, navigate_live, navigate_user_profile

”€”€”€”€ SERVER ACTIONS (use "action" field) ”€”€”€”€
- read_pending_todos     †’ read pending task list aloud (params: {{}})
- add_todo               †’ save todo to DB (params: {{"title":"...", "priority":"high/medium/low"}})
- send_friend_request    †’ send request by name (params: {{"name":"..."}})
- start_quiz             †’ navigate to quiz + auto-start (params: {{"difficulty":"easy/medium/hard"}})
- start_battle           †’ navigate to battle + auto-create room (params: {{}})
- shop_item              †’ buy/equip/unequip a shop item (params: {{"item_name":"...","operation":"buy|equip|unequip"}})
- navigate_user_profile  †’ open any user's profile by name (params: {{"name":"..."}}). Use for "open Krisha's profile", "show Beast's page", etc.
- get_leaderboard        †’ speak user's rank + top 5 (use live data above in reply)
- get_streak             †’ speak streak (use live data)
- get_stats              †’ speak XP, level, streak, rank (use live data)
- get_xp                 †’ speak XP total (use live data)
- get_friends            †’ list friend names aloud (use live data)
- dom_interact           †’ pure DOM interaction, no server call
- conversation           †’ just reply, nothing else

”€”€”€”€ DOM ACTIONS (use "dom_actions" array) ”€”€”€”€
These execute on the browser DOM. Use IDs below.

BATTLE (/battle): btn-create, btn-join, join-code (input), btn-submit, btn-vote-yes, btn-vote-no, btn-accept, btn-reject, chat-input
POMODORO (/pomodoro): start-btn (start/pause), reset-btn, focusMode, shortBreakMode, stopwatchMode, goLiveBtn, add-goal-btn, new-goal-input, brain-dump-area, liveTopicInput, liveSubjectInput
QUIZ (/quiz): start-quiz-btn, next-question-btn; answers = clickNth on #options-container .quiz-option (index 0=A,1=B,2=C,3=D); settings = clickByText on .btn-select ("5","10","15","20","Easy","Medium","Hard")
TODOS (/todos): taskTitle, taskPriority (select: high/medium/low), taskDueDate, btnDone; open modal = click text "Add Task"
CHAT (/chat): chatInput, sendButton, chatForm
GROUP CHAT (/group): groupChatInput, groupSendButton, groupChatForm
FRIENDS (/friends): user-search
SHOP (/shop): shop-search [NOTE: for buying/equipping items, use shop_item action, NOT DOM clicks]
CALENDAR (/calendar): quick-add-title
SYLLABUS (/syllabus): uploadPdf (click to open file picker)
WHITEBOARD (/group †’ Board tab): use action=wb_draw_ai with params={{"shape":"tree|line|circle|house|star|triangle|arrow|heart|smiley|square", "color":"optional color name"}}
GLOBAL (any page): theme-toggle, sidebar-toggle, zen-mode-nav-btn, feedbackBtn
PROGRESS TRACKER (/progress †’ Habit Matrix): use helper functions verseToggleHabits and verseAddHabit via dom_actions with op="callFunction"

=== SHOP CATALOG (use shop_item action) ===
Themes (apply visual theme to the entire app):
- "neon city" (theme_neon_city) †’ 3800 XP
- "sakura" (theme_sakura) †’ 2800 XP
- "cyberpunk" (theme_cyberpunk) †’ 4000 XP
- "synthwave" (theme_synthwave) †’ 3500 XP
- "aurora" (theme_aurora) †’ 3000 XP

Frames (avatar border effects):
- "golden frame" (frame_gold) †’ 2500 XP
- "diamond frame" (frame_diamond) †’ 7500 XP
- "fire frame" (frame_fire) †’ 4000 XP
- "ice frame" (frame_ice) †’ 3500 XP
- "glitch frame" (frame_glitch) †’ 5000 XP

For shop_item action: params = {{"item_name": "name of item", "operation": "buy|equip|unequip"}}
- "buy" = purchase (deducts XP) + auto-equip for themes/frames
- "equip" = apply already-owned item
- "unequip" = remove / revert to default

=== DOM ACTION FORMAT ===
Each dom_action object: {{"op": "click|clickNth|clickByText|type|selectOption|focus|navigate|callFunction",
  "id": "element-id",
  "selector": "css-selector",
  "value": "text to type or option value OR function name for callFunction",
  "text": "exact button text for clickByText",
  "index": 0,
  "fn": "optional function name for callFunction",
  "args": {{"any":"json arguments to pass"}}
}}

ops explained:
- click: click element by id or selector
- clickNth: click the Nth element matching a selector (0=first)
- clickByText: click a button/element whose visible text exactly matches "text" field
- type: type value into an input (clears first)
- selectOption: set a <select> value
- focus: focus an element (e.g. textarea)
- navigate: go to a URL path (always put FIRST if navigation needed)
- callFunction: call a helper function on window with "fn" or "value" and pass "args"

QUIZ PAGE SPECIFICS (IMPORTANT):
- Quiz answer options are <div class="quiz-option"> inside #options-container
- To click answer A: {{"op":"clickNth","selector":"#options-container .quiz-option","index":0}}
- To click answer B: index:1, C: index:2, D: index:3
- Question count/difficulty are .btn-select buttons with visible text "5","10","15","20","Easy","Medium","Hard"
- To select 10 questions: {{"op":"clickByText","selector":".btn-select","text":"10"}}
- To select Hard difficulty: {{"op":"clickByText","selector":".btn-select","text":"Hard"}}

=== FULL APP COVERAGE  EXAMPLES FOR EVERY FEATURE ===

”€”€ STATS & INFO (use live data above, no DOM needed) ”€”€
"what's my rank" †’ action=get_leaderboard, reply="You're ranked #{my_rank}. {rank_1_user} is #1 with {rank_1_xp} XP."
"who is number 1" †’ action=get_leaderboard, reply speaking rank_1_user and rank_1_xp from live data
"how many friends do I have" †’ action=get_friends, reply listing friends_str from live data
"who are my friends" †’ action=get_friends, reply listing friends_str from live data
"what's my streak" †’ action=get_streak
"my stats / how am I doing" †’ action=get_stats (speak XP, level, streak, rank together)
"my XP / how much XP" †’ action=get_xp
"what tasks are pending / show todos" †’ action=read_pending_todos

”€”€ NAVIGATION ”€”€
"go to leaderboard / who's winning" †’ action=navigate_leaderboard, dom_actions=[]
"open support / I have a complaint / help / contact us / raise a ticket" †’ action=navigate_support, dom_actions=[]
"go to chat / talk to AI / AI coach" †’ action=navigate_chat, dom_actions=[]
"open group chat / groups dashboard" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/group"}}]
"go to [group/guild name] group / open [group name] chat" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/group/[group_id_from_context]"}}]
"go to live streams / who is live" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/live"}}]
"draw a [shape] on the whiteboard / draw a tree / draw a circle / draw a house / draw a star / draw an arrow / draw a heart / draw a smiley / draw a line" †’ action=wb_draw_ai, params={{"shape":"<shape name>", "color":"<color if mentioned>"}}, dom_actions=[]
"open profile / my profile" †’ action=navigate_profile, dom_actions=[]
"open settings" †’ action=navigate_settings, dom_actions=[]
"open shop / buy items" †’ action=navigate_shop, dom_actions=[]
"open progress / my progress" †’ action=navigate_progress, dom_actions=[]
"open calendar / my events" †’ action=navigate_calendar, dom_actions=[]
"open syllabus / my courses" †’ action=navigate_syllabus, dom_actions=[]
"open topic resolver / resolve topic / explain topic" †’ action=navigate_topic_resolver, dom_actions=[]
"open photo solver / solve from photo" †’ action=navigate_photo_solver, dom_actions=[]

”€”€ BATTLE ”€”€
"start byte battle / start battle / let's compete" †’ action=start_battle, dom_actions=[]
"create a battle room" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/battle"}},{{"op":"click","id":"btn-create","delay":800}}]
"join battle room" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/battle"}},{{"op":"click","id":"btn-join","delay":600}}]
"vote yes / it's correct" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"btn-vote-yes"}}]
"vote no / that's wrong" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"btn-vote-no"}}]

”€”€ POMODORO ”€”€
"start timer / start focus / let's grind" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/pomodoro"}},{{"op":"click","id":"start-btn","delay":500}}]
"start the timer" (already on pomodoro) †’ action=dom_interact, dom_actions=[{{"op":"click","id":"start-btn"}}]
"stop / pause timer" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"start-btn"}}]
"reset timer" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"reset-btn"}}]
"short break / take a break" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/pomodoro"}},{{"op":"click","id":"shortBreakMode","delay":600}}]
"stopwatch mode" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/pomodoro"}},{{"op":"click","id":"stopwatchMode","delay":600}}]
"go live / stream now" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/pomodoro"}},{{"op":"click","id":"goLiveBtn","delay":600}}]

”€”€ QUIZ ”€”€
"start quiz / quiz me" †’ action=start_quiz, params={{"difficulty":"medium"}}, dom_actions=[]
"10 questions hard quiz" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/quiz"}},{{"op":"clickByText","selector":".btn-select","text":"10","delay":600}},{{"op":"clickByText","selector":".btn-select","text":"Hard","delay":300}},{{"op":"click","id":"start-quiz-btn","delay":400}}]
"answer A" †’ action=dom_interact, dom_actions=[{{"op":"clickNth","selector":"#options-container .quiz-option","index":0}}]
"answer B" †’ index 1 | "answer C" †’ index 2 | "answer D" †’ index 3
"next question" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"next-question-btn"}}]

”€”€ TODOS ”€”€
"add [task] with [priority] priority" †’ action=add_todo, extract title and priority
"what tasks are pending" †’ action=read_pending_todos

”€”€ FRIENDS ”€”€
"send request to [name]" †’ action=send_friend_request, params={{"name":"..."}}
"search [name] in friends" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/friends"}},{{"op":"type","id":"user-search","value":"name","delay":800}}]

”€”€ CHAT ”€”€
"type [message] in chat / send [message]" †’ action=dom_interact, dom_actions=[{{"op":"type","id":"chatInput","value":"message"}},{{"op":"click","id":"sendButton","delay":200}}]
"say [message] in [group/guild name] chat / send [message] in [group name] chat" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/group/[group_id_from_context]"}},{{"op":"type","id":"groupChatInput","value":"message","delay":600}},{{"op":"click","id":"groupSendButton","delay":200}}]

”€”€ HABIT MATRIX (PROGRESS TRACKER) ”€”€
"I did [habit] today" or "mark [habit] for today" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/progress"}},{{"op":"callFunction","fn":"verseToggleHabits","args":{{"habits":["habit"],"day":"today"}}}}]
"I did reading and coding today" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/progress"}},{{"op":"callFunction","fn":"verseToggleHabits","args":{{"habits":["reading","coding"],"day":"today"}}}}]
"mark [habit] on [day]" (e.g. Thursday) †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/progress"}},{{"op":"callFunction","fn":"verseToggleHabits","args":{{"habits":["habit"],"day":"<day name>"}}}}]
"add habit [name]" or "track [name] as a habit" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/progress"}},{{"op":"callFunction","fn":"verseAddHabit","args":"name"}}]

”€”€ GLOBAL CONTROLS ”€”€
"dark mode / light mode / switch theme" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"theme-toggle"}}]
"zen mode" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"zen-mode-nav-btn"}}]
"open sidebar / close sidebar" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"sidebar-toggle"}}]
"give feedback" †’ action=dom_interact, dom_actions=[{{"op":"click","id":"feedbackBtn"}}]
"search [item] in shop" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/shop"}},{{"op":"type","id":"shop-search","value":"item","delay":600}}]
"upload syllabus / upload PDF" †’ action=dom_interact, dom_actions=[{{"op":"navigate","value":"/syllabus"}},{{"op":"click","id":"uploadPdf","delay":600}}]

”€”€ WHITEBOARD DRAWING (via Verse) ”€”€
"draw a tree" †’ action=wb_draw_ai, params={{"shape":"tree"}}
"draw a red circle" †’ action=wb_draw_ai, params={{"shape":"circle","color":"red"}}
"draw a house" †’ action=wb_draw_ai, params={{"shape":"house"}}
"draw a star" †’ action=wb_draw_ai, params={{"shape":"star"}}
"draw a line" †’ action=wb_draw_ai, params={{"shape":"line"}}
"draw an arrow" †’ action=wb_draw_ai, params={{"shape":"arrow"}}
"draw a heart" †’ action=wb_draw_ai, params={{"shape":"heart"}}
"draw a smiley" †’ action=wb_draw_ai, params={{"shape":"smiley"}}
"draw a triangle" †’ action=wb_draw_ai, params={{"shape":"triangle"}}
"draw a square / box / rectangle" †’ action=wb_draw_ai, params={{"shape":"rectangle"}}

CRITICAL RULES:
1. dom_interact = dom_actions only, no server call
2. If navigating + doing something: navigate op FIRST with delay on next actions
3. ALWAYS include reply field (spoken)  
4. dom_actions = [] if not needed
5. For leaderboard/friends/stats: READ FROM LIVE DATA ABOVE, don't say "I don't know"
6. "support" / "complaint" / "help" / "issue" / "ticket" = navigate_support (NOT feedbackBtn)
7. CASUAL LANGUAGE: You MUST understand ANY natural phrasing. Examples:
   - "apply it" / "put it on" = equip
   - "take it off" / "revert" / "go back" / "undo" = unequip
   - "I wanna get" / "let me buy" / "purchase this" = buy
   - "bro start the thing" = start timer
   - "let's do some questions" = start quiz
   - "check how I'm doing" = get_stats
   - "who's at the top" = get_leaderboard

Respond ONLY with valid JSON, NO markdown, NO code fences:
{{"action":"action_name","params":{{}},"reply":"spoken reply","dom_actions":[]}}

User said: "{transcript}"
"""

        try:
            response = gemini_rotator.generate_content(AI_MODEL, system_prompt)
            raw = response.text.strip()
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
            raw = raw.strip()

            result      = json.loads(raw)
            action      = result.get('action', 'none')
            params      = result.get('params', {})
            reply       = result.get('reply', 'Got it!')
            dom_actions = result.get('dom_actions', [])

            return jsonify({'action': action, 'params': params, 'reply': reply, 'dom_actions': dom_actions})

        except json.JSONDecodeError:
            raw_fallback = getattr(response, 'text', '').strip() or "I'm not sure about that."
            return jsonify({'action': 'conversation', 'params': {}, 'reply': raw_fallback, 'dom_actions': []})
        except Exception as e:
            import traceback
            err_str = str(e)
            traceback.print_exc()  # Full traceback in Render logs
            print(f"[Verse] Error type: {type(e).__name__}: {err_str}")

            # Quota / rate limit
            if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
                msg = "I'm a bit overloaded right now  Gemini quota hit. Try in a moment!"
            # API key / authentication
            elif 'api_key' in err_str.lower() or 'invalid' in err_str.lower() or '401' in err_str:
                msg = "There's an issue with my AI keys. Check Render environment variables."
            # Network / timeout
            elif 'timeout' in err_str.lower() or 'connect' in err_str.lower():
                msg = "Connection timed out. Please try again."
            else:
                msg = (
                    f"I ran into a problem: {err_str[:80]}"
                    if len(err_str) < 200
                    else "Something went wrong on my end. Check the Render logs!"
                )

            return jsonify({'action': 'none', 'params': {}, 'reply': msg, 'dom_actions': []})

    except Exception as outer_e:
        # Absolute last-resort guard: if ANYTHING above throws, never return a raw 500 HTML page.
        import traceback
        traceback.print_exc()
        msg = "Something broke while preparing your AI request. Please check the server logs for Verse."
        print(f"[Verse] Outer voice_assistant failure: {outer_e}")
        return jsonify({'action': 'none', 'params': {}, 'reply': msg, 'dom_actions': []})


@app.route('/api/verse/action', methods=['POST'])
@login_required
def verse_execute_action():
    """
    Execute real server-side actions for Verse voice assistant.
    Called by JS after /api/voice-assistant returns an actionable result.
    Returns { success, data, message } for JS to use in the spoken reply.
    """
    data   = request.get_json(silent=True) or {}
    action = data.get('action', '')
    params = data.get('params', {})

    # ”€”€ ADD TODO ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    if action == 'add_todo':
        title    = (params.get('title') or '').strip()
        priority = params.get('priority', 'medium').lower()
        if priority not in ('high', 'medium', 'low'):
            priority = 'medium'
        if not title:
            return jsonify({'success': False, 'message': 'No todo title provided.'})
        todo = Todo(
            user_id=current_user.id,
            title=title,
            completed=False,
            priority=priority,
            is_group=False
        )
        db.session.add(todo)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Added "{title}" with {priority} priority.'})

    # ”€”€ READ PENDING TODOS ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'read_pending_todos':
        todos = Todo.query.filter_by(user_id=current_user.id, completed=False)\
                          .order_by(Todo.created_at.desc()).limit(8).all()
        if not todos:
            return jsonify({'success': True, 'todos': [], 'message': 'You have no pending tasks. All clear!'})
        todo_data = [{'title': t.title, 'priority': t.priority} for t in todos]
        names = [t.title for t in todos]
        msg = f"You have {len(todos)} pending tasks: {', '.join(names[:5])}{'and more.' if len(todos) > 5 else '.'}"
        return jsonify({'success': True, 'todos': todo_data, 'message': msg})

    # ”€”€ SEND FRIEND REQUEST ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'send_friend_request':
        name = (params.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'No friend name found.'})
        parts = name.split()
        fname, lname = parts[0], parts[1] if len(parts) > 1 else ''
        # Search for the user
        query = User.query.filter(User.id != current_user.id)
        if lname:
            query = query.filter(User.first_name.ilike(f'%{fname}%'), User.last_name.ilike(f'%{lname}%'))
        else:
            query = query.filter(User.first_name.ilike(f'%{fname}%'))
        target = query.first()
        if not target:
            return jsonify({'success': False, 'message': f'Could not find a user named {name}.'})
        # Check existing friendship
        existing = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == target.id)) |
            ((Friendship.user_id == target.id) & (Friendship.friend_id == current_user.id))
        ).first()
        if existing:
            status = existing.status
            if status == 'accepted':
                return jsonify({'success': False, 'message': f'You are already friends with {target.first_name}.'})
            else:
                return jsonify({'success': False, 'message': f'A friend request to {target.first_name} already exists.'})
        req = Friendship(user_id=current_user.id, friend_id=target.id, status='pending')
        db.session.add(req)
        db.session.commit()
        # Socket notification
        try:
            socketio.emit('friend_request_received', {
                'from_id':   current_user.id,
                'from_name': f"{current_user.first_name} {current_user.last_name or ''}".strip(),
                'avatar':    current_user.get_avatar(64),
                'request_id': req.id
            }, room=f"user_{target.id}")
        except Exception:
            pass
        return jsonify({'success': True, 'message': f'Friend request sent to {target.first_name}!'})

    # ”€”€ GET STATS ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action in ('get_stats', 'get_streak', 'get_xp'):
        return jsonify({
            'success': True,
            'streak': current_user.current_streak or 0,
            'xp': current_user.total_xp or 0,
            'level': current_user.level or 1,
            'pending': Todo.query.filter_by(user_id=current_user.id, completed=False).count()
        })

    # ”€”€ GET LEADERBOARD ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'get_leaderboard':
        try:
            my_rank = User.query.filter(
                User.is_public_profile == True, User.is_admin == False, User.is_banned == False,
                db.or_(User.level > current_user.level,
                       db.and_(User.level == current_user.level,
                               User.total_xp > current_user.total_xp))
            ).count() + 1
            top_users = User.query.filter(
                User.is_public_profile == True, User.is_admin == False, User.is_banned == False
            ).order_by(User.level.desc(), User.total_xp.desc()).limit(5).all()
            lines = []
            for i, u in enumerate(top_users, 1):
                n = f"{u.first_name} {u.last_name or ''}".strip()
                lines.append(f"#{i} {n} with {u.total_xp} XP")
            top_str = ", ".join(lines) if lines else "no data"
            msg = (f"You are rank #{my_rank} on the leaderboard. "
                   f"Top 5: {top_str}.")
            return jsonify({'success': True, 'rank': my_rank, 'message': msg})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Could not fetch leaderboard: {e}'})

    # ”€”€ GET FRIENDS ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'get_friends':
        try:
            accepted = Friendship.query.filter(
                ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)),
                Friendship.status == 'accepted'
            ).all()
            names = []
            for f in accepted:
                fid = f.friend_id if f.user_id == current_user.id else f.user_id
                friend = User.query.filter_by(id=fid).first()
                if friend:
                    names.append(f"{friend.first_name} {friend.last_name or ''}".strip())
            if not names:
                msg = "You don't have any friends yet on StudyVerse. Say 'send request to someone' to add them!"
            else:
                msg = f"You have {len(names)} friend{'s' if len(names) != 1 else ''}: {', '.join(names)}."
            return jsonify({'success': True, 'friends': names, 'message': msg})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    # ”€”€ START QUIZ (return signal for JS to auto-initiate) ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'start_quiz':
        difficulty = params.get('difficulty', 'medium')
        return jsonify({'success': True, 'difficulty': difficulty, 'navigate': '/quiz', 'auto_start': True})

    # ”€”€ START BATTLE (navigate + signal) ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'start_battle':
        return jsonify({'success': True, 'navigate': '/battle', 'auto_create': True})

    # ”€”€ NAVIGATE TO ANY USER'S PROFILE ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'navigate_user_profile':
        name = (params.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'message': "I need a name to open a profile."})
        parts = name.split()
        fname, lname = parts[0], parts[1] if len(parts) > 1 else ''
        query = User.query.filter(User.id != current_user.id)
        if lname:
            query = query.filter(User.first_name.ilike(f'%{fname}%'), User.last_name.ilike(f'%{lname}%'))
        else:
            query = query.filter(User.first_name.ilike(f'%{fname}%'))
        target = query.first()
        if not target:
            return jsonify({'success': False, 'message': f"I couldn't find a user named {name}."})
        profile_url = f'/profile/{target.id}'
        return jsonify({'success': True, 'navigate': profile_url,
                        'message': f"Opening {target.first_name}'s profile!"})

    # ”€”€ SHOP ITEM: BUY / EQUIP / UNEQUIP ”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€”€
    elif action == 'shop_item':
        item_name  = (params.get('item_name') or params.get('name') or '').strip().lower()
        operation  = (params.get('operation') or '').lower()  # buy | equip | unequip

        if not item_name:
            return jsonify({'success': False, 'message': "I didn't catch which item you meant."})

        # Fuzzy match against shop catalog
        matched_id = None
        matched_item = None
        for iid, idata in ShopService.ITEMS.items():
            search_name = idata['name'].lower()
            # Strip emojis for comparison
            clean_name = ''.join(c for c in search_name if c.isascii()).strip()
            if (item_name in search_name or item_name in clean_name or
                    item_name in iid.replace('_', ' ')):
                matched_id = iid
                matched_item = idata
                break

        if not matched_item:
            return jsonify({'success': False,
                            'message': f"I couldn't find an item called '{item_name}' in the shop."})

        # ”€”€ UNEQUIP ”€”€
        if operation == 'unequip':
            user_item = UserItem.query.filter_by(user_id=current_user.id, item_id=matched_id).first()
            if not user_item:
                return jsonify({'success': False, 'message': f"You don't own {matched_item['name']}."})
            user_item.is_active = False
            db.session.commit()
            return jsonify({'success': True, 'message': f"Unequipped {matched_item['name']}! Back to default."})

        # ”€”€ EQUIP (already owned) ”€”€
        if operation == 'equip':
            result = ShopService.equip_item(current_user, matched_id)
            return jsonify({'success': result['status'] == 'success', 'message': result['message']})

        # ”€”€ BUY (then auto-equip if not consumable) ”€”€
        # First check if already owned
        already_owned = UserItem.query.filter_by(user_id=current_user.id, item_id=matched_id).first()
        if already_owned:
            # If owned but not active, equip it
            if not already_owned.is_active and matched_item['type'] != 'consumable':
                result = ShopService.equip_item(current_user, matched_id)
                return jsonify({'success': result['status'] == 'success',
                                'message': f"You already own this! {result['message']}"})
            return jsonify({'success': False, 'message': f"You already own {matched_item['name']}!"})

        # Buy it
        buy_result = ShopService.buy_item(current_user, matched_id)
        if buy_result['status'] != 'success':
            return jsonify({'success': False, 'message': buy_result['message']})

        # Auto-equip themes and frames after purchase
        if matched_item['type'] in ('theme', 'frame'):
            ShopService.equip_item(current_user, matched_id)
            return jsonify({'success': True,
                            'message': f"Bought and equipped {matched_item['name']}! {buy_result.get('new_xp', 0)} XP remaining."})

        return jsonify({'success': True, 'message': buy_result['message']})

    return jsonify({'success': False, 'message': 'Unknown action.'})




@app.route('/api/verse/welcome')
@login_required
def verse_welcome_data():
    """Return personalised welcome message data for Verse."""
    name   = current_user.first_name or 'there'
    streak = current_user.current_streak or 0
    pending = Todo.query.filter_by(user_id=current_user.id, completed=False).count()

    try:
        upcoming = Event.query.filter(
            Event.user_id == current_user.id,
            Event.date >= datetime.utcnow().date()
        ).count()
    except Exception:
        upcoming = 0

    msg = (
        f"Welcome back, {name}! "
        f"You're on a {streak}-day streak  keep it going! "
        f"You have {pending} pending task{'s' if pending != 1 else ''}"
        f"{f' and {upcoming} upcoming event{chr(115) if upcoming != 1 else chr(46)}' if upcoming else '.'} "
        f"What would you like to work on today?"
    )

    return jsonify({'message': msg, 'name': name, 'streak': streak, 'pending': pending})


# ============================================================================
# STREAK API
# ============================================================================



@app.route('/api/streak')
@login_required
def get_streak():
    """Return current user's streak info."""
    return jsonify({
        'status': 'success',
        'current_streak': current_user.current_streak or 0,
        'longest_streak': current_user.longest_streak or 0,
        'last_activity_date': str(current_user.last_activity_date) if current_user.last_activity_date else None
    })


# ============================================================================
# AUTO-CREATE NEW DB TABLES + SAFE COLUMN MIGRATIONS ON STARTUP
#
# Runs in a background daemon thread so Gunicorn can bind to $PORT immediately.
# Previously this was a blocking module-level call  if the DB connection
# took > a few seconds, Render reported "No open ports detected" and killed
# the process before it ever started serving traffic.
# ============================================================================
import threading as _threading

def _startup_db_init():
    """Run DB create_all and column migrations in the background after startup."""
    import time as _time
    _time.sleep(2)  # Give gunicorn workers a moment to fully start first
    print("[DB-INIT] Starting background database initialization...")
    try:
        with app.app_context():
            # Step 1: Create any new tables that don't exist yet
            try:
                db.create_all()
                print("  DB tables verified / created.")
            except Exception as _dbe:
                print(f"š   db.create_all() warning: {_dbe}")

            # Step 2: Safe column migrations  ADD IF NOT EXISTS for all new columns
            _is_postgres = 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', '')

            _migrations = []

            if _is_postgres:
                _migrations = [
                    # user table
                    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE',
                    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS referred_by INTEGER REFERENCES "user"(id)',
                    # group table
                    'ALTER TABLE "group" ADD COLUMN IF NOT EXISTS description VARCHAR(255)',
                    "ALTER TABLE \"group\" ADD COLUMN IF NOT EXISTS avatar_emoji VARCHAR(10) DEFAULT '“š'",
                    # group_member table
                    "ALTER TABLE group_member ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'member'",
                    'ALTER TABLE group_member ADD COLUMN IF NOT EXISTS last_read_at TIMESTAMP',
                    # group_chat_message table
                    'ALTER TABLE group_chat_message ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE',
                ]
            else:
                # SQLite does not support IF NOT EXISTS in ALTER TABLE
                _migrations = [
                    'ALTER TABLE "user" ADD COLUMN referral_code VARCHAR(20)',
                    'ALTER TABLE "user" ADD COLUMN referred_by INTEGER',
                    'ALTER TABLE "group" ADD COLUMN description VARCHAR(255)',
                    'ALTER TABLE "group" ADD COLUMN avatar_emoji VARCHAR(10)',
                    'ALTER TABLE group_member ADD COLUMN role VARCHAR(20)',
                    'ALTER TABLE group_member ADD COLUMN last_read_at TIMESTAMP',
                    'ALTER TABLE group_chat_message ADD COLUMN is_pinned BOOLEAN',
                ]

            for _sql in _migrations:
                try:
                    db.session.execute(db.text(_sql))
                    db.session.commit()
                    print(f"  Migration OK: {_sql[:70]}€¦")
                except Exception as _col_err:
                    db.session.rollback()
                    _msg = str(_col_err).lower()
                    if any(x in _msg for x in ['already exists', 'duplicate column', 'duplicate']):
                        pass  # Column already present  fine
                    else:
                        print(f"š   Migration warning: {_col_err}")

            print("  DB migrations complete.")
    except Exception as _e:
        print(f"š   DB init thread error: {_e}")

# Start DB init in background  does NOT block gunicorn from binding to $PORT
_db_init_thread = _threading.Thread(target=_startup_db_init, daemon=True, name="db-init")
_db_init_thread.start()
print("[DB-INIT] Background DB initialization thread started.")


# ============================================================================

if __name__ == '__main__':



    # Start Background Scheduler ONLY in development mode
    # In production (gunicorn), this block doesn't run, avoiding eventlet conflicts
    # For production task reminders, use a separate cron job or background worker service
    if not SCHEDULER_STARTED:
        print("Starting background task reminder scheduler (development mode only)...")
        socketio.start_background_task(check_task_reminders)
        SCHEDULER_STARTED = True

    # Use socketio.run instead of app.run
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=False, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

