#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import connection
from collections import OrderedDict
from django.http import HttpResponse
import dateutil.parser
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import simplejson as json
import csv
from django.shortcuts import render
import os
from django.core.files.storage import FileSystemStorage
import pandas as pd
import datetime
import requests
import xml.etree.ElementTree as ET
import socket
import pandas
from django.conf import settings
import zipfile
import StringIO
import decimal

def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError

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
    return fetchVal[0]


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    fetchval = cursor.fetchone()
    cursor.close()
    return fetchval[0]


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_commit_query_void(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]



def form_config(request,username,id_string):
    id_strings = ['hh_registration']
    csv_url = ""
    if id_string in id_strings:
        csv_url = 'http://' + str(request.META['REMOTE_ADDR']) + ':' + str(request.META['SERVER_PORT']) + '/sajidamodule/'+str(username)+'/create_csv/' + id_string
    data_content = {
        'csv_url': csv_url
    }
    return HttpResponse(json.dumps(data_content))


def create_csv(request, username, id_string):
    filenames = []
    user_path_filename = os.path.join(settings.MEDIA_ROOT, username)
    user_path_filename = os.path.join(user_path_filename, 'formid-media')
    if not os.path.exists(user_path_filename):
        os.makedirs(user_path_filename)
    po_file_name = os.path.join(user_path_filename, 'center.csv')
    filenames.append(po_file_name)
    branch_role = ["Community Organizer", "Psychosocial Educator", "Law Officer"]
    center_role = ["Sajida Bondhu"]

    # check the user role
    check_user_role = "select (select role from usermodule_organizationrole where id = role_id )role_name from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = (select id from auth_user where username ='" + str(username) + "' ))"
    df = pandas.read_sql(check_user_role, connection)
    if df.empty:
        message = "Assaign a role to this user"
        return render(request, 'usermodule/error_404.html', {'message': message})
    role_name = df.role_name.tolist()[0]

    if role_name in branch_role:
        query = "WITH branch AS(SELECT user_id, branch_id, (SELECT region_id FROM branch_list WHERE id = t.branch_id) region_id FROM usermodule_branch t WHERE user_id = (SELECT id FROM auth_user WHERE username = '"+str(username)+"')) SELECT region_id region,(select field_name from geo_data where id = region_id) region_list, branch.branch_id branch,(select branch_name from branch_list where id = branch.branch_id) branch_list, id center,center_name center_list FROM center_list, branch WHERE center_list.branch_id = branch.branch_id"
    elif role_name in center_role:
        query = "WITH center AS(SELECT user_id, center_id, (SELECT branch_id FROM center_list WHERE id = t.center_id) branch_id FROM usermodule_center t WHERE user_id = (SELECT id FROM auth_user WHERE username = '"+str(username)+"')), branch AS (SELECT id branch_id, region_id FROM branch_list WHERE id = ANY (SELECT branch_id FROM center)) SELECT region_id region, (select field_name from geo_data where id = region_id) region_list, branch.branch_id branch, (select branch_name from branch_list where id = branch.branch_id) branch_list, center_id center,(select center_name from center_list where id = center_id) center_list FROM branch, center WHERE branch.branch_id = center.branch_id"
    else:
        query = "with t as( select geo_data.id region_id,field_name,branch_list.id branch_id,branch_name from geo_data,branch_list where geo_data.id = branch_list.region_id) select t.region_id region,t.field_name region_list,t.branch_id branch,branch_name branch_list,center_list.id center,center_name center_list from t,center_list where t.branch_id = center_list.branch_id"

    # query = "select * from usermodule_region where user_id = (select id from auth_user where username = '"+str(username)+"')"
    # df = pandas.read_sql(query, connection)
    # if df.empty:
    #     query = "with t as( select geo_data.id region_id,field_name,branch_list.id branch_id,branch_name from geo_data,branch_list where geo_data.id = branch_list.region_id) select t.region_id region,t.field_name region_list,t.branch_id branch,branch_name branch_list,center_list.id center,center_name center_list from t,center_list where t.branch_id = center_list.branch_id"
    # else:
    #         query = "WITH region AS(SELECT * FROM usermodule_region WHERE user_id = (SELECT id FROM auth_user WHERE username = 'sajida_admin')), branch AS (SELECT user_id,branch_id,(select region_id from branch_list where branch_id = id) parent FROM usermodule_branch WHERE user_id = (SELECT id FROM auth_user WHERE username = 'sajida_admin')), center AS (SELECT *,(select branch_id from center_list where center_id = id) parent FROM usermodule_center WHERE user_id = (SELECT id FROM auth_user WHERE username = 'sajida_admin')), first_join as (select region.user_id,region_id,branch_id from region left join branch on region.region_id = branch.parent) , final_join as ( select (SELECT field_name FROM geo_data WHERE id = region_id) region_list,region_id region,(SELECT branch_name FROM branch_list WHERE id = branch_id) branch_list,branch_id branch,(SELECT center_name FROM center_list WHERE id = center_id) center_list,center_id center from first_join left join center on first_join.branch_id = center.parent) select coalesce(region_list::text,'') region_list,coalesce(region::text,'') region, coalesce(branch_list::text,'') branch_list,coalesce(branch::text,'') branch, coalesce(center_list::text,'') center_list,coalesce(center::text,'') center from final_join"
    df = pandas.read_sql(query,connection)
    df.to_csv(po_file_name,index=False)
    zip_subdir = "itemsetfiles"
    zip_filename = "%s.zip" % zip_subdir
    s = StringIO.StringIO()
    # The zip compressor
    zf = zipfile.ZipFile(s, "w")
    for fpath in filenames:
        # Calculate path for file in zip
        if os.path.exists(fpath):
            fdir, fname = os.path.split(fpath)
            zip_path = os.path.join(zip_subdir, fname)
            # Add file, at correct path
            zf.write(fpath, fname)
    # Must close zip for all contents to be written
    zf.close()
    # Grab ZIP file from in-memory, make response with correct MIME-type
    resp = HttpResponse(s.getvalue(), mimetype="application/x-zip-compressed")
    # ..and correct content-disposition
    resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename
    return resp


def logger_instance_data_hh_registration(request, username):
    query = "SELECT instance_id, date_created::date, user_id, username, region region_code,(SELECT field_name FROM geo_data WHERE id = region :: INT) region_name, branch branch_code, (SELECT branch_name FROM branch_list WHERE id = branch :: INT), center center_code, (SELECT center_name FROM center_list WHERE id = center :: INT), member_no, micro_finance_id, member_id, member_name, membership_start_date, membership_duration_month, duration_day, membership_expire_date, membership_status,COALESCE(birth_date,'') birth_date, age, CASE WHEN occupation :: INT = 1 THEN 'Home Maker' WHEN occupation :: INT = 2 THEN 'Home Assitant' WHEN occupation :: INT = 3 THEN 'Small Business' WHEN occupation :: INT = 4 THEN 'Day Labour' WHEN occupation :: INT = 5 THEN 'Farmer' WHEN occupation :: INT = 6 THEN 'Garments worker' WHEN occupation :: INT = 7 THEN 'Private service holder' WHEN occupation :: INT = 8 THEN 'Govt. service holder' WHEN occupation :: INT = 9 THEN 'Driver' WHEN occupation :: INT = 99 THEN 'Others' END occupation,COALESCE (occupation_other,'') occupation_other, CASE WHEN gender :: INT = 1 THEN 'Male' WHEN gender :: INT = 2 THEN 'Female' END gender, CASE WHEN maritial_status :: INT = 1 THEN 'Married' WHEN maritial_status :: INT = 2 THEN 'Unmarried' WHEN maritial_status :: INT = 3 THEN 'Divorced' WHEN maritial_status :: INT = 4 THEN 'Widowed' END maritial_status, CASE WHEN edu_qualification :: INT = 1 THEN 'Illiterate' WHEN edu_qualification :: INT = 2 THEN 'Read & Write' WHEN edu_qualification :: INT = 3 THEN 'Primary' WHEN edu_qualification :: INT = 4 THEN 'Secondary' WHEN edu_qualification :: INT = 5 THEN 'Higher' END edu_qualification, nid, mobile, division, district,COALESCE(upazila,'') upazila,COALESCE(union_name,'') union_name,COALESCE(village,'') village, COALESCE(house_owner_name,'') house_owner_name,status  FROM hh_registration where username ='"+str(username)+"'"
    data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(data)