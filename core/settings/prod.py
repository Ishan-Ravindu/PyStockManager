import os
from .base import *

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-key-should-be-replaced-in-production')

DEBUG = False

# user proper env to handle this

ALLOWED_HOSTS = ['example.lk', 'www.example.lk']

DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.mysql",
        'NAME': "example",
        'USER': "example",
        'PASSWORD': "example",
        'HOST': "xxx.xxx.xxx.xxx",
        'PORT': "3306",
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
        }
    }
}

CSRF_TRUSTED_ORIGINS = [
    "https://example.lk",
    "https://www.example.lk",
]