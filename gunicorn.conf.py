# gunicorn.conf.py
# ============================================================
# Gunicorn configuration for StudyVerse on Render.com
#
# Why this file exists:
# ---------------------
# Flask-SocketIO requires eventlet worker class for real-time
# WebSocket support. However, gunicorn 21.x + eventlet has a
# known bug where monkey_patch() in app.py infects the master
# process, causing:
#   RuntimeError: do not call blocking functions from the mainloop
#
# This config file ensures proper isolation.
# ============================================================

import eventlet
import eventlet.wsgi

# Gunicorn settings
worker_class = "eventlet"
workers = 1          # Must be 1 with eventlet worker class
threads = 1          # Single thread per worker (eventlet handles concurrency)
timeout = 180        # 180s — gemini-2.5-flash vision can take 30-60s on complex images
keepalive = 5        # Keep connections alive for 5s
graceful_timeout = 30

# Bind is set via --bind flag in the start command (uses $PORT env var)

# Logging
loglevel = "info"
accesslog = "-"      # Log access to stdout
errorlog = "-"       # Log errors to stdout

# Pre-load the app in the master process BEFORE forking workers
# This prevents the eventlet hub conflict in the master process
preload_app = False  # Must be False for eventlet workers (can't share hub between processes)

# Worker lifecycle hooks
def post_fork(server, worker):
    """Called after a worker process is forked from the master."""
    # Re-patch eventlet in each worker to ensure a clean hub per worker
    eventlet.monkey_patch()

def pre_exec(server):
    """Called just before a new master process is exec'd."""
    server.log.info("Master process reloading...")

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("StudyVerse starting up with eventlet workers...")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker {worker.pid} exited.")
