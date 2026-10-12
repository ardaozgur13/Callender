from django.shortcuts import render
from django.utils import timezone

from calendar_app import services as calendar_services
from families.context import get_active_family
from fridge import services as fridge_services


def home(request):
    """Ana sayfa (Bugün): bugünün takvim öğeleri ve yaklaşan SKT'ler. Ev işleri sonraki aşamada gelir."""
    today = timezone.localdate()
    family = get_active_family(request)
    return render(request, "core/home.html", {
        "active_nav": "home",
        "today": today,
        "occurrences": calendar_services.occurrences_on(request.user, today, family),
        "expiring": fridge_services.expiring_items(request.user, family),
    })
