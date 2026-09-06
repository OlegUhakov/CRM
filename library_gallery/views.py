from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models import log_activity
from library.models import LibraryItem


def _gallery_queryset():
    image_filter = (
        Q(file_type='image')
        | Q(attachments__file__icontains='.jpg')
        | Q(attachments__file__icontains='.jpeg')
        | Q(attachments__file__icontains='.png')
        | Q(attachments__file__icontains='.webp')
    )
    return (
        LibraryItem.objects.filter(is_active=True)
        .filter(image_filter)
        .select_related('category')
        .distinct()
        .order_by('-created_at')
    )


@login_required
def gallery_list(request):
    items = _gallery_queryset()

    query = request.GET.get('q', '')
    if query:
        items = items.filter(Q(title__icontains=query) | Q(description__icontains=query))

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

    paginator = Paginator(items, 36)
    items_page = paginator.get_page(request.GET.get('page', 1))
    ctx = {
        'items': items_page,
        'query': query,
        'current_date': date_filter,
        'view_mode': view_mode,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'library_gallery/list_partial.html', ctx)
    return render(request, 'library_gallery/list.html', ctx)


@login_required
def photo_detail(request, slug):
    item = get_object_or_404(
        LibraryItem.objects.select_related('category').prefetch_related('tags', 'attachments'),
        slug=slug, is_active=True,
    )
    return render(request, 'library_gallery/detail.html', {'item': item})


@login_required
def photo_upload(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        item = LibraryItem(
            title=uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name,
            file=uploaded_file,
            file_type='image',
            created_by=request.user,
        )
        item.save()
        log_activity(request.user, 'created', f'Photo "{item.title}" (upload)', item)
        return JsonResponse({'success': True, 'slug': item.slug})
    return JsonResponse({'error': 'No file provided'}, status=400)
