"""
Django settings for aadhar_masking_project project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-zqoalkg7_xlhavvjzolz8g7s!yj2q_z@cx_!=w@g64j7nm$5(^'
DEBUG = True
ALLOWED_HOSTS = []   # ⚠️ Later, add domain/IP here in production

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'masking',  # Your app
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

ROOT_URLCONF = 'aadhar_masking_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # ✅ Templates folder enabled
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aadhar_masking_project.wsgi.application'

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

# ✅ Static & Media settings
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",  # ensure folder exists
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # for collectstatic (optional but useful)

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Add to the bottom of your settings.py or merge safely ---

# Path to tesseract executable (override via env var if needed)
TESSERACT_CMD = os.environ.get('TESSERACT_CMD', '/opt/homebrew/bin/tesseract')
# Mask style: "solid", "blur", or "pixelate"
MASK_STYLE = os.environ.get('MASK_STYLE', 'solid')
# PaddleOCR languages default (comma-separated names or single)
PADDLE_OCR_LANG = os.environ.get('PADDLE_OCR_LANG', 'en')
# OCR confidence thresholds (tweakable)
OCR_CONF_MIN = int(os.environ.get('OCR_CONF_MIN', '30'))
OCR_CONF_STRICT = int(os.environ.get('OCR_CONF_STRICT', '40'))

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ...

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'masking' / 'static',
]

