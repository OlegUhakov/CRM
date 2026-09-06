from django.urls import path
from . import views

app_name = 'library_files'
urlpatterns = [
    path('', views.file_list, name='list'),
    path('upload/', views.file_upload, name='upload'),
    path('<slug:slug>/', views.file_detail, name='detail'),
]
