import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-cjr!0n7&56tn7_u09#lhw9@ud14@0td1q@zl#%zd*9jk5st-qu")

DEBUG = int(os.environ.get("DEBUG", default=True))

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "home",
    "inventory",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mssports.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mssports.wsgi.application"

if DEBUG:
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
else:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get("SQL_ENGINE"),
            'NAME': os.environ.get("SQL_DATABASE"),
            'USER': os.environ.get("SQL_USER"),
            'PASSWORD': os.environ.get("SQL_PASSWORD"),
            'HOST': os.environ.get("SQL_HOST"),
            'PORT': os.environ.get("SQL_PORT"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Colombo"

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JAZZMIN_SETTINGS = {
    # Title on the login screen
    "site_title": "MS Sports",
    
    # Title on the brand (top left)
    "site_header": "MS Sports",
    
    # Title on the browser tab
    "site_brand": "MS Sports",
    
    # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",
    
    # Welcome text on the login screen
    "welcome_sign": "Welcome to the MS Sports System",
    
    # Copyright on the footer
    "copyright": "MS Sports",  
    
    # Custom icons for side menu apps/models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "inventory.shop": "fas fa-store",
        "inventory.product": "fas fa-box",
        "inventory.stock": "fas fa-warehouse",
        "inventory.supplier": "fas fa-truck",
        "inventory.customer": "fas fa-users",
        "inventory.purchaseinvoice": "fas fa-file-invoice-dollar",
        "inventory.salesinvoice": "fas fa-receipt",
        "inventory.stocktransfer": "fas fa-exchange-alt",
    },
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
}
