# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import json,pytz
from time import sleep
import  pytz, json
from datetime import date, datetime, timedelta, time
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from diners.models import AccessLog
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Max, Min

from .models import AccessLog, Diner, ElementToEvaluate, SatisfactionRating
from cloudkitchen.settings.base import PAGE_TITLE

def get_name_day(datetime_now):
    days_list = {
        'MONDAY': 'Lunes',
        'TUESDAY': 'Martes',
        'WEDNESDAY': 'Miércoles',
        'THURSDAY': 'Jueves',
        'FRIDAY': 'Viernes',
        'SATURDAY': 'Sábado',
        'SUNDAY': 'Domingo'
    }
    name_day = date(datetime_now.year, datetime_now.month, datetime_now.day)
    return days_list[name_day.strftime('%A').upper()]


def get_number_day(dt):
    days = {
        'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Jueves': 3, 'Viernes': 4, 'Sábado': 5, 'Domingo': 6,
    }
    return days[get_name_day(dt)]


def start_datetime(back_days):
    start_date = date.today() - timedelta(days=back_days) 
    return naive_to_datetime(start_date)


def end_datetime(back_days):
    end_date = start_datetime(back_days) + timedelta(days=1)
    return naive_to_datetime(end_date)


def naive_to_datetime(nd):
    if type(nd) == datetime:
        if nd.tzinfo is not None and nd.tzinfo.utcoffset(nd) is not None: # Is Aware
            return nd
        else: # Is Naive
            return pytz.timezone('America/Mexico_City').localize(nd)              

    elif type(nd) == date:
        d = nd
        t = time(0,0)
        new_date = datetime.combine(d, t)
        return pytz.timezone('America/Mexico_City').localize(new_date)


def get_diners_per_hour():
    hours_list = []
    hours_to_count = 12
    start_hour = 5
    customter_count = 0    
    logs = get_access_logs_today()

    while start_hour <= hours_to_count:

        hour = {            
            'count': None,
        }

        for log in logs:
            datetime = str(log.access_to_room)
            date,time = datetime.split(" ")    
            if(time.startswith("0"+str(start_hour))):
                customter_count += 1 
            hour['count'] = customter_count

        hours_list.append(hour)        
        customter_count = 0
        start_hour += 1
        total_entries = 0

    return json.dumps(hours_list) 


# ------------------------- Django Views ----------------------------- #
@csrf_exempt
def RFID(request):
    if request.method == 'POST':
        rfid = str(request.body).split('"')[3].replace(" ", "")
        if settings.DEBUG:
            print(rfid)

        if rfid is None:
            if settings.DEBUG:
                print('no se recibio rfid')
            return HttpResponse('No se recibió RFID\n')
        else:
            access_logs = get_access_logs_today()
            exists = False
            
            for log in access_logs:
                if rfid == log.RFID:
                    exists = True
                    break

            if exists:
                if settings.DEBUG:
                    print('El usuario ya se ha registrado')
                return HttpResponse('El usuario ya se ha registrado')
            else:
                if len(rfid) < 7:
                    try:
                        diner = Diner.objects.get(RFID=rfid)
                        new_access_log = AccessLog(diner=diner, RFID=rfid)
                        new_access_log.save()
                    except Diner.DoesNotExist:
                        new_access_log = AccessLog(diner=None, RFID=rfid)
                        new_access_log.save()   
                else:
                    if settings.DEBUG:
                        print('RFID Inválido\n')
                    return HttpResponse('RFID Inválido\n')

        return HttpResponse('Operacion Terminada\n')

    else:
        return redirect('diners:diners')


def satisfaction_rating(request):
    if request.method == 'POST':
        if request.POST['type'] == 'satisfaction_rating':
            satisfaction_rating = request.POST['satisfaction_rating']
            elements_list = json.loads(request.POST['elements_id'])

            if request.POST['suggestion']:
                new_satisfaction_rating = SatisfactionRating.objects.create(
                    satisfaction_rating=satisfaction_rating,
                    suggestion=request.POST['suggestion'],
                )
            else:
                new_satisfaction_rating = SatisfactionRating.objects.create(
                    satisfaction_rating=satisfaction_rating
                )
            new_satisfaction_rating.save();

            for element in elements_list:
                new_element = ElementToEvaluate.objects.get(id=element)
                new_satisfaction_rating.elements.add(new_element)
                new_satisfaction_rating.save()
            return JsonResponse({'status':'ready'})


    template = 'satisfaction_rating.html'
    title = 'Rating'
    elements = ElementToEvaluate.objects.all()
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        'elements': elements,
    }
    return render (request, template, context)


@login_required(login_url='users:login')
def analytics(request):
    template = 'analytics.html'
    title = 'Analytics'
    # ratings = SatisfactionRating.objects.all()
    tests = SatisfactionRating.objects.order_by('-creation_date')
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        # 'ratings': ratings,
        'tests': tests,
    }
    return render (request, template, context)


@login_required(login_url='users:login')
def suggestions(request):
    template = 'suggestions.html'
    title = 'Analytics'
    # ratings = SatisfactionRating.objects.all()
    tests = SatisfactionRating.objects.order_by('-creation_date')
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        # 'ratings': ratings,
        'tests': tests,
    }
    return render (request, template, context)


# --------------------------- TEST ------------------------
@login_required(login_url='users:login')
def test(request):
    rfids = [ 52661 ,]

    for rfid in rfids:
        dt = naive_to_datetime(datetime(2017,3,23,13,30))
        rfid = str(rfid)
        if rfid is None:
            print('No se recibió RFID\n')
        else:
            access_logs = get_access_logs(dt)
            exists = False
            
            for log in access_logs:
                if rfid == log.RFID:
                    exists = True
                    if settings.DEBUG:
                        print('es identico...........')
                    break

            if exists:
                if settings.DEBUG:
                    print('El usuario ya se ha registrado')
            else:
                if len(rfid) < 7:
                    try:
                        diner = Diner.objects.get(RFID=rfid)
                        new_access_log = AccessLog(diner=diner, RFID=rfid, access_to_room=dt)
                        new_access_log.save()
                    except Diner.DoesNotExist:
                        new_access_log = AccessLog(diner=None, RFID=rfid, access_to_room=dt)
                        new_access_log.save()
                        if settings.DEBUG:   
                            print('Nuevo comensal\n')
                else:
                    if settings.DEBUG:
                        print('RFID Inválido\n')

    return HttpResponse('Hola')