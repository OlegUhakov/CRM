import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-(5d+qcof*xrx0%nq4-xjhr$mj1@n75==ttb15-0e_uy!d(#h^-')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

_hosts_raw = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _hosts_raw.split(',') if h.strip()] if _hosts_raw else ['localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'companies',
    'contacts',
    'projects',
    'materials',
    'tasks',
    'notes',
    'generator',
    'documents',
    'parts',
    'assistant',
    'calendar_app',
    'library',
    'library_articles',
    'library_gallery',
    'library_files',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.app_version',
                'core.context_processors.sidebar_projects',
                'core.context_processors.current_workspace',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DOCUMENTS_ROOT = BASE_DIR / 'documents'
DOCUMENTS_URL = '/files/'

PROJECT_ROOT_PATH = str(BASE_DIR / 'media')

LIBRARY_ROOT = BASE_DIR / 'media' / 'library'

AI_FILES_ROOT = BASE_DIR / 'ai_files'
AI_FILES_URL = '/ai-files/'
AI_FILES_MAX_SIZE = 50 * 1024 * 1024
AI_FILES_TOTAL_QUOTA = 1024 * 1024 * 1024

AI_BROWSER_BLACKLIST = [
    'malware-site.example',
    'phishing.example',
]
AI_BROWSER_TIMEOUT = 20

OLLAMA_BASE_URL = 'http://localhost:11434'
OLLAMA_DEFAULT_MODEL = ''

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Password reset — console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Session security
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 1 week
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

X_FRAME_OPTIONS = 'SAMEORIGIN'

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
