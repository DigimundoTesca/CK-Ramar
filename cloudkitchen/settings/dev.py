from cloudkitchen.settings.base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, '../db_temporal.sqlite3'),
    }
}
INSTALLED_APPS.append('django_extensions')

GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}
