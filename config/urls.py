from django.contrib import admin;
from django.urls import path, include;
from django.conf import settings;

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboards.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
]

# Debug toolbar URLs solo en desarrollo
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__', include(debug_toolbar.urls)),
    ] + urlpatterns