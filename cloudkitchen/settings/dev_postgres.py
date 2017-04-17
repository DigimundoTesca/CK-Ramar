from cloudkitchen.settings.dev import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('RAMAR_DB_NAME'),
        'USER': os.getenv('RAMAR_DB_USER'),
        'PASSWORD': os.getenv('RAMAR_DB_PASSWORD'),
        'HOST': os.getenv('RAMAR_DB_HOST'),
        'PORT': os.getenv('RAMAR_DB_PORT'),
    }
}


INSTALLED_APPS.append('django-extension')

GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}
