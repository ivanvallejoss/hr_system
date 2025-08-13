from django.urls import path;
from . import views;

app_name = 'dashboards'

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('team-lead/dashboard/', views.team_lead_dashboard, name='team_lead_dashboard'), 
    path('hr/dasboard/', views.hr_dashboard, name='hr_dashboard'),
    path('system/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
