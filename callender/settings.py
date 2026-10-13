"""
Callender ayarları. Tüm gizli/ortama bağlı değerler ortam değişkenlerinden okunur
(yerelde .env dosyası, canlıda Vercel ortam değişkenleri).
"""
import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from core import limits

BASE_DIR = Path(__file__).resolve().parent.parent

# Yerelde .env dosyasını yükle; Vercel'de dosya yoktur, ortam değişkenleri kullanılır.
# CALLENDER_ENV_FILE başka bir dosyayı gösterebilir (ör. canlıya migrate için .env.production);
# böylece canlı veritabanı şifresi terminal geçmişine yazılmaz. Var olan ortam değişkenleri ezilmez.
load_dotenv(os.environ.get("CALLENDER_ENV_FILE") or BASE_DIR / ".env")


def env_required(name):
    """Zorunlu ortam değişkenini okur; yoksa açık bir hata verir."""
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"{name} ortam değişkeni tanımlı değil. .env.example dosyasına bak.")
    return value


def env_list(name):
    """Virgülle ayrılmış ortam değişkenini listeye çevirir."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


SECRET_KEY = env_required("SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".vercel.app", *env_list("ALLOWED_HOSTS")]
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Callender uygulamaları
    "core",
    "accounts",
    "calendar_app",
    "families",
    "fridge",
    "home",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Her sayfa varsayılan olarak giriş ister; açık sayfalar @login_not_required ile işaretlenir
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "callender.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "families.context.family_context",
            ],
        },
    },
]

WSGI_APPLICATION = "callender.wsgi.application"

# Veritabanı: sadece Supabase PostgreSQL (pooler, Transaction mode, port 6543).
# Pooler bağlantıları kendisi yönettiği için kalıcı bağlantı ve sunucu taraflı imleç kapalı.
DATABASES = {
    "default": dj_database_url.parse(env_required("DATABASE_URL"), conn_max_age=0),
}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
# `manage.py test` aynı Supabase sunucusunda geçici bir test veritabanı açar ve sonunda siler
DATABASES["default"]["TEST"] = {"NAME": "test_callender"}
# Pooler test veritabanını açık tuttuğu için silme WITH (FORCE) ile yapılır (bkz. core/test_runner.py)
TEST_RUNNER = "core.test_runner.PoolerSafeTestRunner"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Kimlik doğrulama: e-posta ile giriş yapan özel kullanıcı modeli
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "display_name")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": limits.PASSWORD_MIN},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Testlerde hızlı (güvensiz) parola özeti: testler çok kullanıcı oluşturur, gerçek
# PBKDF2 her birinde ~0,5 sn harcar. Uygulamanın kendisi her zaman varsayılan güçlü özeti kullanır.
if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Dil ve saat dilimi
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

# Statik dosyalar: WhiteNoise doğrudan uygulama içinden sunar.
# USE_FINDERS sayesinde Vercel'de collectstatic/build adımı gerekmez (STATIC_ROOT bu yüzden yok).
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
WHITENOISE_USE_FINDERS = True

# Güvenlik ayarları (docs/callender.md bölüm 12.5)
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
DATA_UPLOAD_MAX_MEMORY_SIZE = 100_000  # 100 KB; formlarımız birkaç KB'ı geçmez

# Canlı ortam (Vercel HTTPS proxy arkasında çalışır)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31_536_000  # 1 yıl
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
