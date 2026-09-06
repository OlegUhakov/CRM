from django.urls import path
from . import views

app_name = 'library_gallery'
urlpatterns = [
    path('', views.gallery_list, name='list'),
    path('upload/', views.photo_upload, name='upload'),
    path('<slug:slug>/', views.photo_detail, name='detail'),
]
