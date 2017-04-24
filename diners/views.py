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


class Logic(object):
    """
    Auxiliar Functions to views logic
    TODO: assign a good name to the class
    """
    def __init__(self):
        self.tz = pytz.timezone('America/Mexico_City')
        super(Logic, self).__init__()
        
    def get_name_day(self, datetime_now):
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

    def get_number_day(self, dt):
        days = {
            'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Jueves': 3, 'Viernes': 4, 'Sábado': 5, 'Domingo': 6,
        }
        return days[self.get_name_day(dt)]

    def get_start_week_day(self, day):
        format = "%w"
        number_day = int(self.naive_to_datetime(day).strftime(format))
        if number_day ==  0:
            number_day = 7
        else:
            day = self.naive_to_datetime(day) - timedelta(days=number_day-1)

    def start_datetime(self, back_days):
        start_date = date.today() - timedelta(days=back_days) 
        return self.naive_to_datetime(start_date)

    def end_datetime(self, back_days):
        end_date = self.start_datetime(back_days) + timedelta(days=1)
        return self.naive_to_datetime(end_date)

    def naive_to_datetime(self, nd):
        if type(nd) == datetime:
            if nd.tzinfo is not None and nd.tzinfo.utcoffset(nd) is not None: # Is Aware
                return nd
            else: # Is Naive
                return self.tz.localize(nd)              

        elif type(nd) == date:
            d = nd
            t = time(0,0)
            new_date = datetime.combine(d, t)
            return self.tz.localize(new_date)


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
    logic = Logic()
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
            years_list = [] # [2015:object, 2016:object, 2017:object, ...]
        except:
            return HttpResponse('Necesitas crear ventas para ver esta pantalla <a href="sales:new">Nueva Venta</a>')
            
        while max_year >= min_year:
            year_object = { # 2015:object or 2016:object or 2017:object ...
                'year' : max_year,
                'weeks_list' : []
            }

            ratings_per_year = all_suggestions.filter(
                creation_date__range=[logic.naive_to_datetime(date(max_year,1,1)),logic.naive_to_datetime(date(max_year,12,31))])
            for rating in ratings_per_year:
                if len(year_object['weeks_list']) == 0: 
                    """
                    Creates a new week_object in the weeks_list of the actual year_object
                    """
                    start_week_day = logic.get_start_week_day(rating.creation_date.date())
                    week_object = { 
                        'week_number': rating.creation_date.isocalendar()[1],
                        'start_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                        'end_date': rating.creation_date.date().strftime("%d-%m-%Y"),
                    }
                    year_object['weeks_list'].append(week_object)
                    # End if
                else: 
                    """
                    Validates if exists some week with an indentical week_number of the actual year
                    If exists a same week in the list validates the start_date and the end_date,
                    In each case valid if there is an older start date or a more current end date 
                        if it is the case, update the values.
                    Else creates a new week_object with the required week number
                    """
                    existing_week = False
                    for week_object in year_object['weeks_list']:

                        if week_object['week_number'] == rating.creation_date.isocalendar()[1]:
                            # There's a same week number
                            existing_week = True
                            if datetime.strptime(week_object['start_date'], "%d-%m-%Y").date() > rating.creation_date.date():
                                exists = True
                                week_object['start_date'] = rating.creation_date.date().strftime("%d-%m-%Y")
                            elif datetime.strptime(week_object['end_date'], "%d-%m-%Y").date() < rating.creation_date.date():
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

                    #End else
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
        days_to_count = logic.get_number_day(datetime.now())
        day_limit = days_to_count
        start_date_number = 0
        
        while start_date_number <= day_limit:
            day_object = {
                'date': str(logic.start_datetime(days_to_count).date().strftime('%d-%m-%Y')),
                'day_name': None,
                'total_suggestions': None,
                'number_day': logic.get_number_day(logic.start_datetime(days_to_count).date()),
            }

            suggestions = all_suggestions.filter(creation_date__range=[logic.start_datetime(days_to_count), logic.end_datetime(days_to_count)])

            for suggestion in suggestions:
                if suggestion.suggestion:
                    total_suggestions += 1

            day_object['total_suggestions'] = str(total_suggestions)
            day_object['day_name'] = logic.get_name_day(logic.start_datetime(days_to_count).date())

            week_suggestions_list.append(day_object)

            # restarting counters
            days_to_count -= 1
            total_suggestions = 0
            start_date_number += 1

        return json.dumps(week_suggestions_list)

    def  get_suggestions(initial_date, final_date):
        return all_suggestions.filter(
                creation_date__range=(initial_date, final_date)).order_by('-creation_date')

    if request.method == 'POST':
        if request.POST['type'] == 'reactions_day':
            start_date = logic.naive_to_datetime(datetime.strptime(request.POST['date'], '%d-%m-%Y').date())
            end_date = logic.naive_to_datetime(start_date + timedelta(days=1))
            today_suggestions = get_suggestions(start_date, end_date)
            reactions_list = []
            for element_to_evaluate in all_elements:
                """ For every element chart """
                element_object = {
                    'id': element_to_evaluate.id,
                    'name': element_to_evaluate.element,
                    'reactions': {
                        0:{'reaction':'Enojado', 'quantity': 0},
                        1:{'reaction':'Triste', 'quantity': 0},
                        2:{'reaction':'Feliz', 'quantity': 0},
                        3:{'reaction':'Encantado', 'quantity': 0},
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
        'suggestions_week':get_suggestions_actual_week(),
        'elements': all_elements,
        'total_elements': all_elements.count(),
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
    
    return HttpResponse('Hola')