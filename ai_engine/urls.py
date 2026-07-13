from django.urls import path

from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('<int:pk>/insights/', views.ai_insights_view, name='insights'),
    path('<int:pk>/retry/', views.retry_processing_view, name='retry'),
]
