from dotenv import load_dotenv
import os
import multiprocessing

# Load environment variables from a .env file
load_dotenv('/root/wisdomvault/.env')  # Adjust the path to your .env file

bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8004')  # Updated default to 8001 to avoid confusion
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
threads = int(os.getenv('GUNICORN_THREADS', 2))
timeout = int(os.getenv('GUNICORN_TIMEOUT', 30))
loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info')
accesslog = os.getenv('GUNICORN_ACCESSLOG', '-')
errorlog = os.getenv('GUNICORN_ERRORLOG', '-')
capture_output = True
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 50))
graceful_timeout = int(os.getenv('GUNICORN_GRACEFUL_TIMEOUT', 30))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 2))

