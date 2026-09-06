from django.db import models
from django.db.models import Q
from library.models import LibraryItem


class PhotoManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(is_active=True)
            .filter(Q(content__isnull=True) | Q(content=''))
            .filter(
                Q(file_type='image')
                | Q(attachments__file__icontains='.jpg')
                | Q(attachments__file__icontains='.jpeg')
                | Q(attachments__file__icontains='.png')
                | Q(attachments__file__icontains='.webp')
            )
            .distinct()
        )


class Photo(LibraryItem):
    """Proxy for LibraryItem rows that are images."""

    objects = PhotoManager()
    all_objects = models.Manager()

    class Meta:
        proxy = True
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'
