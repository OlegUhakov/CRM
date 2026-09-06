import os

from django.core.files.storage import FileSystemStorage

# Extensions treated as gallery images (kept in sync with
# LibraryItem._detect_file_type in models.py).
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def get_library_storage():
    """Callable used by migrations-friendly storage references."""
    return LibraryStorage()


class LibraryStorage(FileSystemStorage):
    """File storage rooted at the library folder from settings.

    Location is resolved dynamically via ``library.utils.get_library_root``
    (AppSettings ``storage.project_path`` or ``MEDIA_ROOT/library``),
    so uploads land next to the article folders instead of ``MEDIA_ROOT``.
    Files are served through the ``library:serve_upload`` view.
    """

    def _get_location(self):
        from .utils import get_library_root

        root = get_library_root()
        os.makedirs(root, exist_ok=True)
        return root

    def path(self, name):
        return os.path.join(self._get_location(), name)

    def _save(self, name, content):
        full_path = self.path(name)
        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(full_path, 'wb+') as f:
            for chunk in content.chunks():
                f.write(chunk)
        return name

    def exists(self, name):
        return os.path.exists(self.path(name))

    def delete(self, name):
        if self.exists(name):
            os.remove(self.path(name))

    def size(self, name):
        return os.path.getsize(self.path(name))

    def url(self, name):
        from django.urls import reverse

        return reverse('library:serve_upload', kwargs={'path': name})


def library_file_upload_to(instance, filename):
    """Docs -> ``files/``, gallery images -> ``images/`` under library root."""
    name = os.path.basename(filename)
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    subfolder = 'images' if ext in IMAGE_EXTENSIONS else 'files'
    return '{}/{}'.format(subfolder, name)


def library_preview_upload_to(instance, filename):
    return 'images/{}'.format(os.path.basename(filename))
