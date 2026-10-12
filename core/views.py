from django.shortcuts import render


def home(request):
    """Ana sayfa (Bugün). Şimdilik boş durum gösterir; içerik sonraki aşamalarda gelir."""
    return render(request, "core/home.html", {"active_nav": "home"})
