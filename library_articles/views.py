import os
from datetime import timedelta

import bleach
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import log_activity
from library.forms import CategoryForm, LibraryItemForm
from library.models import Category, LibraryAttachment, LibraryItem, Tag
from library.storage import IMAGE_EXTENSIONS, LibraryStorage
from library.utils import get_article_folder_path

ALLOWED_HTML_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div',
]
ALLOWED_HTML_ATTRS = {
    'a': ['href', 'target'],
    'img': ['src', 'alt', 'width', 'height'],
    'span': ['style'],
    'div': ['style'],
}


def _clean_html(content):
    if not content:
        return content
    return bleach.clean(content, tags=ALLOWED_HTML_TAGS, attributes=ALLOWED_HTML_ATTRS, strip=True)


def _apply_common_filters(items, request):
    query = request.GET.get('q', '')
    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(content__icontains=query)
            | Q(summary__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    category_slug = request.GET.get('category', '')
    if category_slug:
        items = items.filter(category__slug=category_slug)

    file_type = request.GET.get('type', '')
    if file_type:
        items = items.filter(file_type=file_type)

    if request.GET.get('favorites', ''):
        items = items.filter(is_favorite=True)

    tag_slug = request.GET.get('tag', '')
    if tag_slug:
        items = items.filter(tags__slug=tag_slug)

    date_filter = request.GET.get('date', '')
    if date_filter:
        now = timezone.now()
        if date_filter == 'today':
            items = items.filter(created_at__date=now.date())
        elif date_filter == 'week':
            items = items.filter(created_at__gte=now - timedelta(days=7))
        elif date_filter == 'month':
            items = items.filter(created_at__gte=now - timedelta(days=30))
        elif date_filter == 'year':
            items = items.filter(created_at__gte=now - timedelta(days=365))

    return items


def _list_context(items_page, request):
    categories = Category.objects.filter(is_active=True).annotate(item_count=Count('items'))
    tags = Tag.objects.annotate(
        item_count=Count('items', filter=Q(items__is_active=True))
    ).filter(item_count__gt=0).order_by('-item_count')[:20]
    return {
        'items': items_page,
        'query': request.GET.get('q', ''),
        'categories': categories,
        'file_types': LibraryItem.FILE_TYPE_CHOICES,
        'tags': tags,
        'current_category': request.GET.get('category', ''),
        'current_type': request.GET.get('type', ''),
        'favorites_only': request.GET.get('favorites', ''),
        'view_mode': request.GET.get('view', 'grid'),
        'current_tag': request.GET.get('tag', ''),
        'current_date': request.GET.get('date', ''),
    }


@login_required
def article_list(request):
    """Articles only — no Articles/Files/All segment control."""
    items = (
        LibraryItem.objects.filter(is_active=True)
        .exclude(content__isnull=True)
        .exclude(content='')
        .select_related('category')
        .prefetch_related('tags')
        .order_by('-created_at')
    )
    items = _apply_common_filters(items, request)

    paginator = Paginator(items, 24)
    items_page = paginator.get_page(request.GET.get('page', 1))
    ctx = _list_context(items_page, request)

    if request.headers.get('HX-Request'):
        return render(request, 'library_articles/list_partial.html', ctx)
    return render(request, 'library_articles/list.html', ctx)


@login_required
def article_detail(request, slug):
    item = get_object_or_404(
        LibraryItem.objects.select_related('category').prefetch_related('tags', 'attachments'),
        slug=slug, is_active=True,
    )
    return render(request, 'library_articles/detail.html', {'item': item})


def _prepare_picture_field(form):
    field = form.fields.get('file')
    if field is not None:
        field.widget.attrs['accept'] = 'image/*'


def _validate_picture(request, form):
    uploaded = request.FILES.get('file')
    if uploaded:
        ext = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext not in IMAGE_EXTENSIONS:
            form.add_error('file', 'Please upload an image (JPG, PNG, GIF, WebP).')
            return False
    return True


def _delete_storage_file(name):
    if not name:
        return
    try:
        LibraryStorage().delete(name)
    except Exception:
        pass


@login_required
def article_create(request):
    if request.method == 'POST':
        form = LibraryItemForm(request.POST, request.FILES)
        _prepare_picture_field(form)
        if form.is_valid() and _validate_picture(request, form):
            item = form.save(commit=False)
            item.content = _clean_html(item.content)
            item.created_by = request.user
            item.save()
            form._save_tags(item)
            for f in request.FILES.getlist('additional_files'):
                LibraryAttachment.objects.create(item=item, file=f)
            if item.content or item.file:
                item.save_as_md(item.content or '')
            log_activity(request.user, 'created', f'Article "{item.title}"', item)
            messages.success(request, 'Article created successfully.')
            return redirect('library_articles:detail', slug=item.slug)
    else:
        form = LibraryItemForm()
        _prepare_picture_field(form)
    return render(request, 'library_articles/form.html', {
        'form': form,
        'title': 'New Article',
        'categories': Category.objects.filter(is_active=True),
        'existing_tags': Tag.objects.all().order_by('name'),
    })


@login_required
def article_edit(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    old_file_name = item.file.name if item.file else None
    if request.method == 'POST':
        form = LibraryItemForm(request.POST, request.FILES, instance=item)
        _prepare_picture_field(form)
        if form.is_valid() and _validate_picture(request, form):
            item = form.save(commit=False)
            item.content = _clean_html(item.content)
            if request.POST.get('remove_picture') and 'file' not in request.FILES:
                if item.file:
                    item.file.delete(save=False)
                    item.file = None
            item.save()
            form._save_tags(item)
            if old_file_name and item.file and item.file.name != old_file_name:
                _delete_storage_file(old_file_name)
            if item.content or item.file:
                item.save_as_md(item.content or '')
            log_activity(request.user, 'updated', f'Article "{item.title}"', item)
            messages.success(request, 'Article updated successfully.')
            return redirect('library_articles:detail', slug=item.slug)
    else:
        form = LibraryItemForm(instance=item)
        _prepare_picture_field(form)
    return render(request, 'library_articles/form.html', {
        'form': form,
        'title': 'Edit Article',
        'item': item,
        'categories': Category.objects.filter(is_active=True),
        'existing_tags': Tag.objects.all().order_by('name'),
    })


@login_required
def article_delete(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    if request.method == 'POST':
        item.delete_from_disk()
        item.is_active = False
        item.save()
        log_activity(request.user, 'deleted', f'Article "{item.title}"')
        messages.success(request, 'Article deleted successfully.')
        return redirect('library_articles:list')
    return render(request, 'library_articles/confirm_delete.html', {'item': item})


@login_required
def article_delete_htmx(request, slug):
    if request.method == 'DELETE':
        item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
        item.delete_from_disk()
        item.is_active = False
        item.save()
        log_activity(request.user, 'deleted', f'Article "{item.title}"')
        return HttpResponse('')
    return HttpResponse(status=405)


@login_required
def article_toggle_favorite(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    item.is_favorite = not item.is_favorite
    item.save()
    return JsonResponse({'is_favorite': item.is_favorite})


@login_required
def article_import_url(request):
    # Reuse the same import flow as legacy library (URL -> article).
    # Keeps DuckDuckGo/external search workflow untouched.
    from library.views import library_import_url as legacy_import

    return legacy_import(request)


@login_required
def article_serve_image(request, slug, image_path):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    folder_path = get_article_folder_path(item)
    full_path = os.path.normpath(os.path.join(folder_path, 'images', image_path))
    images_dir = os.path.normpath(os.path.join(folder_path, 'images'))
    if not full_path.startswith(images_dir + os.sep) and full_path != images_dir:
        raise Http404('Invalid path')
    if not os.path.exists(full_path):
        raise Http404('File not found')
    return FileResponse(open(full_path, 'rb'), filename=os.path.basename(full_path))


@login_required
def article_upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        from django.core.files.storage import default_storage

        image = request.FILES['image']
        path = default_storage.save(f'library/content/{image.name}', image)
        return JsonResponse({'url': default_storage.url(path)})
    return JsonResponse({'error': 'No image provided'}, status=400)


@login_required
def article_upload_attachment(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    if request.method == 'POST' and request.FILES.get('file'):
        attachment = LibraryAttachment.objects.create(item=item, file=request.FILES['file'])
        return JsonResponse({'id': attachment.pk, 'name': attachment.name})
    return JsonResponse({'error': 'No file provided'}, status=400)


@login_required
def article_delete_attachment(request, slug, att_id):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    attachment = get_object_or_404(LibraryAttachment, pk=att_id, item=item)
    if request.method == 'POST':
        try:
            if attachment.file and os.path.exists(attachment.file.path):
                attachment.file.delete(save=False)
        except Exception:
            pass
        attachment.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse('')
        return redirect('library_articles:edit', slug=slug)
    return HttpResponse(status=405)


@login_required
def category_list(request):
    categories = Category.objects.filter(is_active=True).annotate(
        item_count=Count('items', filter=Q(items__is_active=True))
    ).order_by('name')
    if request.headers.get('HX-Request'):
        return render(request, 'library_articles/category_list_partial.html', {'categories': categories})
    return render(request, 'library_articles/category_list.html', {'categories': categories})


@login_required
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    items = LibraryItem.objects.filter(is_active=True, category=category).order_by('-created_at')
    paginator = Paginator(items, 24)
    items_page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'library_articles/category_detail.html', {
        'category': category, 'items': items_page,
    })


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Category "{category.name}" created.')
            return redirect('library_articles:category_list')
    else:
        form = CategoryForm()
    return render(request, 'library_articles/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
def category_edit(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('library_articles:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'library_articles/category_form.html',
                  {'form': form, 'title': 'Edit Category', 'category': category})


@login_required
def category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Category "{category.name}" deleted.')
        return redirect('library_articles:category_list')
    return render(request, 'library_articles/category_confirm_delete.html', {'category': category})


@login_required
def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    items = LibraryItem.objects.filter(tags=tag, is_active=True).order_by('-created_at')
    return render(request, 'library_articles/tag_detail.html', {'tag': tag, 'items': items})


@login_required
def category_create_api(request):
    import json

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'error': 'Name is required'}, status=400)
            category = Category.objects.create(
                name=name,
                color=data.get('color', '#8B5CF6'),
                created_by=request.user,
            )
            return JsonResponse({'id': category.pk, 'name': category.name, 'slug': category.slug})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def tag_create_api(request):
    import json

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'error': 'Name is required'}, status=400)
            tag, created = Tag.objects.get_or_create(name=name)
            return JsonResponse({'id': tag.pk, 'name': tag.name, 'slug': tag.slug, 'created': created})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def quick_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        from library.views import library_quick_upload as legacy_quick

        return legacy_quick(request)
    return JsonResponse({'error': 'No file provided'}, status=400)
