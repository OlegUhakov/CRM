from django.db import models
from library.models import LibraryItem


class ArticleManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        return qs.exclude(content__isnull=True).exclude(content='')


class Article(LibraryItem):
    """Proxy for LibraryItem rows that are articles (have text content)."""
    objects = ArticleManager()
    all_objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
