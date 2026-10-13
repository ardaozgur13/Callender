from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core import limits
from families.context import get_active_family
from families.permissions import can_manage

from . import services
from .forms import FoodItemForm
from .models import ShelfLifeRule

SAFETY_NOTICE = (
    "Bu süreler genel önerilerdir. Ürün ambalajındaki üretici talimatı ve görünüm/koku kontrolü "
    "önceliklidir. Şüpheliysen at."
)


def _user_item(request, pk):
    """Kullanıcının erişebildiği ürün (kişisel ya da üyesi olduğu ailenin); değilse 404."""
    return get_object_or_404(services.accessible_items(request.user), pk=pk)


def _manageable_item(request, pk):
    """Düzenleme/silme için: ekleyen ya da aile kurucusu olma şartı (değilse 403).
    Tüketildi / Bugün açtım ortak buzdolabında her üyeye açıktır."""
    item = _user_item(request, pk)
    if not can_manage(request.user, item):
        raise PermissionDenied("Bu ürünü sadece ekleyen kişi ya da aile kurucusu değiştirebilir.")
    return item


def _rules_for_js():
    """Formdaki öneri listesi ve otomatik doldurma için kurallar."""
    return [
        {
            "name": rule.name_tr, "days": rule.opened_days, "storage": rule.storage,
            "source": rule.source, "note": rule.note,
        }
        for rule in ShelfLifeRule.objects.all()
    ]


def fridge_list(request):
    family = get_active_family(request)
    items = list(services.active_items(request.user, family))
    return render(request, "fridge/list.html", {
        "active_nav": "fridge",
        "items": items,
        "max_items": limits.MAX_FRIDGE_ITEMS_PER_FAMILY,
        "safety_notice": SAFETY_NOTICE,
    })


def _form_page(request, form, is_edit, item=None):
    return render(request, "fridge/form.html", {
        "active_nav": "fridge",
        "form": form,
        "is_edit": is_edit,
        "item": item,
        "rules": _rules_for_js(),
        "safety_notice": SAFETY_NOTICE,
    })


def food_create(request):
    form = FoodItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            item = services.add_item(request.user, form.save(commit=False), get_active_family(request))
        except services.FridgeLimitError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"{item.name} buzdolabına eklendi.")
            return redirect("fridge")
    return _form_page(request, form, is_edit=False)


def food_edit(request, pk):
    item = _manageable_item(request, pk)
    form = FoodItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Güncellendi.")
        return redirect("fridge")
    return _form_page(request, form, is_edit=True, item=item)


@require_POST
def food_consume(request, pk):
    item = _user_item(request, pk)
    services.mark_consumed(item)
    messages.success(request, f"{item.name} tüketildi olarak işaretlendi. Afiyet olsun!")
    # Bugün sayfasındaki yaklaşan SKT listesinden gelindiyse oraya dön
    return redirect("home" if request.POST.get("next") == "home" else "fridge")


@require_POST
def food_open_today(request, pk):
    item = _user_item(request, pk)
    services.mark_opened_today(item)
    messages.info(request, f"{item.name}: açılma tarihi bugün olarak kaydedildi.")
    return redirect("fridge")


@require_POST
def food_delete(request, pk):
    item = _manageable_item(request, pk)
    item.delete()
    messages.info(request, f"{item.name} silindi.")
    return redirect("fridge")
