from cloudkitchen.settings.dev import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('RAMAR_DB_NAME'),
        'USER': os.getenv('RAMAR_DB_USER'),
        'PASSWORD': os.getenv('RAMAR_DB_PASSWORD'),
        'HOST': os.getenv('RAMAR_DB_HOST'),
        'PORT': os.getenv('RAMAR_DB_PORT'),
        'OPTIONS': {
        }  
    }
}
