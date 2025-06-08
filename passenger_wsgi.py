import os
import sys

# Step 1: Set project and virtualenv paths
project_path = '/home/j9bqcm7s1zfp/example'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Step 2: Set Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['DJANGO_ENVIRONMENT'] = 'prod'

# Step 3: Load Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
