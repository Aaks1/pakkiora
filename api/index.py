#!/usr/bin/env python
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables from .env file (critical for Vercel)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass  # dotenv not available, continue without it

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')

# Load Django
import django
django.setup()

# Import WSGI application
from django.core.wsgi import get_wsgi_application

# Vercel handler - must be at top level
def handler(environ, start_response):
    """Vercel serverless function handler"""
    wsgi_app = get_wsgi_application()
    return wsgi_app(environ, start_response)

# Alternative names for compatibility
app = handler
application = handler
