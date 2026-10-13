from django.contrib.auth.decorators import login_not_required
from django.shortcuts import render
from django.utils import timezone

from calendar_app import services as calendar_services
from families.context import get_active_family
from fridge import services as fridge_services
from home import services as home_services


def home(request):
    """Ana sayfa (Bugün): takvim, yaklaşan SKT'ler; aile seçiliyse ev durumu ve bugünün ev işleri."""
    today = timezone.localdate()
    family = get_active_family(request)
    context = {
        "active_nav": "home",
        "today": today,
        "occurrences": calendar_services.occurrences_on(request.user, today, family),
        "expiring": fridge_services.expiring_items(request.user, family),
    }
    if family is not None:
        context["statuses"] = home_services.get_statuses(family)
        context["today_chores"] = home_services.week_schedule(family, [today])[0]["entries"]
    return render(request, "core/home.html", context)


# ---------- Hukuki metinler (KVKK, bölüm 13.2) ----------
# Taslak metinlerdir; yayına almadan önce bir hukuk uzmanına okutulmalıdır.

LEGAL_PAGES = {
    "privacy_notice": ("KVKK aydınlatma metni", "legal/_privacy_notice.html"),
    "privacy_policy": ("Gizlilik politikası", "legal/_privacy_policy.html"),
    "terms": ("Kullanım koşulları", "legal/_terms.html"),
}


def _legal_page(request, key):
    title, body_template = LEGAL_PAGES[key]
    return render(request, "legal/page.html", {
        "page_title": title,
        "body_template": body_template,
        "updated_on": "13 Ekim 2026",
    })


@login_not_required
def privacy_notice(request):
    return _legal_page(request, "privacy_notice")


@login_not_required
def privacy_policy(request):
    return _legal_page(request, "privacy_policy")


@login_not_required
def terms(request):
    return _legal_page(request, "terms")
