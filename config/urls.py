from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('companies/', include('companies.urls')),
    path('contacts/', include('contacts.urls')),
    path('projects/', include('projects.urls')),
    path('tasks/', include('tasks.urls')),
    path('notes/', include('notes.urls')),
    path('materials/', include('materials.urls')),
    path('deals/', include('generator.urls')),
    path('documents/', include('documents.urls')),
    path('parts/', include('parts.urls')),
    path('assistant/', include('assistant.urls')),
    path('calendar/', include('calendar_app.urls')),
    path('library/articles/', include('library_articles.urls')),
    path('library/gallery/', include('library_gallery.urls')),
    path('library/files/', include('library_files.urls')),
    path('library/', include('library.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^files/(?P<path>.*)$', static_serve, {'document_root': settings.DOCUMENTS_ROOT}),
    re_path(r'^ai-files/(?P<path>.*)$', static_serve, {'document_root': settings.AI_FILES_ROOT}),
]
