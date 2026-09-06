import os
from django.db import models
from slugify import slugify
from core.models import TimeStampedModel, generate_unique_slug
from .storage import LibraryStorage, library_file_upload_to, library_preview_upload_to


class Category(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    color = models.CharField(max_length=7, blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, 'name', Category)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class LibraryItem(TimeStampedModel):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('djvu', 'DJVU'),
        ('docx', 'DOCX'),
        ('txt', 'TXT'),
        ('rtf', 'RTF'),
        ('md', 'MD'),
        ('image', 'Image'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True, help_text='Auto-generated or manual summary')
    source_url = models.URLField(blank=True, null=True, help_text='Original URL if imported')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    tags = models.ManyToManyField(Tag, blank=True, related_name='items')
    file = models.FileField(upload_to=library_file_upload_to, storage=LibraryStorage(), blank=True, null=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, blank=True, null=True)
    preview_image = models.ImageField(upload_to=library_preview_upload_to, storage=LibraryStorage(), blank=True, null=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, 'title', LibraryItem)
        if self.file and not self.file_type:
            self.file_type = self._detect_file_type()
        super().save(*args, **kwargs)

    def _detect_file_type(self):
        ext = self.file.name.split('.')[-1].lower() if '.' in self.file.name else ''
        mapping = {
            'pdf': 'pdf', 'djvu': 'djvu', 'docx': 'docx',
            'txt': 'txt', 'rtf': 'rtf', 'md': 'md',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image',
            'webp': 'image', 'gif': 'image',
        }
        return mapping.get(ext, 'other')

    def save_as_md(self, content, images=None):
        from .utils import save_article_as_md
        md_path, updated_content = save_article_as_md(self, content, images)
        if updated_content and updated_content != content:
            LibraryItem.objects.filter(pk=self.pk).update(content=updated_content)
            self.content = updated_content
        return md_path

    def delete_from_disk(self):
        from .utils import delete_item_from_disk
        delete_item_from_disk(self)


def attachment_upload_to(instance, filename):
    from .utils import get_article_folder_name
    folder = get_article_folder_name(instance.item)
    return '{}/attachments/{}'.format(folder, os.path.basename(filename))


class LibraryAttachment(models.Model):
    item = models.ForeignKey(LibraryItem, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_upload_to, storage=LibraryStorage())
    name = models.CharField(max_length=500, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return self.name or self.file.name

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.file.name.split('/')[-1] if '/' in self.file.name else self.file.name
        super().save(*args, **kwargs)
