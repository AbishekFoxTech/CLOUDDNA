from django.urls import path

from . import views

app_name = 'relationships'

urlpatterns = [
    path('graph/', views.graph_view, name='graph'),
    path('graph/data/', views.graph_data_api, name='graph_data'),
    path('link/', views.create_manual_link_view, name='create_manual_link'),
    path('<int:pk>/unlink/', views.delete_relationship_view, name='delete_relationship'),
]
