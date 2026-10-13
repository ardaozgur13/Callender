"""
Bağlam seçici: kullanıcı "Bireysel" ya da üyesi olduğu bir aile görünümündedir.
Seçim oturumda tutulur ve her istekte üyelik yeniden doğrulanır.
"""
from django.utils.functional import SimpleLazyObject

from .models import Family
from .permissions import owned_family_ids

SESSION_KEY = "active_family_id"


def get_active_family(request):
    """Seçili aile (kullanıcı hâlâ üyeyse); değilse None = Bireysel."""
    if not request.user.is_authenticated:
        return None
    if not hasattr(request, "_active_family"):
        family_id = request.session.get(SESSION_KEY)
        family = None
        if family_id:
            family = Family.objects.filter(pk=family_id, memberships__user=request.user).first()
            if family is None:
                request.session.pop(SESSION_KEY, None)  # Üyelik bitmiş, bireysele dön
        request._active_family = family
    return request._active_family


def set_active_family(request, family):
    request.session[SESSION_KEY] = family.pk if family else None
    request._active_family = family


def family_context(request):
    """Şablon bağlam işlemcisi: menüdeki bağlam seçici için."""
    if not request.user.is_authenticated:
        return {}
    return {
        "active_family": get_active_family(request),
        "my_families": Family.objects.filter(memberships__user=request.user).order_by("name"),
        # Şablonlarda düzenle/sil butonlarını göstermek için (yetki asıl olarak view'da kontrol edilir)
        "owned_family_ids": SimpleLazyObject(lambda: owned_family_ids(request.user)),
    }
