import os
import json
import urllib.request
import urllib.error
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.utils import timezone
from projects.models import Project
from tasks.models import Task
from companies.models import Company
from contacts.models import Contact
from library.models import LibraryItem
from notes.models import Note
from materials.models import Material
from parts.models import Part
from generator.models import Deal
from .models import AppSetting, AIProvider, AIModel, AppSettings
from projects.utils import get_project_root_path


@login_required
def dashboard(request):
    from django.db.models import Q as QFilter
    article_count = LibraryItem.objects.filter(is_active=True).exclude(QFilter(content__isnull=True) | QFilter(content='')).count()
    file_count = LibraryItem.objects.filter(is_active=True, file__isnull=False).exclude(file='').exclude(QFilter(content__isnull=False) & ~QFilter(content='')).count()
    context = {
        'project_count': Project.objects.filter(is_active=True).count(),
        'active_projects': Project.objects.filter(is_active=True, status='active').count(),
        'company_count': Company.objects.filter(is_active=True).count(),
        'contact_count': Contact.objects.filter(is_active=True).count(),
        'task_count': Task.objects.filter(is_active=True).count(),
        'article_count': article_count,
        'file_count': file_count,
        'recent_projects': Project.objects.filter(is_active=True).select_related('company').order_by('-created_at')[:6],
        'today_tasks': Task.objects.filter(is_active=True).select_related('project').order_by('-created_at')[:10],
        'recent_notes': Note.objects.filter(is_active=True).select_related('project', 'company', 'contact').order_by('-created_at')[:5],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def search_view(request):
    query = request.GET.get('q', '').strip()
    results = {
        'projects': [],
        'contacts': [],
        'companies': [],
        'tasks': [],
        'notes': [],
        'materials': [],
        'parts': [],
        'deals': [],
    }

    if query:
        results['projects'] = Project.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(number__icontains=query)
        )[:10]

        results['contacts'] = Contact.objects.filter(is_active=True).filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )[:10]

        results['companies'] = Company.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )[:10]

        results['tasks'] = Task.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:10]

        results['notes'] = Note.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )[:10]

        results['materials'] = Material.objects.filter(is_active=True).filter(
            Q(name__icontains=query)
        )[:10]

        results['parts'] = Part.objects.filter(is_active=True).filter(
            Q(number__icontains=query) | Q(size__icontains=query)
        )[:10]

        results['deals'] = Deal.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:10]

    return render(request, 'core/search_results.html', {
        'results': results,
        'query': query,
    })


@login_required
def settings_page(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.all().order_by('username')
    return render(request, 'core/settings.html', {'users': users})


@login_required
def save_setting(request):
    if request.method == 'POST':
        key = request.POST.get('key', '')
        value = request.POST.get('value', '')
        if key:
            AppSetting.set_value(key, value)
            return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=400)


@login_required
def get_setting(request, key):
    value = AppSetting.get_value(key, '')
    default = ''
    if not value and key == 'project_root_path':
        default = getattr(settings, 'PROJECT_ROOT_PATH', '')
    return JsonResponse({'key': key, 'value': value, 'default': default})


@login_required
def serve_project_file(request, file_path):
    if os.path.isabs(file_path):
        raise Http404("Invalid file path")

    root_path = get_project_root_path()
    if root_path:
        normalized_root = os.path.normpath(root_path)
        full_path = os.path.normpath(os.path.join(normalized_root, file_path))
        if full_path.startswith(normalized_root + os.sep) and os.path.exists(full_path):
            return FileResponse(open(full_path, 'rb'), filename=os.path.basename(full_path))

    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    media_path = os.path.normpath(os.path.join(media_root, file_path))
    if media_path.startswith(media_root + os.sep) and os.path.exists(media_path):
        return FileResponse(open(media_path, 'rb'), filename=os.path.basename(media_path))
    raise Http404("File not found")


@login_required
def help_page(request):
    return render(request, 'core/help.html')


@login_required
@require_POST
def workspace_switch(request):
    workspace = request.POST.get('workspace', 'projects')
    if workspace not in ('projects', 'collections'):
        workspace = 'projects'
    request.session['workspace'] = workspace
    from django.http import HttpResponseRedirect
    redirect_url = '/library/' if workspace == 'collections' else '/projects/'
    if request.headers.get('HX-Request'):
        from django.http import HttpResponse
        return HttpResponse(status=204, headers={'HX-Redirect': redirect_url})
    return HttpResponseRedirect(redirect_url)


PROVIDER_ENDPOINTS = {
    'anthropic': {
        'url': 'https://api.anthropic.com/v1/models',
        'headers': lambda key: {'x-api-key': key, 'anthropic-version': '2023-06-01'},
    },
    'openai': {
        'url': 'https://api.openai.com/v1/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
    'google': {
        'url': 'https://generativelanguage.googleapis.com/v1beta/models',
        'headers': lambda key: {'x-goog-api-key': key},
    },
    'mistral': {
        'url': 'https://api.mistral.ai/v1/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
    'groq': {
        'url': 'https://api.groq.com/openai/v1/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
    'deepseek': {
        'url': 'https://api.deepseek.com/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
    'openrouter': {
        'url': 'https://openrouter.ai/api/v1/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
    'opencode': {
        'url': 'https://opencode.ai/zen/v1/models',
        'headers': lambda key: {'Authorization': f'Bearer {key}'},
    },
}


def _normalize_models(provider, raw_data):
    models = []
    if provider == 'anthropic':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('display_name', m.get('id', ''))})
    elif provider == 'openai':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('id', '')})
    elif provider == 'google':
        for m in raw_data.get('models', []):
            full_name = m.get('name', '')
            model_id = full_name.replace('models/', '') if full_name.startswith('models/') else full_name
            models.append({'id': model_id, 'name': m.get('displayName', model_id)})
    elif provider == 'mistral':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('name', m.get('id', ''))})
    elif provider == 'groq':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('id', '')})
    elif provider == 'deepseek':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('id', '')})
    elif provider == 'openrouter':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('name', m.get('id', ''))})
    elif provider == 'opencode':
        for m in raw_data.get('data', []):
            models.append({'id': m.get('id', ''), 'name': m.get('id', '')})
    elif provider == 'ollama':
        for m in raw_data.get('models', []):
            model_id = m.get('model', '') or m.get('name', '')
            models.append({'id': model_id, 'name': m.get('name', model_id)})
    return models


@login_required
@require_POST
def ai_fetch_models(request):
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    provider = body.get('provider', '')
    api_key = body.get('api_key', '')
    base_url = body.get('base_url', 'http://localhost:11434')

    if provider == 'ollama':
        url = f'{base_url}/api/tags'
        headers = {}
        req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode())
                models = []
                for m in raw.get('models', []):
                    models.append({'id': m.get('model', ''), 'name': m.get('name', m.get('model', ''))})
                return JsonResponse({'ok': True, 'models': models})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})

    if provider not in PROVIDER_ENDPOINTS:
        return JsonResponse({'ok': False, 'error': f'Unknown provider: {provider}'}, status=400)

    if not api_key:
        return JsonResponse({'ok': False, 'error': 'API key is required.'}, status=400)

    endpoint = PROVIDER_ENDPOINTS[provider]
    url = endpoint['url']
    headers = endpoint['headers'](api_key)

    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
            models = _normalize_models(provider, raw)
            return JsonResponse({'ok': True, 'models': models})
    except urllib.error.HTTPError as e:
        error_body = ''
        try:
            error_body = e.read().decode()[:500]
        except Exception:
            pass
        return JsonResponse({'ok': False, 'error': f'HTTP {e.code}: {error_body or e.reason}'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_GET
def api_providers(request):
    providers = AIProvider.objects.all().order_by('id')
    data = []
    for p in providers:
        data.append({
            'id': p.id,
            'name': p.name,
            'type': p.type,
            'base_url': p.base_url or '',
            'selected_model': p.selected_model or '',
            'is_active': p.is_active,
            'key_verified_at': p.key_verified_at.isoformat() if p.key_verified_at else None,
            'models_synced_at': p.models_synced_at.isoformat() if p.models_synced_at else None,
            'api_key_masked': p.get_masked_key(),
            'has_api_key': bool(p.api_key_enc),
        })
    return JsonResponse({'ok': True, 'providers': data})


@login_required
@require_http_methods(["PUT"])
def api_provider_update(request, provider_id):
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    provider, _ = AIProvider.objects.get_or_create(
        id=provider_id,
        defaults={'name': provider_id.title(), 'type': 'cloud'}
    )

    if 'api_key' in body and body['api_key']:
        provider.set_api_key(body['api_key'])
    if 'base_url' in body:
        provider.base_url = body['base_url'] or None
    if 'selected_model' in body:
        provider.selected_model = body['selected_model'] or None

    provider.save()
    return JsonResponse({'ok': True, 'api_key_masked': provider.get_masked_key()})


@login_required
@require_POST
def api_provider_verify(request, provider_id):
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    try:
        provider = AIProvider.objects.get(id=provider_id)
    except AIProvider.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Provider not found.'}, status=404)

    api_key = provider.get_api_key()
    base_url = provider.base_url or 'http://localhost:11434'

    if provider_id == 'ollama':
        url = f'{base_url}/api/tags'
        req = urllib.request.Request(url, method='GET')
    else:
        if not api_key:
            return JsonResponse({'ok': False, 'error': 'No API key set.'}, status=400)
        if provider_id not in PROVIDER_ENDPOINTS:
            return JsonResponse({'ok': False, 'error': 'Unknown provider.'}, status=400)
        endpoint = PROVIDER_ENDPOINTS[provider_id]
        url = endpoint['url']
        req = urllib.request.Request(url, headers=endpoint['headers'](api_key), method='GET')

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            provider.key_verified_at = timezone.now()
            provider.save(update_fields=['key_verified_at', 'updated_at'])
            return JsonResponse({'ok': True, 'api_key_masked': provider.get_masked_key()})
    except urllib.error.HTTPError as e:
        return JsonResponse({'ok': False, 'error': f'HTTP {e.code}'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_POST
def api_provider_sync_models(request, provider_id):
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    try:
        provider = AIProvider.objects.get(id=provider_id)
    except AIProvider.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Provider not found.'}, status=404)

    api_key = provider.get_api_key()
    base_url = provider.base_url or 'http://localhost:11434'

    if provider_id == 'ollama':
        url = f'{base_url}/api/tags'
        req = urllib.request.Request(url, method='GET')
    else:
        if not api_key:
            return JsonResponse({'ok': False, 'error': 'No API key set.'}, status=400)
        if provider_id not in PROVIDER_ENDPOINTS:
            return JsonResponse({'ok': False, 'error': 'Unknown provider.'}, status=400)
        endpoint = PROVIDER_ENDPOINTS[provider_id]
        url = endpoint['url']
        req = urllib.request.Request(url, headers=endpoint['headers'](api_key), method='GET')

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
            fetched_models = _normalize_models(provider_id, raw)

            custom_models = list(AIModel.objects.filter(provider=provider, is_custom=True).values_list('model_id', flat=True))

            existing = {m.model_id: m for m in AIModel.objects.filter(provider=provider, is_custom=False)}

            for fm in fetched_models:
                if fm['id'] in existing:
                    obj = existing[fm['id']]
                    obj.name = fm['name']
                    obj.save(update_fields=['name'])
                else:
                    AIModel.objects.create(
                        provider=provider,
                        model_id=fm['id'],
                        name=fm['name'],
                        is_custom=False,
                        tags=[],
                    )

            fetched_ids = {fm['id'] for fm in fetched_models}
            stale_ids = [mid for mid, obj in existing.items() if mid not in fetched_ids]
            if stale_ids:
                AIModel.objects.filter(provider=provider, model_id__in=stale_ids, is_custom=False).delete()

            provider.models_synced_at = timezone.now()
            provider.save(update_fields=['models_synced_at', 'updated_at'])

            return JsonResponse({'ok': True, 'count': len(fetched_models)})
    except urllib.error.HTTPError as e:
        return JsonResponse({'ok': False, 'error': f'HTTP {e.code}'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})


@login_required
@require_http_methods(["GET", "POST"])
def api_provider_models_or_add(request, provider_id):
    try:
        provider = AIProvider.objects.get(id=provider_id)
    except AIProvider.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Provider not found.'}, status=404)

    if request.method == 'GET':
        models = AIModel.objects.filter(provider=provider).order_by('-is_custom', 'sort_order', 'name')
        data = [{
            'id': m.model_id,
            'name': m.name,
            'custom': m.is_custom,
            'tags': m.tags or [],
        } for m in models]
        return JsonResponse({'ok': True, 'models': data})

    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    model_id = (body.get('model_id') or '').strip()
    name = (body.get('name') or model_id).strip()

    if not model_id:
        return JsonResponse({'ok': False, 'error': 'model_id is required.'}, status=400)

    obj, created = AIModel.objects.get_or_create(
        provider=provider,
        model_id=model_id,
        defaults={'name': name, 'is_custom': True, 'tags': []}
    )
    if not created:
        return JsonResponse({'ok': False, 'error': 'Model already exists.'}, status=400)

    return JsonResponse({'ok': True, 'model': {'id': obj.model_id, 'name': obj.name, 'custom': True, 'tags': []}})


@login_required
@require_http_methods(["DELETE"])
def api_provider_model_delete(request, provider_id, model_id):
    try:
        provider = AIProvider.objects.get(id=provider_id)
    except AIProvider.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Provider not found.'}, status=404)

    deleted, _ = AIModel.objects.filter(provider=provider, model_id=model_id, is_custom=True).delete()
    if not deleted:
        return JsonResponse({'ok': False, 'error': 'Custom model not found.'}, status=404)

    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["PUT"])
def api_active_provider(request):
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

    provider_id = (body.get('provider_id') or '').strip()
    if not provider_id:
        return JsonResponse({'ok': False, 'error': 'provider_id is required.'}, status=400)

    AIProvider.objects.filter(is_active=True).update(is_active=False)
    updated = AIProvider.objects.filter(id=provider_id).update(is_active=True)
    if not updated:
        return JsonResponse({'ok': False, 'error': 'Provider not found.'}, status=404)

    return JsonResponse({'ok': True})


@login_required
def api_general_settings(request):
    if request.method == 'GET':
        settings_data = AppSettings.get_all()
        return JsonResponse({'ok': True, 'settings': settings_data})

    if request.method == 'PUT':
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Invalid JSON.'}, status=400)

        for key, value in body.items():
            AppSettings.set_value(key, value)

        return JsonResponse({'ok': True})

    return JsonResponse({'ok': False, 'error': 'Method not allowed.'}, status=405)
