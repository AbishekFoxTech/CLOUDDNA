from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('favorites/', views.document_favorites, name='favorites'),
    path('search/', views.document_search, name='search'),
    path('upload/', views.document_upload, name='upload'),
    path('<int:pk>/', views.document_detail, name='detail'),
    path('<int:pk>/rename/', views.document_rename, name='rename'),
    path('<int:pk>/delete/', views.document_delete, name='delete'),
    path('<int:pk>/download/', views.document_download, name='download'),
    path('<int:pk>/favorite/', views.document_toggle_favorite, name='toggle_favorite'),
]
