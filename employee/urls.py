from django.urls import path;
from . import views

app_name = 'employee'

urlpatterns = [
    path('profile/picture/', views.UpdateProfilePictureView.as_view(), name='update_profile_picture'),
    path('<int:pk>/salary/update/', views.UpdateEmployeeSalaryView.as_view(), name='update_salary'),
    path('<int:pk>/role/update/', views.UpdateEmployeeRoleView.as_view(), name='update_role'),
]
