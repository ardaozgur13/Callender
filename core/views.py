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
