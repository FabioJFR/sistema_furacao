from pathlib import Path

import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-ahs1cu-_etpmaxvd&k-iu@mdhc+w7g6=x+blxrwe7bs57=b2*9'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'projetos.apps.ProjetosConfig',
    'widget_tweaks',
    'core',
    'plataforma',
    'website',
    'dispositivos',
    'rest_framework',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'projetos.middleware.UserLanguageMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'website' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "projetos.context_processors.menu_context",
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "sistema_furacao",
        "USER": "fabiorevez",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-pt'

LANGUAGES = [
    ('pt-pt', 'Português'),
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'Français'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = 'Europe/Lisbon'

USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = '/login/'  # website app
LOGIN_REDIRECT_URL = '/app/'
LOGOUT_REDIRECT_URL = '/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@sistemafuracao.local'


LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} | {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },

    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "errors.log",
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
        },
    },

    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
        },

        # 👇 teu projeto
        "core": {
            "handlers": ["file", "error_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}