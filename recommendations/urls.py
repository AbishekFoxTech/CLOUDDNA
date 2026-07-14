from django.urls import path

from . import views

app_name = 'recommendations'

urlpatterns = [
    path('', views.recommendations_view, name='home'),
    path('<int:pk>/click/', views.recommendation_click_view, name='click'),
    path('activity/', views.activity_log_view, name='activity_log'),
    path('notifications/', views.notifications_list_api, name='notifications_api'),
    path('notifications/<int:pk>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
]
