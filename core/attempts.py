"""
Deneme sınırı (ek paket olmadan). Son LOCKOUT dakika içinde MAX_ATTEMPTS başarısız deneme
yapılmış anahtar kilitlidir. Başarılı işlemde o anahtarın kayıtları silinir; eski kayıtlar
yeni bir başarısız deneme yazılırken tembel olarak temizlenir.
"""
from datetime import timedelta

from django.utils import timezone

from . import limits
from .models import AuthAttempt

RULES = {
    AuthAttempt.Kind.LOGIN: (limits.LOGIN_MAX_ATTEMPTS, limits.LOGIN_LOCKOUT_MINUTES),
    AuthAttempt.Kind.JOIN: (limits.JOIN_MAX_ATTEMPTS, limits.JOIN_LOCKOUT_MINUTES),
}


def _window_start(kind):
    _, minutes = RULES[kind]
    return timezone.now() - timedelta(minutes=minutes)


def is_locked(kind, key):
    max_attempts, _ = RULES[kind]
    recent = AuthAttempt.objects.filter(kind=kind, key=key, created_at__gte=_window_start(kind))
    return recent.count() >= max_attempts


def record_failure(kind, key):
    # Tembel temizlik: pencereden eski kayıtları sil
    AuthAttempt.objects.filter(kind=kind, created_at__lt=_window_start(kind)).delete()
    AuthAttempt.objects.create(kind=kind, key=key)


def clear(kind, key):
    AuthAttempt.objects.filter(kind=kind, key=key).delete()


def lockout_message(kind):
    _, minutes = RULES[kind]
    return f"Çok fazla hatalı deneme yapıldı. Lütfen {minutes} dakika sonra tekrar dene."
