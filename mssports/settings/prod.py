import os
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
# In production, set this using environment variables
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-key-should-be-replaced-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Add your production domain(s) here
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Database
# Use environment variables for sensitive database credentials
DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.mysql",
        'NAME': os.environ.get('DB_NAME', 'mssports'),
        'USER': os.environ.get('DB_USER', 'mssports'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
        }
    }
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'