# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, timedelta

import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Min
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from cloudkitchen.settings.base import PAGE_TITLE
from helpers import Helper, DinersHelper, RatesHelper
from .models import AccessLog, Diner, ElementToEvaluate, SatisfactionRating


# ------------------------- Django Views ----------------------------- #
@csrf_exempt
def rfid(request):
    diners_helper = DinersHelper()
    if request.method == 'POST':
        rfid_str = str(request.body).split('"')[3].replace(" ", "")
        if settings.DEBUG:
            print(rfid_str)

        if rfid_str is None:
            if settings.DEBUG:
                print('no se recibio rfid')
            return HttpResponse('No se recibió RFID\n')
        else:
            today_access_logs = diners_helper.get_access_logs_today()
            exists = False
            
            for log in today_access_logs:
                if rfid_str == log.RFID:
                    exists = True
                    break

            if exists:
                if settings.DEBUG:
                    print('El usuario ya se ha registrado')
                return HttpResponse('El usuario ya se ha registrado')
            else:
                if len(rfid_str) < 7:
                    try:
                        diner = Diner.objects.get(RFID=rfid_str)
                        new_access_log = AccessLog(diner=diner, RFID=rfid_str)
                        new_access_log.save()
                    except Diner.DoesNotExist:
                        new_access_log = AccessLog(diner=None, RFID=rfid_str)
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
            satisfaction_rating_value = request.POST['satisfaction_rating']
            if int(satisfaction_rating_value) > 4:
                satisfaction_rating_value = 4
            elements_list = json.loads(request.POST['elements_id'])

            if request.POST['suggestion']:
                new_satisfaction_rating = SatisfactionRating.objects.create(
                    satisfaction_rating=satisfaction_rating_value,
                    suggestion=request.POST['suggestion'],
                )
            else:
                new_satisfaction_rating = SatisfactionRating.objects.create(
                    satisfaction_rating=satisfaction_rating_value
                )
            new_satisfaction_rating.save()

            for element in elements_list:
                new_element = ElementToEvaluate.objects.get(id=element)
                new_satisfaction_rating.elements.add(new_element)
                new_satisfaction_rating.save()
            return JsonResponse({'status': 'ready'})

    template = 'satisfaction_rating.html'
    title = 'Rating'
    elements = ElementToEvaluate.objects.all()
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        'elements': elements,
    }
    return render(request, template, context)


@login_required(login_url='users:login')
def analytics(request):
    helper = Helper()
    rates_helper = RatesHelper()

    if request.method == 'POST':
        if request.POST['type'] == 'reactions_day':
            start_date = helper.naive_to_datetime(datetime.strptime(request.POST['date'], '%d-%m-%Y').date())
            end_date = helper.naive_to_datetime(start_date + timedelta(days=1))
            today_suggestions = rates_helper.get_satisfaction_ratings(start_date, end_date)
            reactions_list = []
            for element_to_evaluate in rates_helper.elements_to_evaluate:
                """ For every element chart """
                element_object = {
                    'id': element_to_evaluate.id,
                    'name': element_to_evaluate.element,
                    'reactions': {
                        0: {'reaction': 'Enojado', 'quantity': 0},
                        1: {'reaction': 'Triste', 'quantity': 0},
                        2: {'reaction': 'Feliz', 'quantity': 0},
                        3: {'reaction': 'Encantado', 'quantity': 0},
                    },
                }
                for suggestion in today_suggestions:
                    for element_in_suggestion in suggestion.elements.all():
                        if element_in_suggestion == element_to_evaluate:
                            element_object['reactions'][suggestion.satisfaction_rating-1]['quantity'] += 1

                reactions_list.append(element_object)
            return JsonResponse(reactions_list, safe=False)
        elif request.POST['type'] == 'reactions_week':
            initial_date = helper.parse_to_datetime(request.POST['dt_week'].split(',')[0])
            final_date = helper.parse_to_datetime(request.POST['dt_week'].split(',')[1])
            data = {
                'week_number': helper.get_week_number(initial_date),
                'suggestions': rates_helper.get_rates_list(initial_date, final_date),
            }
            return JsonResponse(data)

    template = 'analytics.html'
    title = 'Analytics'
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        'dates_range': rates_helper.get_dates_range(),
        'suggestions_week': rates_helper.get_rates_actual_week(),
        'elements': rates_helper.elements_to_evaluate,
        'total_elements': rates_helper.elements_to_evaluate.count(),
    }
    return render(request, template, context)


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
    return render(request, template, context)


# --------------------------- TEST ------------------------
@login_required(login_url='users:login')
def test(request):
    
    return HttpResponse('Your tests here')
