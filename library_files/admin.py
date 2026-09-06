from django.contrib import admin
from .models import FileDocument


@admin.register(FileDocument)
class FileDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'file_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'file_type', 'category']
    search_fields = ['title', 'description']
