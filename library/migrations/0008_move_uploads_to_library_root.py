import os
import shutil

from django.db import migrations


def _unique_dest_rel(storage, dest_rel):
    if not storage.exists(dest_rel):
        return dest_rel
    return storage.get_available_name(dest_rel)


def move_library_uploads(apps, schema_editor):
    from django.conf import settings

    from library.storage import IMAGE_EXTENSIONS, LibraryStorage
    from library.utils import get_article_folder_name

    LibraryItem = apps.get_model('library', 'LibraryItem')
    LibraryAttachment = apps.get_model('library', 'LibraryAttachment')

    storage = LibraryStorage()
    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    root = os.path.normpath(storage._get_location())

    def move_physical(old_name, dest_rel):
        """Move a file into the library root. Returns the new storage-relative name."""
        if not old_name:
            return old_name
        if os.path.isabs(old_name):
            src = os.path.normpath(old_name)
        else:
            src = os.path.normpath(os.path.join(media_root, old_name))
        dst = os.path.normpath(os.path.join(root, dest_rel))
        if os.path.normcase(src) == os.path.normcase(dst):
            return dest_rel
        if os.path.isfile(src):
            final_rel = dest_rel
            final_dst = dst
            if os.path.exists(final_dst):
                final_rel = _unique_dest_rel(storage, dest_rel)
                final_dst = os.path.normpath(os.path.join(root, final_rel))
            os.makedirs(os.path.dirname(final_dst), exist_ok=True)
            shutil.move(src, final_dst)
            return final_rel
        # Physical file missing (already deleted?) — still normalize the DB path.
        return dest_rel

    def route(filename):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return 'images' if ext in IMAGE_EXTENSIONS else 'files'

    for item in LibraryItem.objects.all():
        updated = {}
        if item.file:
            base = os.path.basename(item.file.name)
            if base:
                updated['file'] = move_physical(item.file.name, '{}/{}'.format(route(base), base))
        if item.preview_image:
            base = os.path.basename(item.preview_image.name)
            if base:
                updated['preview_image'] = move_physical(item.preview_image.name, 'images/{}'.format(base))
        for field_name, new_name in updated.items():
            setattr(item, field_name, new_name)
        if updated:
            item.save(update_fields=list(updated))

    for att in LibraryAttachment.objects.select_related('item').all():
        if not att.file:
            continue
        base = os.path.basename(att.file.name)
        if not base:
            continue
        try:
            folder = get_article_folder_name(att.item)
        except Exception:
            continue
        att.file.name = move_physical(att.file.name, '{}/attachments/{}'.format(folder, base))
        att.save(update_fields=['file'])

    # Remove leftover empty legacy directories under MEDIA_ROOT.
    for legacy in ('library/files', 'library/previews', 'library/attachments'):
        try:
            os.rmdir(os.path.join(media_root, legacy))
        except OSError:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0007_alter_libraryattachment_file_alter_libraryitem_file_and_more'),
    ]

    operations = [
        migrations.RunPython(move_library_uploads, migrations.RunPython.noop),
    ]
