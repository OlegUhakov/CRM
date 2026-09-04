from django.urls import path
from . import views

app_name = 'core'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search_view, name='search'),
    path('help/', views.help_page, name='help'),
    path('workspace/switch/', views.workspace_switch, name='workspace_switch'),
    path('settings/', views.settings_page, name='settings_page'),
    path('settings/save/', views.save_setting, name='save_setting'),
    path('settings/<str:key>/', views.get_setting, name='get_setting'),
    path('ai/fetch-models/', views.ai_fetch_models, name='ai_fetch_models'),
    path('api/settings/ai/providers', views.api_providers, name='api_providers'),
    path('api/settings/ai/providers/<str:provider_id>', views.api_provider_update, name='api_provider_update'),
    path('api/settings/ai/providers/<str:provider_id>/verify', views.api_provider_verify, name='api_provider_verify'),
    path('api/settings/ai/providers/<str:provider_id>/sync-models', views.api_provider_sync_models, name='api_provider_sync_models'),
    path('api/settings/ai/providers/<str:provider_id>/models', views.api_provider_models_or_add, name='api_provider_models'),
    path('api/settings/ai/providers/<str:provider_id>/models/<str:model_id>', views.api_provider_model_delete, name='api_provider_model_delete'),
    path('api/settings/ai/active-provider', views.api_active_provider, name='api_active_provider'),
    path('api/settings/general', views.api_general_settings, name='api_general_settings'),
    path('api/settings/users', views.api_users, name='api_users'),
    path('api/settings/users/<int:user_id>', views.api_user_update, name='api_user_update'),
    path('api/settings/users/<int:user_id>/delete', views.api_user_delete, name='api_user_delete'),
    path('project-files/<path:file_path>', views.serve_project_file, name='serve_project_file'),
]
