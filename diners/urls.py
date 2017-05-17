from django.conf import settings
from django.conf.urls import url

from diners import views


app_name = 'diners'

urlpatterns = [
    # Diners pin
    url(r'^diners/rfid/$', views.RFID, name='rfid'),
    url(r'^diners/satisfaction-rating/$', views.satisfaction_rating, name='satisfaction_rating'),
    url(r'^diners/analytics/$', views.analytics, name='analytics'),
    url(r'^diners/suggestions/$', views.suggestions, name='suggestions'),
]

# Test
if settings.DEBUG:
    urlpatterns.append( url(r'^diners/test/$', views.test, name='diners_test'))
