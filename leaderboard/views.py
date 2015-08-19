from __future__ import division
from django.shortcuts import render
from survey.models import Commutersurvey, Employer, Leg, Month, Team, Mode
from django.shortcuts import render_to_response
from django.template import RequestContext
# from django.db.models import Sum,Count
from django.db.models import Q
from aggregate_if import Count, Sum
from django.db.models import Count

from datetime import date, datetime
import datetime

def calculate_rankings(company_dict):
    ranks = {}
    ranks['percent_green_commuters'], ranks['percent_participation'], ranks['percent_green_switches'], ranks['percent_healthy_switches'], ranks['percent_avg_participation'] = [],[],[],[],[]

    top_percent_green = sorted(company_dict.keys(), key=lambda x: company_dict[x]['already_green'], reverse=True)[:10]
    for key in top_percent_green:
        ranks['percent_green_commuters'].append([key, company_dict[key]['already_green']])

    top_participation = sorted(company_dict.keys(), key=lambda x: company_dict[x]['participants'], reverse=True)[:10]
    for key in top_participation:
        ranks['percent_participation'].append([key, company_dict[key]['participants']])

    top_gs = sorted(company_dict.keys(), key=lambda x: company_dict[x]['green_switch'], reverse=True)[:10]
    for key in top_gs:
        ranks['percent_green_switches'].append([key, company_dict[key]['green_switch']])

    top_hs = sorted(company_dict.keys(), key=lambda x: company_dict[x]['healthy_switch'], reverse=True)[:10]
    for key in top_hs:
        ranks['percent_healthy_switches'].append([key, company_dict[key]['healthy_switch']])

    top_avg_participation = sorted(company_dict.keys(), key=lambda x: company_dict[x]['avg_participation'], reverse=True)[:10]
    for key in top_avg_participation:
        ranks['percent_avg_participation'].append([key, company_dict[key]['avg_participation']])

    return ranks


def calculate_metrics(company, selected_month):

    months_dict = { 'all': 'all', 'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06', 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12' }
    shortmonth = months_dict[selected_month]

    percent_participants = 100*company.percent_participation(shortmonth)
    percent_already_green = 100*company.percent_already_green(shortmonth)
    percent_green_switch = 100*company.percent_green_switch(shortmonth)
    percent_healthy_switch = 100*company.percent_healthy_switch(shortmonth)
    percent_participants_average = 100*company.average_percent_participation()

    num_checkins = company.num_checkins(shortmonth)
    total_C02 = company.total_C02(shortmonth)
    total_calories = company.total_calories(shortmonth)

    return {
        'participants': round(percent_participants,2),
        'already_green': round(percent_already_green,2),
        'green_switch': round(percent_green_switch,2),
        'healthy_switch': round(percent_healthy_switch,2),
        'avg_participation': round(percent_participants_average,2),
        'num_checkins': num_checkins,
        'total_C02': total_C02,
        'total_calories': total_calories
        }

def company(request, employerid=None, teamid=None):
    context = RequestContext(request)

    if not employerid:
        companies = Employer.objects.exclude(id__in=[32,33,34,38,39,40]).filter(active2015=True)
        return render_to_response('pick_company.html', { 'companies': companies }, context)

    else:
        if teamid:
            company = Team.objects.get(id=teamid)
        else:
            company = Employer.objects.get(id=employerid)

        """
        Build dictionary storing results for all stats for all months
        """
        past_months = Month.objects.filter(open_checkin__lte=date.today(), open_checkin__gt=('2015-03-31')).count()
        months = ['all','april','may','june','july','august','september','october'][0:past_months+1]

        # Show detailed info about each firm: total check-ins, total CO2, Total Calories, monthly changes, new check-ins.
        data = {
            'num_checkins': [],
            'total_C02': [],
            'total_calories': [],
            'percent_participants': [],
            'percent_already_green': [],
            'percent_green_switch': [],
            'percent_healthy_switch': [],
            'percent_avg_participation': []
            }

        for month in months:
            metrics = calculate_metrics(company, month)
            data['num_checkins'].append(
                (month, metrics['num_checkins'])
                )
            data['total_C02'].append(
                (month, metrics['total_C02'])
                )
            data['total_calories'].append(
                (month, metrics['total_calories'])
                )
            data['percent_participants'].append(
                (month, metrics['participants'])
                )
            data['percent_already_green'].append(
                (month, metrics['already_green'])
                )
            data['percent_green_switch'].append(
                (month, metrics['green_switch'])
                )
            data['percent_healthy_switch'].append(
                (month, metrics['healthy_switch'])
                )
            data['percent_avg_participation'].append(
                (month, metrics['avg_participation'])
                )

        return render_to_response('company.html',
            {   'company': company,
                'data': data
            }, context)

def latest_leaderboard(request, size='all', parentid=None, selected_month='all'):
    # Obtain the context from the HTTP request.
    context = RequestContext(request)

    d = {}

    parent = None

    if parentid: # this is a bunch of subteams
        parent = Employer.objects.get(id=parentid)

        teams = Team.objects.only('id','name').filter(parent_id=parentid)

        survey_data = teams

    else: # this is a bunch of companies
        companies = Employer.objects.only('id','name').exclude(id__in=[32,33,34,38,39,40]).filter(active2015=True)

        # Filtering the results by size
        if size == 'small':
            companies = companies.filter(nr_employees__lte=50)
        elif size == 'medium':
            companies = companies.filter(nr_employees__gt=50,nr_employees__lte=300)
        elif size == 'large':
            companies = companies.filter(nr_employees__gt=300,nr_employees__lte=2000)
        elif size == 'largest':
            companies = companies.filter(nr_employees__gt=2000)

        survey_data = companies

    if selected_month != 'all':
        months_dict = { 'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06', 'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12' }
        shortmonth = months_dict[selected_month]
        month_model = Month.objects.filter(wr_day__year='2015', wr_day__month=shortmonth)
        survey_data = survey_data.filter(commutersurvey__wr_day_month=month_model)

    survey_data = survey_data.annotate(
        saved_carbon=Sum('commutersurvey__carbon_savings'),
        overall_calories=Sum('commutersurvey__calories_total'),
        num_checkins=Count('commutersurvey'))

    totals = survey_data.aggregate(
        total_carbon=Sum('saved_carbon'),
        total_calories=Sum('overall_calories'),
        total_checkins=Sum('num_checkins')
    )

    for company in survey_data:
        d[str(company.name)] = calculate_metrics(company, selected_month)

    ranks = calculate_rankings(d)

    return render_to_response('leaderboard/leaderboard_new.html',
        {
            'ranks': ranks,
            'totals': totals,
            'request': request,
            'employersWithSubteams': Employer.objects.filter(team__isnull=False).distinct(),
            'size': size,
            'selected_month': selected_month,
            'parent': parent
        }, context)
