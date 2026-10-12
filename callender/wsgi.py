"""WSGI giriş noktası. Vercel `app` adını arar."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "callender.settings")

application = get_wsgi_application()
app = application
