import os
import multiprocessing

# Port binding (Dynamic PORT bind for Render and Railway compatibility)
port = os.environ.get('PORT', '5001')
bind = f"0.0.0.0:{port}"

# Gunicorn configuration values
backlog = 2048

# Worker configurations (CPU count-based worker sizing)
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
errorlog = '-'
accesslog = '-'
loglevel = 'info'
capture_output = True
enable_stdio_inheritance = True
