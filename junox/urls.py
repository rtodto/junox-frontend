from django.urls import path
from . import views

app_name = 'junox'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login_junox/', views.login_junox, name='login_junox'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('check_session/', views.check_session, name='check_session'),
    path('device_detail/<int:device_id>/<str:hostname>/', views.device_detail_view, name='device_detail'),
    path('device_dashboard/', views.device_dashboard_view, name='device_dashboard'),
    path('add_device/', views.add_device_view, name='add_device'),
    path('jobs_list/', views.jobs_list_view, name='jobs_list'),
    path('assign_vlan/', views.assign_vlan_view, name='assign_vlan'),
    path('vlan_catalog/', views.vlan_catalog_view, name='vlan_catalog'),
]