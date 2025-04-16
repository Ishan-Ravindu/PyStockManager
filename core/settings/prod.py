import os
from .base import *

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'fallback-key-should-be-replaced-in-production')

DEBUG = False

ALLOWED_HOSTS = ['mssports.lk', 'www.mssports.lk']

DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.mysql",
        'NAME': "mssports",
        'USER': "mssports",
        'PASSWORD': "123Mssports123Mssports",
        'HOST': "118.139.180.214",
        'PORT': "3306",
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
        }
    }
}

CSRF_TRUSTED_ORIGINS = [
    "https://mssports.lk",
    "https://www.mssports.lk",
]