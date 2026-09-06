from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import log_activity
from library.models import LibraryItem


@login_required
def file_list(request):
    items = (
        LibraryItem.objects.filter(is_active=True, file__isnull=False)
        .exclude(file='')
        .filter(Q(content__isnull=True) | Q(content=''))
        .select_related('category')
        .order_by('-created_at')
    )

    query = request.GET.get('q', '')
    if query:
        items = items.filter(Q(title__icontains=query) | Q(file__icontains=query))

    file_type = request.GET.get('type', '')
    if file_type:
        items = items.filter(file_type=file_type)

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

    sort = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'date': 'created_at', '-date': '-created_at',
        'name': 'title', '-name': '-title',
        'type': 'file_type', '-type': '-file_type',
    }
    items = items.order_by(valid_sorts.get(sort, '-created_at'))

    view_mode = request.GET.get('view', 'list')

    paginator = Paginator(items, 20)
    items_page = paginator.get_page(request.GET.get('page', 1))
    ctx = {
        'items': items_page,
        'query': query,
        'current_type': file_type,
        'file_types': LibraryItem.FILE_TYPE_CHOICES,
        'current_sort': sort,
        'current_date': date_filter,
        'view_mode': view_mode,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'library_files/list_partial.html', ctx)
    return render(request, 'library_files/list.html', ctx)


@login_required
def file_detail(request, slug):
    item = get_object_or_404(
        LibraryItem.objects.select_related('category').prefetch_related('tags', 'attachments'),
        slug=slug, is_active=True,
    )
    return render(request, 'library_files/detail.html', {'item': item})


@login_required
def file_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        file_type = {
            'pdf': 'pdf', 'djvu': 'djvu', 'docx': 'docx',
            'txt': 'txt', 'rtf': 'rtf', 'md': 'md',
            'jpg': 'image', 'jpeg': 'image', 'png': 'image',
            'webp': 'image', 'gif': 'image',
        }.get(ext, 'other')
        item = LibraryItem(
            title=uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name,
            file=uploaded_file,
            file_type=file_type,
            created_by=request.user,
        )
        item.save()
        log_activity(request.user, 'created', f'File "{item.title}" (upload)', item)
        return JsonResponse({'success': True, 'slug': item.slug})
    return JsonResponse({'error': 'No file provided'}, status=400)
