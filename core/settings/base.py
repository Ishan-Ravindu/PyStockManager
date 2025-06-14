import os
from pathlib import Path
from django.urls import reverse_lazy
from django.templatetags.static import static

BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "dashboard",
    "unfold", 
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.guardian",
    "unfold.contrib.simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "simple_history",
    "import_export",
    "guardian",
    "home",
    "inventory",
    "account",
    "receipt",
    "purchase_invoice",
    "payment",
    "sale_invoice",
    "shop",
    "supplier",
    "product",
    "customer",
    "expense",
    "config"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"

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
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Colombo"
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/debug.log',  # Path to your log file
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}

SIMPLE_HISTORY_REVERT_DISABLED = True

UNFOLD = {
    "SITE_TITLE": "MS Sports",
    "SITE_HEADER": "MS Sports",
    "SITE_SUBHEADER": "Play Genuine Pay Less",
    "SIDEBAR": {
    "navigation": [
        # Main Dashboard Section
        {
            "separator": False,
            "collapsible": False,
            "items": [
                {
                    "title": "Dashboard",
                    "icon": "dashboard",
                    "link": reverse_lazy("admin:index"),
                    "permission": lambda request: request.user.is_superuser,
                },
            ],
        },
        # Sales & Purchases Section
        {
            "separator": True, 
            "collapsible": False,
            "title": "Transactions",
            "items": [
                {
                    "title": "Sales Invoices",
                    "icon": "receipt_long",
                    "link": reverse_lazy("admin:sale_invoice_salesinvoice_changelist"),
                    "permission": lambda request: request.user.has_perm("sale_invoice.can_view_icon_sale_invoice"),
                },
                {
                    "title": "Purchase Invoices",
                    "icon": "shopping_cart",
                    "link": reverse_lazy("admin:purchase_invoice_purchaseinvoice_changelist"),
                    "permission": lambda request: request.user.has_perm("purchase_invoice.can_view_icon_purchase_invoice"),
                },
            ],
        },
        # Financial Section
        {
            "separator": True,
            "collapsible": False,
            "title": "Finance",
            "items": [
                {
                    "title": "Accounts",
                    "icon": "credit_card",
                    "link": reverse_lazy("admin:account_account_changelist"),
                    "permission": lambda request: request.user.has_perm("account.can_view_icon_account"),
                },
                {
                    "title": "Expenses",
                    "icon": "money",
                    "link": reverse_lazy("admin:expense_expense_changelist"),
                    "permission": lambda request: request.user.has_perm("expense.can_view_icon_expense"),
                },
                {
                    "title": "Withdrawals",
                    "icon": "money_off",
                    "link": reverse_lazy("admin:account_withdraw_changelist"),
                    "permission": lambda request: request.user.has_perm("withdraw.can_view_icon_withdraw"),
                },
                {
                    "title": "Account Transfers",
                    "icon": "swap_horiz",
                    "link": reverse_lazy("admin:account_accounttransfer_changelist"),
                    "permission": lambda request: request.user.has_perm("account_accounttransfer.can_view_icon_account_account_transfer"),
                },
                {
                    "title": "Payments",
                    "icon": "payments",
                    "link": reverse_lazy("admin:payment_payment_changelist"),
                    "permission": lambda request: request.user.has_perm("payment.can_view_icon_payment"),
                },
                {
                    "title": "Receipts",
                    "icon": "receipt",
                    "link": reverse_lazy("admin:receipt_receipt_changelist"),
                    "permission": lambda request: request.user.has_perm("receipt.can_view_icon_receipt"),
                },
            ],
        },
        # Inventory & Products Section
        {
            "separator": True,
            "collapsible": False,
            "title": "Inventory",
            "items": [
                {
                    "title": "Products",
                    "icon": "inventory_2",
                    "link": reverse_lazy("admin:product_product_changelist"),
                    "permission": lambda request: request.user.has_perm("product.can_view_icon_product"),
                },
                {
                    "title": "Categories",
                    "icon": "category",
                    "link": reverse_lazy("admin:product_category_changelist"),
                    "permission": lambda request: request.user.has_perm("category.can_view_icon_category"),
                },
                {
                    "title": "Stock",
                    "icon": "inventory",
                    "link": reverse_lazy("admin:inventory_stock_changelist"),
                    "permission": lambda request: request.user.has_perm("inventory.can_view_icon_stock"),
                },
                {
                    "title": "Stock Transfers",
                    "icon": "swap_vert",
                    "link": reverse_lazy("admin:inventory_stocktransfer_changelist"),
                    "permission": lambda request: request.user.has_perm("inventory.can_view_icon_stock_transfe"),
                },
                {
                    "title": "Shops",
                    "icon": "store",
                    "link": reverse_lazy("admin:shop_shop_changelist"),
                    "permission": lambda request: request.user.has_perm("shop.can_view_icon"),
                },
            ],
        },
        # People Section
        {
            "separator": True,
            "collapsible": False,
            "title": "People",
            "items": [
                {
                    "title": "Customers",
                    "icon": "people",
                    "link": reverse_lazy("admin:customer_customer_changelist"),
                    "permission": lambda request: request.user.has_perm("customer.can_view_icon_customer"),
                },
                {
                    "title": "Suppliers",
                    "icon": "local_shipping",
                    "link": reverse_lazy("admin:supplier_supplier_changelist"),
                    "permission": lambda request: request.user.has_perm("supplier.can_view_icon_supplier"),
                },
                {
                    "title": "Users",
                    "icon": "admin_panel_settings",
                    "link": reverse_lazy("admin:auth_user_changelist"),
                    "permission": lambda request: request.user.has_perm("auth.view_user"),
                },
                {
                    "title": "Groups",
                    "icon": "group_work",
                    "link": reverse_lazy("admin:auth_group_changelist"),
                    "permission": lambda request: request.user.has_perm("auth.view_group"),
                },
            ],
        },
    ],
},

    # hack for avoid this issue(https://github.com/unfoldadmin/django-unfold/issues/1211) 
    # if issue fixed remove the custom css
    "STYLES": [
        lambda request: static("css/styles.css"),
    ]
}

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'guardian.backends.ObjectPermissionBackend',
)