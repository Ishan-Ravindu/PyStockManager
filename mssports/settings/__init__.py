import os

# Load the appropriate settings file based on the DJANGO_ENVIRONMENT environment variable
environment = os.environ.get('DJANGO_ENVIRONMENT', 'dev')

if environment == 'prod':
    from .prod import *
else:
    from .dev import *