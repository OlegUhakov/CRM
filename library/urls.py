from django.urls import path
from . import views

app_name = 'library'
urlpatterns = [
    path('', views.library_list, name='list'),
    path('dashboard/', views.library_dashboard, name='dashboard'),
    path('create/', views.library_create, name='create'),
    path('import-url/', views.library_import_url, name='import_url'),

    path('gallery/', views.library_gallery, name='gallery'),
    path('files/', views.library_files, name='files'),
    path('uploads/<path:path>', views.library_serve_upload, name='serve_upload'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('categories/<slug:slug>/edit/', views.category_edit, name='category_edit'),
    path('categories/<slug:slug>/delete/', views.category_delete, name='category_delete'),
    path('api/category/create/', views.category_create_api, name='category_create_api'),
    path('api/tag/create/', views.tag_create_api, name='tag_create_api'),
    path('api/upload-image/', views.library_upload_image, name='upload_image'),
    path('api/quick-upload/', views.library_quick_upload, name='quick_upload'),
    path('<slug:slug>/image/<path:image_path>', views.library_serve_image, name='serve_image'),
    path('tags/<slug:slug>/', views.tag_detail, name='tag_detail'),
    path('<slug:slug>/', views.library_detail, name='detail'),
    path('<slug:slug>/edit/', views.library_edit, name='edit'),
    path('<slug:slug>/delete/', views.library_delete, name='delete'),
    path('<slug:slug>/delete-htmx/', views.library_delete_htmx, name='delete_htmx'),
    path('<slug:slug>/favorite/', views.library_toggle_favorite, name='favorite'),
    path('<slug:slug>/upload-attachment/', views.library_upload_attachment, name='upload_attachment'),
    path('<slug:slug>/delete-attachment/<int:att_id>/', views.library_delete_attachment, name='delete_attachment'),
]
