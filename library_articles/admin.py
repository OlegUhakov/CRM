from django.contrib import admin
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'file_type', 'is_favorite', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_favorite', 'file_type', 'category']
    search_fields = ['title', 'description', 'content']
