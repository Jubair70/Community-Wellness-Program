import pytz
import sys
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.models import User

from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType

from onadata.apps.api.tools import get_media_file_response
from onadata.apps.logger.models.xform import XForm

from onadata.libs.utils.logger_tools import get_xform_list

from onadata.apps.main.models.meta_data import MetaData
from onadata.apps.main.models.user_profile import UserProfile
from onadata.libs import filters
from onadata.libs.authentication import DigestAuthentication
from onadata.libs.renderers.renderers import MediaFileContentNegotiation
from onadata.libs.renderers.renderers import XFormListRenderer
from onadata.libs.renderers.renderers import XFormManifestRenderer
from onadata.libs.serializers.xform_serializer import XFormListSerializer
from onadata.libs.serializers.xform_serializer import XFormManifestSerializer
from onadata.apps.usermodule.models import UserModuleProfile
from onadata.apps.scheduling.models.geo_location_psu import GeoPsu
from django.core import serializers
from django.http import HttpResponse
import json
from collections import OrderedDict
from django.db import connection
import pandas

# 10,000,000 bytes
DEFAULT_CONTENT_LENGTH = getattr(settings, 'DEFAULT_CONTENT_LENGTH', 10000000)


class XFormListApi(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (DigestAuthentication,)
    content_negotiation_class = MediaFileContentNegotiation
    filter_backends = (filters.XFormListObjectPermissionFilter,)
    queryset = XForm.objects.filter(downloadable=True)
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (XFormListRenderer,)
    serializer_class = XFormListSerializer
    template_name = 'api/xformsList.xml'

    def __db_fetch_values_dict(self,query):
        cursor = connection.cursor()
        cursor.execute(query)
        fetchVal = self.dictfetchall(cursor)
        cursor.close()
        return fetchVal

    def dictfetchall(self,cursor):
        desc = cursor.description
        return [
            OrderedDict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()]

    def get_openrosa_headers(self):
        tz = pytz.timezone(settings.TIME_ZONE)
        dt = datetime.now(tz).strftime('%a, %d %b %Y %H:%M:%S %Z')

        return {
            'Date': dt,
            'X-OpenRosa-Version': '1.0',
            'X-OpenRosa-Accept-Content-Length': DEFAULT_CONTENT_LENGTH
        }

    def mobile_login(self, request, *args, **kwargs):
        username = self.kwargs.get('username')
        #username = request.GET.get('username', '')
        password = request.GET.get('password', '')

        users = authenticate(username=username, password=password)
        if users is not None:
            return HttpResponse(json.dumps(self.mobile_login_response(username, password)),
                                content_type="application/json", status=200)
        else:
            return Response(password, headers=self.get_openrosa_headers(), status=401)
    def mobile_login_response(self, username, password):
        region = []
        branch = []

        region_query = "select region_id,(select field_name from geo_data where id = region_id ) region_name from usermodule_region where user_id = (select id from auth_user where username = '"+str(username)+"')"
        region = self.__db_fetch_values_dict(region_query)
        if len(region) == 0:
            region_query = "select id region_id,field_name region_name from geo_data"
            region = self.__db_fetch_values_dict(region_query)
            branch_query = "select id branch_id, branch_name from branch_list"
            branch = self.__db_fetch_values_dict(branch_query)
        else:
            branch_query = "select branch_id,(select branch_name from branch_list where id = branch_id ) branch_name from usermodule_branch where user_id = (select id from auth_user where username = '"+str(username)+"')"
            branch = self.__db_fetch_values_dict(branch_query)

        cycle_query = "select start_date|| ' --- ' || end_date cycle_duration from users_cycle_duration where end_date > now()::date and user_id = (select id from auth_user where username= '"+str(username)+"') order by id desc limit 1"
        target_query = "select target_hh target from hh_target WHERE  extract(month from given_month)::int > extract(month from now())::int and user_id = (select id from auth_user where username= '"+str(username)+"') order by id desc limit 1"

        cycle_duration = None
        target = None

        df_cycle = pandas.read_sql(cycle_query,connection)
        if not df_cycle.empty:
            cycle_duration = df_cycle.cycle_duration.tolist()[0]
        df_target = pandas.read_sql(target_query, connection)
        if not df_target.empty:
            target = df_target.target.tolist()[0]



        return {
            'username': username,
            'password': password,
            'role': 'Enumerator',
            'region':region,
            'branch':branch,
            'cycle_duration':cycle_duration,
            'target':target
        }


    def get_renderers(self):
        if self.action and self.action == 'manifest':
            return [XFormManifestRenderer()]

        return super(XFormListApi, self).get_renderers()

    def filter_queryset(self, queryset):
        username = self.kwargs.get('username')
        formlist_user = get_object_or_404(User, username=username)
        content_user = get_object_or_404(User, username=username)
        print "hello"
        if username is None and self.request.user.is_anonymous():
            # raises a permission denied exception, forces authentication
            
            self.permission_denied(self.request)

        if username is not None:
            #print "here"
            profile = get_object_or_404(
                UserProfile, user__username=username.lower())
            print profile
            if profile.require_auth and self.request.user.is_anonymous():
                # raises a permission denied exception, forces authentication
                self.permission_denied(self.request)
            else:
                xfct = ContentType.objects.get(app_label='logger', model='xform')
                xfs = content_user.userobjectpermission_set.filter(content_type=xfct)
                shared_forms_pks = list(set([xf.object_pk for xf in xfs]))
                queryset = get_xform_list(username)
                #queryset =  XForm.objects.filter(pk__in=shared_forms_pks).select_related('user')  
                #print queryset
                #print xforms              
                #queryset = queryset.filter(user=profile.user)

        if not self.request.user.is_anonymous():
            queryset = super(XFormListApi, self).filter_queryset(queryset)
        
        return queryset

    def list(self, request, *args, **kwargs):
        self.object_list = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(self.object_list, many=True)

        return Response(serializer.data, headers=self.get_openrosa_headers())

    def retrieve(self, request, *args, **kwargs):
        self.object = self.get_object()

        return Response(self.object.xml, headers=self.get_openrosa_headers())

    @action(methods=['GET'])
    def manifest(self, request, *args, **kwargs):
        self.object = self.get_object()
        object_list = MetaData.objects.filter(data_type='media',
                                              xform=self.object)
        context = self.get_serializer_context()
        serializer = XFormManifestSerializer(object_list, many=True,
                                             context=context)

        return Response(serializer.data, headers=self.get_openrosa_headers())

    @action(methods=['GET'])
    def media(self, request, *args, **kwargs):
        self.object = self.get_object()
        pk = kwargs.get('metadata')

        if not pk:
            raise Http404()

        meta_obj = get_object_or_404(
            MetaData, data_type='media', xform=self.object, pk=pk)

        return get_media_file_response(meta_obj)
