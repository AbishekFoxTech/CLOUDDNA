"""
URL configuration for config project (CloudDNA).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('documents/', include('documents.urls')),
    path('ai/', include('ai_engine.urls')),
    path('relationships/', include('relationships.urls')),
    path('recommendations/', include('recommendations.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'config.views.custom_404_view'
handler500 = 'config.views.custom_500_view'
