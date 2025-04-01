import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-cjr!0n7&56tn7_u09#lhw9@ud14@0td1q@zl#%zd*9jk5st-qu")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(os.environ.get("DEBUG", default=True))

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(" ")


# Application definition

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


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get("SQL_ENGINE", "django.db.backends.postgresql"),
        'NAME': os.environ.get("SQL_DATABASE", "postgres"),
        'USER': os.environ.get("SQL_USER", "postgres"),
        'PASSWORD': os.environ.get("SQL_PASSWORD", "postgres"),
        'HOST': os.environ.get("SQL_HOST", "localhost"),
        'PORT': os.environ.get("SQL_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'

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

# CSRF settings
# CSRF_TRUSTED_ORIGINS =os.environ.get("CSRF_TRUSTED_ORIGINS", ["http://localhost:8080", "http://127.0.0.1:8080"])
# CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
# SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
# CSRF_COOKIE_HTTPONLY = False  # For debugging purposes
# CSRF_USE_SESSIONS = False  # For testing, store CSRF in cookie