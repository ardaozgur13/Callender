from django.shortcuts import render
from django.utils import timezone

from calendar_app import services as calendar_services


def home(request):
    """Ana sayfa (Bugün): bugünün takvim öğeleri. Buzdolabı ve ev işleri sonraki aşamalarda gelir."""
    today = timezone.localdate()
    return render(request, "core/home.html", {
        "active_nav": "home",
        "today": today,
        "occurrences": calendar_services.occurrences_on(request.user, today),
    })
