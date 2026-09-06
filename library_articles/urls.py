from django.urls import path
from . import views

app_name = 'library_articles'
urlpatterns = [
    path('', views.article_list, name='list'),
    path('create/', views.article_create, name='create'),
    path('import-url/', views.article_import_url, name='import_url'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('categories/<slug:slug>/edit/', views.category_edit, name='category_edit'),
    path('categories/<slug:slug>/delete/', views.category_delete, name='category_delete'),
    path('tags/<slug:slug>/', views.tag_detail, name='tag_detail'),
    path('api/upload-image/', views.article_upload_image, name='upload_image'),
    path('api/quick-upload/', views.quick_upload, name='quick_upload'),
    path('api/category/create/', views.category_create_api, name='category_create_api'),
    path('api/tag/create/', views.tag_create_api, name='tag_create_api'),
    path('<slug:slug>/image/<path:image_path>', views.article_serve_image, name='serve_image'),
    path('<slug:slug>/', views.article_detail, name='detail'),
    path('<slug:slug>/edit/', views.article_edit, name='edit'),
    path('<slug:slug>/delete/', views.article_delete, name='delete'),
    path('<slug:slug>/delete-htmx/', views.article_delete_htmx, name='delete_htmx'),
    path('<slug:slug>/favorite/', views.article_toggle_favorite, name='favorite'),
    path('<slug:slug>/upload-attachment/', views.article_upload_attachment, name='upload_attachment'),
    path('<slug:slug>/delete-attachment/<int:att_id>/', views.article_delete_attachment, name='delete_attachment'),
]
