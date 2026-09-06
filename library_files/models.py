from django.db import models
from django.db.models import Q
from library.models import LibraryItem


class FileDocumentManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(is_active=True, file__isnull=False)
            .exclude(file='')
            .filter(Q(content__isnull=True) | Q(content=''))
        )


class FileDocument(LibraryItem):
    """Proxy for LibraryItem rows that are file-only (no article content)."""

    objects = FileDocumentManager()
    all_objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'File'
        verbose_name_plural = 'Files'
