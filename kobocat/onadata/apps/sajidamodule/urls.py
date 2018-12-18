from django.conf.urls import patterns, include, url
from django.contrib import admin
from onadata.apps.sajidamodule import views , views_api

urlpatterns = patterns('',
url(r'^$', views.index, name='index'),
url(r'^cycle_list/$', views.cycle_list, name='cycle_list'),
url(r'^add_cycle_form/(?P<user_id>\d+)/$', views.add_cycle_form, name='add_cycle_form'),
url(r'^insert_cycle_form/$', views.insert_cycle_form, name='insert_cycle_form'),
url(r'^edit_cycle_form/(?P<id>\d+)/$', views.edit_cycle_form, name='edit_cycle_form'),
url(r'^update_cycle_form/$', views.update_cycle_form, name='update_cycle_form'),
url(r'^hh_target_list/$', views.hh_target_list, name='hh_target_list'),
url(r'^add_hh_target_form/(?P<user_id>\d+)/$', views.add_hh_target_form, name='add_hh_target_form'),
url(r'^insert_hh_target_form/$', views.insert_hh_target_form, name='insert_hh_target_form'),
url(r'^edit_hh_target_form/(?P<id>\d+)/$', views.edit_hh_target_form, name='edit_hh_target_form'),
url(r'^update_hh_target_form/$', views.update_hh_target_form, name='update_hh_target_form'),
url(r'^profile_view/(?P<user_id>\d+)/$', views.profile_view, name='profile_view'),

url(r'^meeting_list/$', views.meeting_list, name='meeting_list'),
url(r'^add_meeting_form/$', views.add_meeting_form, name='add_meeting_form'),
url(r'^insert_meeting_form/$', views.insert_meeting_form, name='insert_meeting_form'),
url(r'^edit_meeting_form/(?P<meeting_id>\d+)/$', views.edit_meeting_form, name='edit_meeting_form'),
url(r'^update_meeting_form/$', views.update_meeting_form, name='update_meeting_form'),
url(r'^delete_meeting_form/(?P<meeting_id>\d+)/$', views.delete_meeting_form, name='delete_meeting_form'),


url(r'^legal_awareness_class_list/$', views.legal_awareness_class_list, name='legal_awareness_class_list'),
url(r'^add_legal_awareness_class/$', views.add_legal_awareness_class, name='add_legal_awareness_class'),
url(r'^edit_legal_awareness_class/(?P<instance_id>\d+)',views.edit_legal_awareness_class),
url(r'^delete_legal_awareness_class/(?P<instance_id>\d+)',views.delete_legal_awareness_class),
url(r'^get_branches/$', views.get_branches, name='get_branches'),
url(r'^submit-xml-data/$', views.submitXMLData),
url(r'^getBranches/$', views.getBranches, name='getBranches'),
url(r'^getAwarenessData/$', views.getAwarenessData, name='getAwarenessData'),

url(r'^add_daily_register_co/$', views.add_daily_register_co, name='add_daily_register_co'),
url(r'^daily_register_co_list/$', views.daily_register_co_list, name='daily_register_co_list'),

url(r'^legal_advice_refer_list/$', views.legal_advice_refer_list, name='legal_advice_refer_list'),
url(r'^legal_advice_form/(?P<member_id>[^/]+)/$', views.legal_advice_form, name='legal_advice_form'),

# api url
url(r'^form_config/(?P<username>[^/]+)/(?P<id_string>[^/]+)/$', views_api.form_config,name='form_config'),
url(r'^(?P<username>[^/]+)/create_csv/(?P<id_string>[^/]+)/$', views_api.create_csv, name='create_csv'),
url(r'^logger_instance_data_hh_registration/(?P<username>[^/]+)/$', views_api.logger_instance_data_hh_registration, name='logger_instance_data_hh_registration'),

    )
