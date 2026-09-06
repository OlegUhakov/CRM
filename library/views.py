import json
import os
import bleach
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.template.loader import render_to_string
from .models import LibraryItem, Category, Tag, LibraryAttachment
from .forms import LibraryItemForm, CategoryForm
from .utils import get_article_folder_path, get_library_root
from core.models import log_activity


@login_required
def library_serve_image(request, slug, image_path):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    folder_path = get_article_folder_path(item)
    full_path = os.path.normpath(os.path.join(folder_path, 'images', image_path))
    images_dir = os.path.normpath(os.path.join(folder_path, 'images'))
    if not full_path.startswith(images_dir + os.sep) and full_path != images_dir:
        raise Http404("Invalid path")
    if not os.path.exists(full_path):
        raise Http404("File not found")
    return FileResponse(open(full_path, 'rb'), filename=os.path.basename(full_path))


@login_required
def library_serve_upload(request, path):
    """Serve files from the library root (files/, images/, article folders)."""
    import mimetypes

    root = os.path.normpath(get_library_root())
    full_path = os.path.normpath(os.path.join(root, path))
    if not full_path.startswith(root + os.sep) and full_path != root:
        raise Http404("Invalid path")
    if not os.path.isfile(full_path):
        raise Http404("File not found")
    content_type, _ = mimetypes.guess_type(full_path)
    return FileResponse(
        open(full_path, 'rb'),
        filename=os.path.basename(full_path),
        content_type=content_type or 'application/octet-stream',
    )


@login_required
def library_dashboard(request):
    recent = LibraryItem.objects.filter(is_active=True).order_by('-created_at')[:10]
    favorites = LibraryItem.objects.filter(is_active=True, is_favorite=True).order_by('-updated_at')[:10]
    categories = Category.objects.filter(is_active=True).annotate(item_count=Count('items')).filter(item_count__gt=0)
    return render(request, 'library/dashboard.html', {
        'recent': recent,
        'favorites': favorites,
        'categories': categories,
    })


@login_required
def library_list(request):
    items = LibraryItem.objects.filter(is_active=True).select_related('category').prefetch_related('tags')

    query = request.GET.get('q', '')
    if query:
        items = items.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(content__icontains=query) |
            Q(summary__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

    category_slug = request.GET.get('category', '')
    if category_slug:
        items = items.filter(category__slug=category_slug)

    content_type = request.GET.get('content_type', 'article')
    if content_type == 'article':
        items = items.filter(Q(content__isnull=False) | Q(content__gt=''))
    elif content_type == 'file':
        items = items.filter(file__isnull=False).exclude(file='').filter(Q(content__isnull=True) | Q(content=''))

    file_type = request.GET.get('type', '')
    if file_type:
        items = items.filter(file_type=file_type)

    favorites_only = request.GET.get('favorites', '')
    if favorites_only:
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

    view_mode = request.GET.get('view', 'grid')
    paginator = Paginator(items, 24)
    page = request.GET.get('page', 1)
    items_page = paginator.get_page(page)

    categories = Category.objects.filter(is_active=True).annotate(item_count=Count('items'))
    file_types = LibraryItem.FILE_TYPE_CHOICES
    tags = Tag.objects.annotate(item_count=Count('items', filter=Q(items__is_active=True))).filter(item_count__gt=0).order_by('-item_count')[:20]

    if request.headers.get('HX-Request'):
        return render(request, 'library/list_partial.html', {
            'items': items_page,
            'query': query,
            'categories': categories,
            'file_types': file_types,
            'tags': tags,
            'current_category': category_slug,
            'current_type': file_type,
            'current_content_type': content_type,
            'favorites_only': favorites_only,
            'view_mode': view_mode,
            'current_tag': tag_slug,
            'current_date': date_filter,
        })

    return render(request, 'library/list.html', {
        'items': items_page,
        'query': query,
        'categories': categories,
        'file_types': file_types,
        'tags': tags,
        'current_category': category_slug,
        'current_type': file_type,
        'current_content_type': content_type,
        'favorites_only': favorites_only,
        'view_mode': view_mode,
        'current_tag': tag_slug,
        'current_date': date_filter,
    })


@login_required
def library_detail(request, slug):
    item = get_object_or_404(LibraryItem.objects.select_related('category').prefetch_related('tags', 'attachments'), slug=slug, is_active=True)
    return render(request, 'library/detail.html', {'item': item})


@login_required
def library_import_url(request):
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        if not url:
            messages.error(request, 'Please provide a URL.')
            return render(request, 'library/form.html', {'url': url, 'categories': Category.objects.filter(is_active=True), 'active_tab': 'import'})

        try:
            import urllib.request
            import urllib.parse
            from bs4 import BeautifulSoup

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            with urllib.request.urlopen(req, timeout=15) as response:
                html_content = response.read().decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html_content, 'html.parser')

            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else url.split('/')[-1].replace('-', ' ').replace('_', ' ')

            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            meta_desc = soup.find('meta', attrs={'name': 'description'})
            summary = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else ''

            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)
                if not summary:
                    summary = text[:300] + '...' if len(text) > 300 else text
            else:
                text = soup.get_text(separator=' ', strip=True)
                if not summary:
                    summary = text[:300] + '...' if len(text) > 300 else text

            content_html = ''
            downloaded_images = {}
            if body:
                for tag in body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'pre', 'code', 'img', 'a']):
                    if tag.name == 'img':
                        src = tag.get('src', '')
                        alt = tag.get('alt', '')
                        if src:
                            try:
                                abs_url = urllib.parse.urljoin(url, src)
                                img_name = urllib.parse.urlparse(abs_url).path.split('/')[-1]
                                if not img_name or '.' not in img_name:
                                    img_name = f'img_{len(downloaded_images)+1}.jpg'
                                img_req = urllib.request.Request(abs_url, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                                    downloaded_images[img_name] = img_resp.read()
                                content_html += f'<p><img src="{abs_url}" alt="{alt}"></p>'
                            except Exception:
                                content_html += f'<p><img src="{src}" alt="{alt}"></p>'
                    elif tag.name == 'a':
                        href = tag.get('href', '')
                        link_text = tag.get_text(strip=True)
                        if href and link_text:
                            content_html += f'<p><a href="{href}" target="_blank">{link_text}</a></p>'
                    else:
                        content_html += str(tag)

            if not content_html:
                content_html = f'<p>{text}</p>'

            item = LibraryItem(
                title=title,
                content=bleach.clean(content_html, tags=['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'], attributes={'a': ['href', 'target'], 'img': ['src', 'alt', 'width', 'height'], 'span': ['style'], 'div': ['style']}, strip=True),
                summary=summary,
                source_url=url,
                created_by=request.user,
            )
            item.save()

            if downloaded_images:
                first_img_name = next(iter(downloaded_images))
                first_img_data = downloaded_images[first_img_name]
                from django.core.files.base import ContentFile
                item.preview_image.save(first_img_name, ContentFile(first_img_data), save=False)
                item.save()

            tags_input = request.POST.get('tags_input', '')
            if tags_input:
                tag_names = [t.strip() for t in tags_input.split(',') if t.strip()]
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    item.tags.add(tag)

            category_id = request.POST.get('category')
            if category_id:
                try:
                    item.category = Category.objects.get(id=category_id, is_active=True)
                    item.save()
                except Category.DoesNotExist:
                    pass

            if item.content:
                item.save_as_md(item.content, images=downloaded_images if downloaded_images else None)

            log_activity(request.user, 'created', f'Library item "{item.title}" (imported from URL)', item)
            messages.success(request, 'Document imported successfully from URL.')
            return redirect('library:detail', slug=item.slug)

        except Exception as e:
            messages.error(request, f'Failed to import URL: {str(e)}')
            return render(request, 'library/form.html', {'url': url, 'categories': Category.objects.filter(is_active=True), 'active_tab': 'import'})

    categories = Category.objects.filter(is_active=True)
    return render(request, 'library/form.html', {
        'categories': categories,
        'active_tab': 'import',
    })


@login_required
def library_create(request):
    if request.method == 'POST':
        form = LibraryItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            if item.content:
                item.content = bleach.clean(item.content, tags=['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'], attributes={'a': ['href', 'target'], 'img': ['src', 'alt', 'width', 'height'], 'span': ['style'], 'div': ['style']}, strip=True)
            item.created_by = request.user
            item.save()
            form._save_tags(item)
            for f in request.FILES.getlist('additional_files'):
                LibraryAttachment.objects.create(item=item, file=f)
            if item.content or item.file:
                item.save_as_md(item.content or '')
            log_activity(request.user, 'created', f'Library item "{item.title}"', item)
            messages.success(request, 'Document created successfully.')
            return redirect('library:detail', slug=item.slug)
    else:
        form = LibraryItemForm()
    categories = Category.objects.filter(is_active=True)
    existing_tags = Tag.objects.all().order_by('name')
    return render(request, 'library/form.html', {
        'form': form,
        'title': 'Create Document',
        'categories': categories,
        'existing_tags': existing_tags,
        'active_tab': 'editor',
    })


@login_required
def library_edit(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    old_file_name = item.file.name if item.file else None
    if request.method == 'POST':
        form = LibraryItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save(commit=False)
            if item.content:
                item.content = bleach.clean(item.content, tags=['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'], attributes={'a': ['href', 'target'], 'img': ['src', 'alt', 'width', 'height'], 'span': ['style'], 'div': ['style']}, strip=True)
            if request.POST.get('remove_picture') and 'file' not in request.FILES:
                if item.file:
                    item.file.delete(save=False)
                    item.file = None
            item.save()
            form._save_tags(item)
            if old_file_name and item.file and item.file.name != old_file_name:
                try:
                    item.file.storage.delete(old_file_name)
                except Exception:
                    pass
            if item.content or item.file:
                item.save_as_md(item.content or '')
            log_activity(request.user, 'updated', f'Library item "{item.title}"', item)
            messages.success(request, 'Document updated successfully.')
            return redirect('library:detail', slug=item.slug)
    else:
        form = LibraryItemForm(instance=item)
    categories = Category.objects.filter(is_active=True)
    existing_tags = Tag.objects.all().order_by('name')
    return render(request, 'library/form.html', {
        'form': form,
        'title': 'Edit Document',
        'item': item,
        'categories': categories,
        'existing_tags': existing_tags,
        'active_tab': 'editor',
    })


@login_required
def library_delete(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    if request.method == 'POST':
        item.delete_from_disk()
        item.is_active = False
        item.save()
        log_activity(request.user, 'deleted', f'Library item "{item.title}"')
        messages.success(request, 'Document deleted successfully.')
        return redirect('library:list')
    return render(request, 'library/confirm_delete.html', {'item': item})


@login_required
def library_delete_htmx(request, slug):
    if request.method == 'DELETE':
        item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
        item.delete_from_disk()
        item.is_active = False
        item.save()
        log_activity(request.user, 'deleted', f'Library item "{item.title}"')
        return HttpResponse('')
    return HttpResponse(status=405)


@login_required
def library_toggle_favorite(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    item.is_favorite = not item.is_favorite
    item.save()
    return JsonResponse({'is_favorite': item.is_favorite})


@login_required
def library_upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        from django.core.files.storage import default_storage
        path = default_storage.save(f'library/content/{image.name}', image)
        url = default_storage.url(path)
        return JsonResponse({'url': url})
    return JsonResponse({'error': 'No image provided'}, status=400)


@login_required
def library_quick_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        type_mapping = {
            'pdf': 'pdf', 'djvu': 'djvu', 'docx': 'docx',
            'txt': 'txt', 'rtf': 'rtf', 'md': 'md',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image',
            'webp': 'image', 'gif': 'image',
        }
        file_type = type_mapping.get(ext, 'other')

        item = LibraryItem(
            title=uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name,
            file=uploaded_file,
            file_type=file_type,
            created_by=request.user,
        )
        item.save()
        log_activity(request.user, 'created', f'Library item "{item.title}" (quick upload)', item)
        return JsonResponse({'success': True, 'slug': item.slug})
    return JsonResponse({'error': 'No file provided'}, status=400)


@login_required
def library_upload_attachment(request, slug):
    item = get_object_or_404(LibraryItem, slug=slug, is_active=True)
    if request.method == 'POST' and request.FILES.get('file'):
        attachment = LibraryAttachment.objects.create(
            item=item,
            file=request.FILES['file'],
        )
        return JsonResponse({'id': attachment.pk, 'name': attachment.name})
    return JsonResponse({'error': 'No file provided'}, status=400)


@login_required
def library_delete_attachment(request, slug, att_id):
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
        return redirect('library:edit', slug=slug)
    return HttpResponse(status=405)


@login_required
def library_gallery(request):
    image_filter = Q(file_type='image') | Q(attachments__file__icontains='.jpg') | Q(attachments__file__icontains='.jpeg') | Q(attachments__file__icontains='.png') | Q(attachments__file__icontains='.webp')
    items = LibraryItem.objects.filter(
        is_active=True,
    ).filter(
        Q(content__isnull=True) | Q(content='')
    ).filter(
        image_filter
    ).select_related('category').distinct()

    paginator = Paginator(items, 36)
    page = request.GET.get('page', 1)
    items_page = paginator.get_page(page)

    if request.headers.get('HX-Request'):
        return render(request, 'library/gallery_partial.html', {'items': items_page})

    return render(request, 'library/gallery.html', {'items': items_page})


@login_required
def library_files(request):
    items = LibraryItem.objects.filter(
        is_active=True,
        file__isnull=False,
    ).exclude(
        file=''
    ).filter(
        Q(content__isnull=True) | Q(content='')
    ).select_related('category')

    query = request.GET.get('q', '')
    if query:
        items = items.filter(
            Q(title__icontains=query) |
            Q(file__icontains=query)
        )

    file_type = request.GET.get('type', '')
    if file_type:
        items = items.filter(file_type=file_type)

    sort = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'date': 'created_at',
        '-date': '-created_at',
        'name': 'title',
        '-name': '-title',
        'type': 'file_type',
        '-type': '-file_type',
    }
    sort_field = valid_sorts.get(sort, '-created_at')
    items = items.order_by(sort_field)

    paginator = Paginator(items, 20)
    page = request.GET.get('page', 1)
    items_page = paginator.get_page(page)

    file_types = LibraryItem.FILE_TYPE_CHOICES

    if request.headers.get('HX-Request'):
        return render(request, 'library/files_partial.html', {
            'items': items_page,
            'query': query,
            'current_type': file_type,
            'file_types': file_types,
            'current_sort': sort,
        })

    return render(request, 'library/files.html', {
        'items': items_page,
        'query': query,
        'current_type': file_type,
        'file_types': file_types,
        'current_sort': sort,
    })


@login_required
def category_list(request):
    categories = Category.objects.filter(is_active=True).annotate(
        item_count=Count('items', filter=Q(items__is_active=True))
    ).order_by('name')

    if request.headers.get('HX-Request'):
        return render(request, 'library/category_list_partial.html', {'categories': categories})

    return render(request, 'library/category_list.html', {'categories': categories})


@login_required
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    items = LibraryItem.objects.filter(
        is_active=True,
        category=category,
    ).select_related('category').prefetch_related('tags').order_by('-created_at')
    paginator = Paginator(items, 24)
    page = request.GET.get('page', 1)
    items_page = paginator.get_page(page)

    if request.headers.get('HX-Request'):
        return render(request, 'library/category_detail_partial.html', {
            'category': category,
            'items': items_page,
        })

    return render(request, 'library/category_detail.html', {
        'category': category,
        'items': items_page,
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
            if request.headers.get('HX-Request'):
                categories = Category.objects.filter(is_active=True).annotate(item_count=Count('items')).order_by('name')
                return render(request, 'library/category_list_partial.html', {'categories': categories})
            return redirect('library:category_list')
    else:
        form = CategoryForm()

    if request.headers.get('HX-Request'):
        return render(request, 'library/category_form_inline.html', {'form': form, 'title': 'Create Category'})

    return render(request, 'library/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
def category_edit(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            if request.headers.get('HX-Request'):
                categories = Category.objects.filter(is_active=True).annotate(item_count=Count('items')).order_by('name')
                return render(request, 'library/category_list_partial.html', {'categories': categories})
            return redirect('library:category_list')
    else:
        form = CategoryForm(instance=category)

    if request.headers.get('HX-Request'):
        return render(request, 'library/category_form_inline.html', {'form': form, 'title': 'Edit Category', 'category': category})

    return render(request, 'library/category_form.html', {'form': form, 'title': 'Edit Category', 'category': category})


@login_required
def category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Category "{category.name}" deleted.')
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('library:category_list')
    return render(request, 'library/category_confirm_delete.html', {'category': category})


@login_required
def category_create_api(request):
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
def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    items = LibraryItem.objects.filter(tags=tag, is_active=True)
    categories = Category.objects.filter(is_active=True)
    existing_tags = Tag.objects.all().order_by('name')
    return render(request, 'library/tag_detail.html', {
        'tag': tag,
        'items': items,
        'categories': categories,
        'existing_tags': existing_tags,
    })
