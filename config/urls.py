from django.contrib import admin;
from django.urls import path, include;
from django.conf import settings;

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboards.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
]

# EN CASO DE ESTAR EN DESARROLLO:
# 1- Agregamos Debug toolbar URLs.
# 2- Agregamos MEDIA en local storage
if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static

    urlpatterns.insert(0, path('__debug__/', include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)