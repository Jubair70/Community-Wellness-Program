from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count, Q
from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
# from django.utils import simplejson
import json
import logging
import sys
import operator
import pandas
from django.shortcuts import render
import numpy
import time
import datetime
from django.core.files.storage import FileSystemStorage

from django.core.urlresolvers import reverse

from django.db import (IntegrityError, transaction)
from django.db.models import ProtectedError
from django.shortcuts import redirect
from onadata.apps.main.models.user_profile import UserProfile
from onadata.apps.usermodule.forms import UserForm, UserProfileForm, ChangePasswordForm, UserEditForm, OrganizationForm, \
    OrganizationDataAccessForm, ResetPasswordForm
from onadata.apps.usermodule.models import UserModuleProfile, UserPasswordHistory, UserFailedLogin, Organizations, \
    OrganizationDataAccess

from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
# Menu imports
from onadata.apps.usermodule.forms import MenuForm
from onadata.apps.usermodule.models import MenuItem
# Unicef Imports
from onadata.apps.logger.models import Instance, XForm
# Organization Roles Import
from onadata.apps.usermodule.models import OrganizationRole, MenuRoleMap, UserRoleMap
from onadata.apps.usermodule.forms import OrganizationRoleForm, RoleMenuMapForm, UserRoleMapForm, UserRoleMapfForm
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms.formsets import formset_factory

from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from collections import OrderedDict
import os
import decimal
import xml.etree.ElementTree as ET
import requests

def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal


def __db_fetch_single_value(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    cursor.close()
    return fetchVal


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError


@login_required
def index(request):
    id_string = 'add_new_class'
    query = "SELECT id, uuid  FROM logger_xform where id_string = 'add_new_class'"
    queryResult = __db_fetch_single_value(query)
    xform_id = queryResult[0]
    form_uuid = str(queryResult[1])
    username = request.user.username
    return render(request, 'sajidamodule/customer_mangement.html',{'id_string': id_string, 'xform_id': xform_id,
                   'form_uuid': form_uuid, 'username': username
                   })





@login_required
def cycle_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]
    if current_user.status != 'Active':
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})

    user_id = request.user.id

    query = "select * from usermodule_branch where user_id ="+str(user_id)
    df_branch = pandas.DataFrame()
    df_branch = pandas.read_sql(query,connection)

    query = "select * from usermodule_center where user_id =" + str(user_id)
    df_center = pandas.DataFrame()
    df_center = pandas.read_sql(query, connection)

    if not df_center.empty:
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})

    if df_branch.empty:
        query = "WITH user_branch AS(select distinct user_id,(select branch_id from center_list where id = center_id) branch_id from usermodule_center) SELECT id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, (select branch_name from branch_list where id =branch_id)branch_name, Coalesce(start_date :: text, '') start_date, Coalesce(end_date :: text, '') end_date FROM user_branch left join (SELECT * FROM users_cycle_duration WHERE end_date > Now() :: DATE) AS users_cycle_duration ON user_branch.user_id = users_cycle_duration.user_id"

    else:
        query="WITH user_branch AS(select distinct user_id,(select branch_id from center_list where id = center_id) branch_id from usermodule_center where center_id = any( select id from center_list where branch_id = any(select branch_id from usermodule_branch where user_id = "+str(user_id)+"))) SELECT id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, (select branch_name from branch_list where id =branch_id)branch_name, Coalesce(start_date :: text, '') start_date, Coalesce(end_date :: text, '') end_date FROM user_branch left join (SELECT * FROM users_cycle_duration WHERE end_date > Now() :: DATE) AS users_cycle_duration ON user_branch.user_id = users_cycle_duration.user_id"

    cycle_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/cycle_list.html', {
        'cycle_list': cycle_list
    })

    # # current user role
    # query = "select (select role from usermodule_organizationrole where id = role_id)role_name,role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(
    #     request.user.id) + ")"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     message = "Assaign a role to this logged in user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # else:
    #     role_id = df.role_id.tolist()[0]
    #     role_name = df.role_name.tolist()[0]
    #     print(role_name)
    #
    #     permitted_role = ["Community Organizer","Admin"]
    #
    #     # for Community Organizer and Admin users
    #     if role_name =="Community Organizer":
    #         query = "select user_id from usermodule_branch where branch_id in (select branch_id from usermodule_branch where user_id  = " + str(
    #             request.user.id) + ") and user_id != " + str(request.user.id)
    #         df = pandas.DataFrame()
    #         df = pandas.read_sql(query, connection)
    #         users = df.user_id.tolist()
    #         users = str(map(str, users))
    #         users = users.replace('[', '(').replace(']', ')')
    #         # query for only users which has sajida bondhu role and under this CO user
    #         query = "with user_branch as( select user_id,(select branch_name from branch_list where id = branch_id) branch_name from usermodule_branch where user_id in (select (select user_id from usermodule_usermoduleprofile where id = t.user_id and user_id IN " + str(
    #             users) + ") from usermodule_userrolemap t where role_id = 53) )select id,(select username from auth_user where id = user_branch.user_id) username,user_branch.user_id,branch_name,coalesce(start_date::text,'') start_date,coalesce(end_date::text,'') end_date from user_branch left join (select * from users_cycle_duration where end_date > now()::date) as users_cycle_duration on user_branch.user_id = users_cycle_duration.user_id"
    #         cycle_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    #         return render(request, 'sajidamodule/cycle_list.html', {
    #             'cycle_list': cycle_list, 'role_id': role_id
    #         })
    #
    #
    #     else:
    #         role_id = 0
    #
    #         # query for only users which has sajida bondhu role
    #         query = "with user_branch as( select user_id,(select branch_name from branch_list where id = branch_id) branch_name from usermodule_branch where user_id in (select (select user_id from usermodule_usermoduleprofile where id = t.user_id) from usermodule_userrolemap t where role_id = 53) )select id,(select username from auth_user where id = user_branch.user_id) username,user_branch.user_id,branch_name,coalesce(start_date::text,'') start_date,coalesce(end_date::text,'') end_date from user_branch left join (select * from users_cycle_duration where end_date > now()::date) as users_cycle_duration on user_branch.user_id = users_cycle_duration.user_id"
    #         cycle_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    #         return render(request, 'sajidamodule/cycle_list.html', {
    #             'cycle_list': cycle_list, 'role_id': role_id
    #         })


@login_required
def add_cycle_form(request, user_id):
    # current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    # if current_user:
    #     current_user = current_user[0]
    # if current_user.status != 'Active':
    #     message = "You have no access to this page"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    #
    # # current user role
    # query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = "+str(request.user.id)+")"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query,connection)
    # if df.empty:
    #     message = "Assaign a role to this logged in user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # else:
    #     role_id = df.role_id.tolist()[0]
    #
    #     # for Community Organizer users
    #     if role_id == 52:
    #         query = "select user_id,(select username from auth_user where id = user_id) username from usermodule_branch where branch_id in (select branch_id from usermodule_branch where user_id  = " + str(
    #             request.user.id) + ") and user_id != " + str(request.user.id)+" and user_id in (SELECT(SELECT user_id FROM usermodule_usermoduleprofile WHERE id = t.user_id) FROM usermodule_userrolemap t WHERE role_id = 53)"
    #         df = pandas.DataFrame()
    #         df = pandas.read_sql(query, connection)
    #         username = df.user_id.tolist()
    #         user_id = df.username.tolist()
    #         users = zip(user_id,username)
    #     else:
    #         query = "SELECT (SELECT user_id FROM usermodule_usermoduleprofile WHERE id = t.user_id) user_id,(SELECT username FROM usermodule_usermoduleprofile WHERE id = t.user_id) username FROM usermodule_userrolemap t WHERE role_id = 53"
    #         df = pandas.DataFrame()
    #         df = pandas.read_sql(query, connection)
    #         username = df.user_id.tolist()
    #         user_id = df.username.tolist()
    #         users = zip(user_id, username)
    #     return render(request, 'sajidamodule/add_cycle_form.html',
    #                   {'users': users})

    # query for username
    query = "select username from auth_user where id =" + str(user_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    username = df.username.tolist()[0]
    return render(request, 'sajidamodule/add_cycle_form.html', {'username': username})


@login_required
def insert_cycle_form(request):
    if request.POST:
        username = request.POST.get('username')
        start_date = request.POST.get('from_date')
        end_date = request.POST.get('to_date')
        # delete_query = "delete from users_cycle_duration where user_id = (select id from auth_user where username = '"+str(username)+"')"
        # __db_commit_query(delete_query)
        insert_query = "INSERT INTO public.users_cycle_duration (user_id, start_date, end_date) VALUES((select id from auth_user where username = '" + str(
            username) + "'), '" + str(start_date) + "', '" + str(end_date) + "')"
        __db_commit_query(insert_query)
    return HttpResponseRedirect("/sajidamodule/cycle_list/")


@login_required
def edit_cycle_form(request, id):
    query = "select (select username from auth_user where id = user_id) username,start_date,end_date from users_cycle_duration where id = " + str(
        id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    username = df.username.tolist()[0]
    start_date = df.start_date.tolist()[0]
    end_date = df.end_date.tolist()[0]
    return render(request, 'sajidamodule/edit_cycle_form.html',
                  {'username': username, 'start_date': json.dumps(start_date, default=decimal_date_default),
                   'end_date': json.dumps(end_date, default=decimal_date_default), 'id': id})


@login_required
def update_cycle_form(request):
    if request.POST:
        id = request.POST.get('id')
        start_date = request.POST.get('from_date')
        end_date = request.POST.get('to_date')
        update_query = "UPDATE public.users_cycle_duration SET start_date='" + str(start_date) + "', end_date='" + str(
            end_date) + "' where id= " + str(id)
        __db_commit_query(update_query)
    return HttpResponseRedirect("/sajidamodule/cycle_list/")


@login_required
def hh_target_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]
    # check this user is active or not
    if current_user.status != 'Active':
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})

    user_id = request.user.id

    query = "select * from usermodule_branch where user_id =" + str(user_id)
    df_branch = pandas.DataFrame()
    df_branch = pandas.read_sql(query, connection)

    query = "select * from usermodule_center where user_id =" + str(user_id)
    df_center = pandas.DataFrame()
    df_center = pandas.read_sql(query, connection)

    if not df_center.empty:
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})

    if df_branch.empty:
            query = "WITH user_branch AS(SELECT DISTINCT user_id, (SELECT branch_id FROM center_list WHERE id = center_id) branch_id FROM usermodule_center) SELECT id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, (SELECT branch_name FROM branch_list WHERE id = branch_id) branch_name, Coalesce(given_month :: text, '') given_month, Coalesce(given_month_text :: text, '') given_month_text, Coalesce(target_hh :: text, '') target_hh FROM user_branch left join (SELECT * FROM hh_target WHERE extract(month from given_month)::int > extract(month from now())::int) AS hh_target ON user_branch.user_id = hh_target.user_id"

    else:
        query = " WITH user_branch AS(SELECT DISTINCT user_id, (SELECT branch_id FROM center_list WHERE id = center_id) branch_id FROM usermodule_center WHERE center_id = ANY (SELECT id FROM center_list WHERE branch_id = ANY (SELECT branch_id FROM usermodule_branch WHERE user_id = "+str(user_id)+"))) SELECT id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, (SELECT branch_name FROM branch_list WHERE id = branch_id) branch_name, Coalesce(given_month :: text, '') given_month, Coalesce(given_month_text :: text, '') given_month_text, Coalesce(target_hh :: text, '') target_hh FROM user_branch left join (SELECT * FROM hh_target WHERE extract(month from given_month)::int > extract(month from now())::int) AS hh_target ON user_branch.user_id = hh_target.user_id"

    hh_target_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/hh_target_list.html', {
        'hh_target_list': hh_target_list
    })




    # # current user role
    # query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(
    #     request.user.id) + ")"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     message = "Assaign a role to this logged in user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # else:
    #     role_id = df.role_id.tolist()[0]
    #
    #     # for Community Organizer users
    #     if role_id == 52:
    #         query = "select user_id from usermodule_branch where branch_id in (select branch_id from usermodule_branch where user_id  = " + str(
    #             request.user.id) + ") and user_id != " + str(request.user.id)
    #         df = pandas.DataFrame()
    #         df = pandas.read_sql(query, connection)
    #         users = df.user_id.tolist()
    #         users = str(map(str, users))
    #         users = users.replace('[', '(').replace(']', ')')
    #
    #         # query for only users
    #         # which has sajida bondhu role
    #         # and under this CO user
    #         query = "WITH user_branch AS(SELECT user_id, (SELECT branch_name FROM branch_list WHERE id = branch_id) branch_name FROM usermodule_branch WHERE user_id IN (SELECT (SELECT user_id FROM usermodule_usermoduleprofile WHERE id = t.user_id and user_id IN " + str(
    #             users) + ") FROM usermodule_userrolemap t WHERE role_id = 53)) SELECT hh_target.id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, branch_name, Coalesce(start_date :: text, '') start_date, Coalesce(end_date :: text, '') end_date, Coalesce(target_hh :: text, '') target_hh FROM user_branch left join (select * from hh_target where end_date >= now()::date) as hh_target ON user_branch.user_id = hh_target.user_id"
    #         hh_target_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    #         return render(request, 'sajidamodule/hh_target_list.html', {
    #             'hh_target_list': hh_target_list, 'role_id': role_id
    #         })
    #     else:
    #         role_id = 0
    #
    #         # query for only users
    #         # which has sajida bondhu role
    #         query = "WITH user_branch AS(SELECT user_id, (SELECT branch_name FROM branch_list WHERE id = branch_id) branch_name FROM usermodule_branch WHERE user_id IN (SELECT (SELECT user_id FROM usermodule_usermoduleprofile WHERE id = t.user_id) FROM usermodule_userrolemap t WHERE role_id = 53)) SELECT hh_target.id, (SELECT username FROM auth_user WHERE id = user_branch.user_id) username, user_branch.user_id, branch_name, Coalesce(start_date :: text, '') start_date, Coalesce(end_date :: text, '') end_date, Coalesce(target_hh :: text, '') target_hh FROM user_branch left join (select * from hh_target where end_date >= now()::date) as hh_target ON user_branch.user_id = hh_target.user_id"
    #     hh_target_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    #     return render(request, 'sajidamodule/hh_target_list.html', {
    #         'hh_target_list': hh_target_list, 'role_id': role_id
    #     })


@login_required
def add_hh_target_form(request, user_id):
    # query for username
    query = "select username from auth_user where id =" + str(user_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    username = df.username.tolist()[0]

    # query for getting cycle duration date for this user_id
    # for giving targeting user must give with in start and end date of cycle
    # query = "select start_date,end_date from users_cycle_duration where user_id = " + str(
    #     user_id) + " and end_date >= now()::date"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     message = "Set Cycle Duration for this user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # min_date = df.start_date.tolist()[0]
    # max_date = df.end_date.tolist()[0]
    return render(request, 'sajidamodule/add_hh_target_form.html',
                  {'username': username
                   #    , 'min_date': json.dumps(min_date, default=decimal_date_default),
                   # 'max_date': json.dumps(max_date, default=decimal_date_default)
                   })


@login_required
def insert_hh_target_form(request):
    if request.POST:
        username = request.POST.get('username')
        given_month = request.POST.get('given_month')
        given_month_text = request.POST.get('given_month_text')
        target_hh = request.POST.get('target_hh')
        print(username)
        print(given_month)
        print(target_hh)
        print(given_month_text)

        # delete_query = "delete from hh_target where user_id = (select id from auth_user where username = '"+str(username)+"')"
        # __db_commit_query(delete_query)
        insert_query = "INSERT INTO public.hh_target (user_id, given_month, given_month_text,target_hh) VALUES((select id from auth_user where username = '" + str(
            username) + "'), '" + str(given_month) + "', '" + str(given_month_text) + "'," + str(target_hh) + ")"
        __db_commit_query(insert_query)
    return HttpResponseRedirect("/sajidamodule/hh_target_list/")


@login_required
def edit_hh_target_form(request, id):
    query = "select user_id,(select username from auth_user where id = user_id) username,given_month,given_month_text,target_hh from hh_target where id = " + str(
        id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    username = df.username.tolist()[0]
    user_id = df.user_id.tolist()[0]
    given_month = df.given_month.tolist()[0]
    given_month_text = df.given_month_text.tolist()[0]
    target_hh = df.target_hh.tolist()[0]

    # query for getting cycle duration date for this user_id
    # for giving targeting user must give with in start and end date of cycle
    # query = "select start_date,end_date from users_cycle_duration where user_id = " + str(
    #     user_id) + " and end_date >= now()::date"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     message = "Set Cycle Duration for this user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # min_date = df.start_date.tolist()[0]
    # max_date = df.end_date.tolist()[0]
    return render(request, 'sajidamodule/edit_hh_target_form.html',
                  {'username': username, 'given_month': json.dumps(given_month, default=decimal_date_default),
                   'given_month_text': json.dumps(given_month_text, default=decimal_date_default), 'target_hh': target_hh, 'id': id,
                   # 'min_date': json.dumps(min_date, default=decimal_date_default),
                   # 'max_date': json.dumps(max_date, default=decimal_date_default)
                   })


@login_required
def update_hh_target_form(request):
    if request.POST:
        id = request.POST.get('id')
        given_month = request.POST.get('given_month')
        given_month_text = request.POST.get('given_month_text')
        target_hh = request.POST.get('target_hh')
        update_query = "UPDATE public.hh_target SET given_month='" + str(given_month) + "', given_month_text='" + str(
            given_month_text) + "',target_hh=" + str(target_hh) + " where id= " + str(id)
        __db_commit_query(update_query)
    return HttpResponseRedirect("/sajidamodule/hh_target_list/")


@login_required
def profile_view(request, user_id):
    # User Details Information Query
    query = "select first_name || ' ' || last_name fullname,email,(select contact_number from usermodule_usermoduleprofile where user_id = t.id),(select (select branch_name from branch_list where id = branch_id) from usermodule_branch where user_id = t.id),(select(select field_name from geo_data where id = (select region_id from branch_list where id = branch_id)) from usermodule_branch where user_id = t.id) region_name from auth_user t where t.id =" + str(
        user_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    fullname = df.fullname.tolist()[0]
    email = df.email.tolist()[0]
    contact_number = df.contact_number.tolist()[0]
    region_name = df.region_name.tolist()[0]
    branch_name = df.branch_name.tolist()[0]

    # Cycle List
    # query = "select start_date,end_date,(select count(*) total_hh from hh_registration where user_id = users_cycle_duration.user_id ) from users_cycle_duration where user_id = " + str(user_id)
    query = "WITH t AS(SELECT user_id, Count(*) total_hh FROM hh_registration WHERE user_id = "+str(user_id)+" GROUP BY user_id), t1 AS (SELECT users_cycle_duration.user_id, start_date, end_date, Coalesce(total_hh :: text, '0') total_hh FROM users_cycle_duration left join t ON users_cycle_duration.user_id = t.user_id), t2 AS (SELECT user_id, \"date\", Count(*) visited_hh FROM daily_activities WHERE user_id = "+str(user_id)+" GROUP BY user_id, \"date\") SELECT start_date, end_date, total_hh, Coalesce(visited_hh :: text, '0')visited_hh FROM t1 left join t2 ON t2.user_id = t1.user_id AND \"date\" :: DATE BETWEEN t1.start_date AND t1.end_date"
    print(query)
    cycle_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)

    # Target List
    # query = "select given_month_text given_month_text,target_hh from hh_target where user_id =" + str(user_id)

    query = "WITH t AS(SELECT user_id, given_month, given_month_text given_month_text, target_hh FROM hh_target WHERE user_id = "+str(user_id)+"), t1 AS (SELECT user_id, \"date\", Count(*) visited_hh FROM daily_activities WHERE user_id = "+str(user_id)+" GROUP BY user_id, \"date\") SELECT given_month_text, target_hh, Coalesce(visited_hh, '0') visited_hh FROM t left join t1 ON t1.user_id = t.user_id AND Extract(month FROM \"date\" :: DATE) :: INT = Extract(month FROM given_month) :: INT"
    target_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/profile_view.html', {'fullname': fullname,
                                                              'email': email
        , 'contact_number': contact_number
        , 'region_name': region_name
        , 'branch_name': branch_name
        , 'cycle_list': cycle_list
        , 'target_list': target_list})


@login_required
def meeting_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]
    # check this user is active or not
    if current_user.status != 'Active':
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})

    # # current user role
    # query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(
    #     request.user.id) + ")"
    # df = pandas.DataFrame()
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     message = "Assaign a role to this logged in user"
    #     return render(request, 'sajidamodule/error_404.html', {'message': message})
    # else:
    #     role_id = df.role_id.tolist()[0]

    query = "select id,meeting_date,organization_name,topic from external_meeting_register"
    meeting_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/meeting_list.html', {
        'meeting_list': meeting_list
    })


@login_required
def add_meeting_form(request):
    return render(request, 'sajidamodule/add_meeting_form.html')


@login_required
def insert_meeting_form(request):
    if request.POST:
        meeting_date = request.POST.get('meeting_date')
        organization_name = request.POST.get('organization_name')
        topic = request.POST.get('topic')
        insert_query = "INSERT INTO public.external_meeting_register (meeting_date, organization_name, topic) VALUES('" + str(
            meeting_date) + "', '" + str(organization_name) + "', '" + str(topic) + "')"
        __db_commit_query(insert_query)
    return HttpResponseRedirect("/sajidamodule/meeting_list/")


@login_required
def edit_meeting_form(request, meeting_id):
    query = "select meeting_date,organization_name,topic from external_meeting_register where id=" + str(meeting_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    meeting_date = df.meeting_date.tolist()[0]
    organization_name = df.organization_name.tolist()[0]
    topic = df.topic.tolist()[0]
    return render(request, 'sajidamodule/edit_meeting_form.html',
                  {'meeting_date': json.dumps(meeting_date, default=decimal_date_default),
                   'organization_name': organization_name, 'topic': topic, 'meeting_id': meeting_id})


@login_required
def update_meeting_form(request):
    if request.POST:
        meeting_id = request.POST.get('meeting_id')
        meeting_date = request.POST.get('meeting_date')
        organization_name = request.POST.get('organization_name')
        topic = request.POST.get('topic')
        update_query = "UPDATE external_meeting_register SET meeting_date='" + str(
            meeting_date) + "', organization_name='" + str(organization_name) + "', topic='" + str(
            topic) + "' WHERE id=" + str(meeting_id)
        __db_commit_query(update_query)
    return HttpResponseRedirect("/sajidamodule/meeting_list/")


@login_required
def delete_meeting_form(request, meeting_id):
    delete_query = "delete from external_meeting_register where id = " + str(meeting_id) + ""
    __db_commit_query(delete_query)
    return HttpResponseRedirect("/sajidamodule/meeting_list/")


@login_required
def legal_awareness_class_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    user_id = request.user.id

    query = "select * from usermodule_branch where user_id =" + str(user_id)
    df_branch = pandas.DataFrame()
    df_branch = pandas.read_sql(query, connection)

    query = "select * from usermodule_center where user_id =" + str(user_id)
    df_center = pandas.DataFrame()
    df_center = pandas.read_sql(query, connection)

    # check this user is active or not
    if current_user.status != 'Active' or not df_center.empty:
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})


    status = 0
    if df_branch.empty:
        status = 1
        query = "with t as( select id,json->>'_submitted_by' username,json->>'branch' branch,json->>'participant_number' participant_number,json->>'class_end_date' class_end_date, json->>'class_start_date' class_start_date , json->>'organizer' organizer from logger_instance where xform_id = (select id from logger_xform where id_string='add_new_class') and deleted_at is null)select id,(select branch_name from branch_list where branch_code = branch)branch_name,class_start_date, class_end_date,participant_number,case when organizer = '1' then 'BLAST' when organizer = '2' then 'BRAC' when organizer = '3' then 'Community Organizer' when organizer = '4' then 'Law Officer' when organizer = '99' then 'Others' end organizer from t"
    else:
        status = 0
        query = "with t as( select id,json->>'_submitted_by' username,json->>'branch' branch,json->>'participant_number' participant_number,json->>'class_end_date' class_end_date, json->>'class_start_date' class_start_date , json->>'organizer' organizer from logger_instance where xform_id = (select id from logger_xform where id_string='add_new_class') and deleted_at is null)select id,(select branch_name from branch_list where branch_code = branch)branch_name,class_start_date, class_end_date,participant_number,case when organizer = '1' then 'BLAST' when organizer = '2' then 'BRAC' when organizer = '3' then 'Community Organizer' when organizer = '4' then 'Law Officer' when organizer = '99' then 'Others' end organizer from t where username ='"+str(current_user)+"'"
    legal_awareness_class_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/legal_awareness_class_list.html', {
        'legal_awareness_class_list': legal_awareness_class_list,'status':status
    })


@login_required
def add_legal_awareness_class(request):
    id_string = 'add_new_class'
    query = "SELECT id, uuid  FROM logger_xform where id_string = 'add_new_class'"
    queryResult = __db_fetch_single_value(query)
    xform_id = queryResult[0]
    form_uuid = str(queryResult[1])
    username = request.user.username
    return render(request, 'sajidamodule/add_legal_awareness_class.html',{'id_string': id_string, 'xform_id': xform_id,
                   'form_uuid': form_uuid, 'username': username
                   })


@csrf_exempt
def submitXMLData(request):
    jsondata = json.loads(request.body)
    xml_data = jsondata.get("xml_submission_file")
    tree = ET.XML(xml_data)

    file_path = "onadata/media/" + request.user.username + "/xml/"
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open("onadata/media/" + request.user.username + "/xml/submit_data.xml", "w+") as f:
        f.write(ET.tostring(tree))

    files = {'xml_submission_file': open(str(f.name), 'rb')}
    requests.post('http://' + request.META.get('HTTP_HOST') + '/' + request.user.username + '/submission', files=files)
    return HttpResponse("success!")


# for edit KMP Content
def edit_legal_awareness_class(request, instance_id):
    id_string = 'add_new_class'
    xform_id = __db_fetch_single_value("select id from logger_xform where id_string ='" + str(id_string) + "'")[0]
    form_uuid = __db_fetch_single_value("select uuid from logger_xform where id = " + str(xform_id))[0]
    xml_data = __db_fetch_single_value("select xml from logger_instance where id = " + str(instance_id))[0]
    xml_data = str(xml_data).replace('\t', '').replace('\n', '').replace("'","\\'")
    username = request.user.username
    return render(request, "sajidamodule/add_legal_awareness_class.html",
                  {'id_string': id_string, 'xform_id': xform_id, 'username': username,
                   'form_uuid': form_uuid, 'xml_data': xml_data, 'instance_id': instance_id})


def delete_legal_awareness_class(request,instance_id):
    id_string = 'add_new_class'
    queryDelete = "UPDATE public.logger_instance SET deleted_at= current_timestamp  WHERE id = "+str(instance_id)+"  and xform_id = (select id FROM public.logger_xform where id_string = '" +str(id_string)+"' )"
    __db_commit_query(queryDelete)
    return HttpResponseRedirect("/sajidamodule/legal_awareness_class_list/")

@csrf_exempt
def get_branches(request):
    branch_data = []
    reqBody = json.loads(request.body)
    region = reqBody.get('search_key')
    if region is not None:
        branch_query = "select branch_name,branch_code from branch_list where region_id = (select id from geo_data where geocode = '"+str(region)+"')"
        branch_data = json.dumps(__db_fetch_values_dict(branch_query))
    return HttpResponse(branch_data)


def getBranches(request):
    region_code = request.POST.get('region')
    query = "select branch_code,branch_name from branch_list where substring(branch_code from 1 for 2) = '"+str(region_code)+"'"
    region_data = json.dumps(__db_fetch_values_dict(query))
    return HttpResponse(region_data)



def getAwarenessData(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]
    from_date = request.POST.get('from_date')
    to_date = request.POST.get('to_date')
    region = request.POST.get('region')
    branch = request.POST.get('branch')
    organizer = request.POST.get('organizer')
    status = request.POST.get('status')
    filter_query = "where  class_start_date >= '" + str(from_date) + "'"
    # if region != "":
    #     filter_query += " and region = '" + str(region)+"'"
    if branch != "":
        filter_query += " and branch = '" + str(branch)+"'"
    if organizer != "":
        filter_query += " and organizer = '" + str(organizer)+"'"

    if status:
        query = "with t as( select id,json->>'_submitted_by' username,json->>'branch' branch,json->>'participant_number' participant_number,json->>'class_end_date' class_end_date, json->>'class_start_date' class_start_date , json->>'organizer' organizer from logger_instance where xform_id = (select id from logger_xform where id_string='add_new_class') and deleted_at is null)select id,(select branch_name from branch_list where branch_code = branch)branch_name,class_start_date, class_end_date,participant_number,case when organizer = '1' then 'BLAST' when organizer = '2' then 'BRAC' when organizer = '3' then 'Community Organizer' when organizer = '4' then 'Law Officer' when organizer = '99' then 'Others' end organizer from t "+str(filter_query)
    else:
        filter_query += "and username ='"+str(current_user)+"'"
        query = "with t as( select id,json->>'_submitted_by' username,json->>'branch' branch,json->>'participant_number' participant_number,json->>'class_end_date' class_end_date, json->>'class_start_date' class_start_date , json->>'organizer' organizer from logger_instance where xform_id = (select id from logger_xform where id_string='add_new_class') and deleted_at is null)select id,(select branch_name from branch_list where branch_code = branch)branch_name,class_start_date, class_end_date,participant_number,case when organizer = '1' then 'BLAST' when organizer = '2' then 'BRAC' when organizer = '3' then 'Community Organizer' when organizer = '4' then 'Law Officer' when organizer = '99' then 'Others' end organizer from t "+str(filter_query)


    list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(list)


@login_required
def add_daily_register_co(request):
    id_string = 'daily_register_co'
    query = "SELECT id, uuid  FROM logger_xform where id_string = 'daily_register_co'"
    queryResult = __db_fetch_single_value(query)
    xform_id = queryResult[0]
    form_uuid = str(queryResult[1])
    username = request.user.username

    user_id = request.user.id

    query = "select distinct user_id,(select username from auth_user where id = user_id) from usermodule_center where center_id in (select id from center_list where branch_id in (select branch_id from usermodule_branch where user_id = "+str(user_id)+"))"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    if df.empty:
        query = "select distinct user_id,(select username from auth_user where id =user_id) from usermodule_center"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
    user_id = df.user_id.tolist()
    username = df.username.tolist()
    users = zip(user_id,username)

    user_id = request.user.id
    query = "select (select branch_code from branch_list where id = branch_id),(select branch_name from branch_list where id = branch_id) from usermodule_branch where user_id = "+str(user_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    if df.empty:
        query = "select branch_code,branch_name from branch_list"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
    branch_code = df.branch_code.tolist()
    branch_name = df.branch_name.tolist()
    branches = zip(branch_code, branch_name)
    return render(request, 'sajidamodule/add_daily_register_co.html',{'id_string': id_string, 'xform_id': xform_id,
                   'form_uuid': form_uuid, 'username': username,'users':users,'branches':branches })


@login_required
def daily_register_co_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    user_id = request.user.id

    query = "select * from usermodule_branch where user_id =" + str(user_id)
    df_branch = pandas.DataFrame()
    df_branch = pandas.read_sql(query, connection)

    query = "select * from usermodule_center where user_id =" + str(user_id)
    df_center = pandas.DataFrame()
    df_center = pandas.read_sql(query, connection)

    # check this user is active or not
    if current_user.status != 'Active' or not df_center.empty:
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})


    status = 0
    if df_branch.empty:
        status = 1
        query = "WITH t AS(SELECT id, json ->> '_submitted_by' username, json ->> 'branch_name' branch, json ->> 'sb_name' sb_name, json ->> 'date' submitted_date, json_array_elements((json->>'visit')::json) json FROM logger_instance WHERE xform_id = (SELECT id FROM logger_xform WHERE id_string = 'daily_register_co') AND deleted_at IS NULL) SELECT id, (SELECT branch_name FROM branch_list WHERE branch_code = branch)branch_name, case when json->>'visit/properly_visited' = '0' then 'No' when json->>'visit/properly_visited' = '1' then 'Yes' end properly_visited, case when json->>'visit/form_name' = '1' then 'Daily Activities' when json->>'visit/form_name' = '2' then '0-5 years Child Health' when json->>'visit/form_name' = '3' then 'Hospital Referral Properly done' when json->>'visit/form_name' = '4' then 'Lactational Women' when json->>'visit/form_name' = '5' then 'NCD Patient' when json->>'visit/form_name' = '6' then 'Pregnant Women' end form_name, json->>'visit/member_id' member_id,sb_name FROM t"
    else:
        status = 0
        query = "WITH t AS(SELECT id, json ->> '_submitted_by' username, json ->> 'branch_name' branch, json ->> 'sb_name' sb_name, json ->> 'date' submitted_date, json_array_elements((json->>'visit')::json) json FROM logger_instance WHERE xform_id = (SELECT id FROM logger_xform WHERE id_string = 'daily_register_co') AND deleted_at IS NULL) SELECT id, (SELECT branch_name FROM branch_list WHERE branch_code = branch)branch_name, case when json->>'visit/properly_visited' = '0' then 'No' when json->>'visit/properly_visited' = '1' then 'Yes' end properly_visited, case when json->>'visit/form_name' = '1' then 'Daily Activities' when json->>'visit/form_name' = '2' then '0-5 years Child Health' when json->>'visit/form_name' = '3' then 'Hospital Referral Properly done' when json->>'visit/form_name' = '4' then 'Lactational Women' when json->>'visit/form_name' = '5' then 'NCD Patient' when json->>'visit/form_name' = '6' then 'Pregnant Women' end form_name, json->>'visit/member_id' member_id,sb_name FROM t where username ='"+str(current_user)+"'"
    daily_register_co_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/daily_register_co_list.html', {
        'daily_register_co_list': daily_register_co_list,'status':status
    })



@login_required
def legal_advice_refer_list(request):
    current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
    if current_user:
        current_user = current_user[0]

    user_id = request.user.id

    query = "select * from usermodule_branch where user_id =" + str(user_id)
    df_branch = pandas.DataFrame()
    df_branch = pandas.read_sql(query, connection)

    query = "select * from usermodule_center where user_id =" + str(user_id)
    df_center = pandas.DataFrame()
    df_center = pandas.read_sql(query, connection)

    # check this user is active or not
    if current_user.status != 'Active' or not df_center.empty:
        message = "You have no access to this page"
        return render(request, 'sajidamodule/error_404.html', {'message': message})



    if df_branch.empty:
        query = "with t as( select member_id,age from hh_registration union select member_id,age from add_member)select t.member_id,member_name,(select center_name from center_list where center_code::bigint = center::bigint) center,age from refer_confirmation inner join t on t.member_id::bigint = refer_confirmation.member_id::bigint where legal_refer = '1' and legal_status = 0"
    else:
        query = "with t as( select member_id,age from hh_registration union select member_id,age from add_member)select t.member_id,member_name,(select center_name from center_list where center_code::bigint = center::bigint) center,age from refer_confirmation inner join t on t.member_id::bigint = refer_confirmation.member_id::bigint where legal_refer = '1' and legal_status = 0 and center::bigint in (select center_code::bigint from center_list where branch_id in (select branch_id from usermodule_branch where user_id = "+str(user_id)+"))"
    legal_advice_refer_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'sajidamodule/legal_advice_refer_list.html', {
        'legal_advice_refer_list': legal_advice_refer_list
    })


def legal_advice_form(request,member_id):
    return render(request, 'sajidamodule/legal_advice_form.html',{'member_id',member_id})