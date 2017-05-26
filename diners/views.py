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
from helpers import Helper, DinersHelper
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
    all_suggestions = SatisfactionRating.objects.all()
    all_elements = ElementToEvaluate.objects.all()

    def get_dates_range():
        """
        Returns a JSON with a years list.
        The years list contains years objects that contains a weeks list
            and the Weeks list contains a weeks objects with two attributes: 
            start date and final date. Ranges of each week.
        """
        try:
            min_year = all_suggestions.aggregate(Min('creation_date'))['creation_date__min'].year
            max_year = all_suggestions.aggregate(Max('creation_date'))['creation_date__max'].year
            years_list = []  # [2015:object, 2016:object, 2017:object, ...]
        except:
            min_year = datetime.now().year
            max_year = datetime.now().year
            years_list = []  # [2015:object, 2016:object, 2017:object, ...]
            
        while max_year >= min_year:
            year_object = {  # 2015:object or 2016:object or 2017:object ...
                'year': max_year,
                'weeks_list': [],
            }

            ratings_per_year = all_suggestions.filter(
                creation_date__range=[
                    helper.naive_to_datetime(date(max_year, 1, 1)),
                    helper.naive_to_datetime(date(max_year, 12, 31))])

            for rating in ratings_per_year:
                if not year_object['weeks_list']:
                    """
                    Creates a new week_object in the weeks_list of the actual year_object
                    """
                    week_object = {
                        'week_number': rating.creation_date.isocalendar()[1],
                        'start_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                        'end_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                    }
                    year_object['weeks_list'].append(week_object)
                    # End if
                else: 
                    """
                    Validates if exists some week with an similar week_number of the actual year
                    If exists a same week in the list validates the start_date and the end_date,
                    In each case valid if there is an older start date or a more current end date 
                        if it is the case, update the values.
                    Else creates a new week_object with the required week number
                    """
                    existing_week = False
                    for week_object in year_object['weeks_list']:

                        if week_object['week_number'] == rating.creation_date.isocalendar()[1]:
                            # There's a same week number
                            if datetime.strptime(week_object['start_date'], "%d-%m-%Y").date() > \
                                    rating.creation_date.date():
                                week_object['start_date'] = rating.creation_date.date().strftime("%d-%m-%Y")
                            elif datetime.strptime(week_object['end_date'], "%d-%m-%Y").date() < \
                                    rating.creation_date.date():
                                week_object['end_date'] = rating.creation_date.date().strftime("%d-%m-%Y")

                            existing_week = True
                            break

                    if not existing_week:
                        # There's a different week number
                        week_object = { 
                            'week_number': rating.creation_date.isocalendar()[1],
                            'start_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                            'end_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                        }
                        year_object['weeks_list'].append(week_object)

                    # End else
            # End While
            year_object['weeks_list'].reverse()
            years_list.append(year_object)
            max_year -= 1
        # End while
        return json.dumps(years_list)

    def get_suggestions_actual_week():
        """
        Gets the following properties for each week's day: Name, Date and suggestions
        """
        week_suggestions_list = []
        total_suggestions = 0
        days_to_count = helper.get_number_day(datetime.now())
        day_limit = days_to_count
        start_date_number = 0
        
        while start_date_number <= day_limit:
            day_object = {
                'date': str(helper.start_datetime(days_to_count).date().strftime('%d-%m-%Y')),
                'day_name': None,
                'total_suggestions': None,
                'number_day': helper.get_number_day(helper.start_datetime(days_to_count).date()),
            }

            filtered_suggestions = all_suggestions.filter(
                creation_date__range=[helper.start_datetime(days_to_count), helper.end_datetime(days_to_count)])

            for filtered_suggestion in filtered_suggestions:
                if filtered_suggestion.suggestion:
                    total_suggestions += 1

            day_object['total_suggestions'] = str(total_suggestions)
            day_object['day_name'] = helper.get_name_day(helper.start_datetime(days_to_count).date())

            week_suggestions_list.append(day_object)

            # restarting counters
            days_to_count -= 1
            total_suggestions = 0
            start_date_number += 1

        return json.dumps(week_suggestions_list)

    def get_suggestions(initial_date, final_date):
        return all_suggestions.filter(
                creation_date__range=(initial_date, final_date)).order_by('-creation_date')

    if request.method == 'POST':
        if request.POST['type'] == 'reactions_day':
            start_date = helper.naive_to_datetime(datetime.strptime(request.POST['date'], '%d-%m-%Y').date())
            end_date = helper.naive_to_datetime(start_date + timedelta(days=1))
            today_suggestions = get_suggestions(start_date, end_date)
            reactions_list = []
            for element_to_evaluate in all_elements:
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
    template = 'analytics.html'
    title = 'Analytics'
    # ratings = SatisfactionRating.objects.all()
    context = {
        'title': PAGE_TITLE + ' | ' + title,
        'page_title': title,
        'dates_range': get_dates_range(),
        'suggestions_week': get_suggestions_actual_week(),
        'elements': all_elements,
        'total_elements': all_elements.count(),
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
    
    return HttpResponse('Hola')
