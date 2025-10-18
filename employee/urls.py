from django.urls import path;
from . import views

app_name = 'employee'

urlpatterns = [
    path('profile/picture/', views.UpdateProfilePictureView.as_view(), name='update_profile_picture')
]
