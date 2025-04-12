from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "23423rfe7!x8f3p@4nwq2z*6k9jm5"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database (from devcontainer)
DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.mysql",
        'NAME': "devdb",
        'USER': "root",
        'PASSWORD': "rootpassword",
        'HOST': "db",
        'PORT': "3306",
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
        }
    }
}