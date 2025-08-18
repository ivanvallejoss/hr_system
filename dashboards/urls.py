from django.urls import path;
from . import views;

app_name = 'dashboards'

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('employee/dashboard/', views.EmployeeDashboardView.as_view(), name='employee_dashboard'),
    path('team-lead/dashboard/', views.TeamLeadDashboardView.as_view(), name='team_lead_dashboard'), 
    path('hr/dashboard/', views.HRDashboardView.as_view(), name='hr_dashboard'),
    path('system/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
