from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "23423rfe7!x8f3p@4nwq2z*6k9jm5"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database
DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.postgresql",
        'NAME': "postgres",
        'USER': "postgres",
        'PASSWORD': "postgres",
        'HOST': "localhost",
        'PORT': "5432",
    }
}