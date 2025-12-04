"""
ASGI config for aadhar_masking_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import multiprocessing

# ✅ Mac & Windows safe for multiprocessing (Critical for PaddleOCR)
try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aadhar_masking_project.settings')

application = get_asgi_application()
