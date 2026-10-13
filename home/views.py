from datetime import date, timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core import limits
from families.context import get_active_family

from . import services
from .forms import ChoreForm


def _parse_date(raw, default):
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError):
        return default


def _home_url(week_of=None):
    url = reverse("home_page")
    return f"{url}?hafta={week_of.isoformat()}" if week_of else url


def home_page(request):
    """Ev: bulaşık/çamaşır durum kartları ve haftalık ev işleri (sadece aile görünümünde)."""
    family = get_active_family(request)
    if family is None:
        return render(request, "home/no_family.html", {"active_nav": "home_chores"})

    today = timezone.localdate()
    days = services.week_days(_parse_date(request.GET.get("hafta"), today))
    return render(request, "home/home.html", {
        "active_nav": "home_chores",
        "statuses": services.get_statuses(family),
        "week": services.week_schedule(family, days),
        "week_start": days[0],
        "week_end": days[-1],
        "prev_week": days[0] - timedelta(days=7),
        "next_week": days[0] + timedelta(days=7),
        "is_current_week": days[0] <= today <= days[-1],
        "today": today,
        "chores": services.family_chores(family),
        "max_chores": limits.MAX_CHORES_PER_FAMILY,
    })


def _family_or_redirect(request):
    family = get_active_family(request)
    if family is None:
        messages.info(request, "Ev işleri aile içindir; önce üstten bir aile seç.")
    return family


def chore_create(request):
    family = _family_or_redirect(request)
    if family is None:
        return redirect("home_page")
    form = ChoreForm(request.POST or None, family=family)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_chore(form.save(commit=False), family)
        except services.HomeError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Ev işi eklendi.")
            return redirect("home_page")
    return render(request, "home/chore_form.html", {"active_nav": "home_chores", "form": form, "is_edit": False})


def _user_chore(request, pk):
    """Kullanıcının üyesi olduğu ailenin işi; değilse 404."""
    return get_object_or_404(services.accessible_chores(request.user).select_related("family"), pk=pk)


def chore_edit(request, pk):
    chore = _user_chore(request, pk)
    form = ChoreForm(request.POST or None, instance=chore, family=chore.family)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_chore(form.save(commit=False), chore.family)
        except services.HomeError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, "Güncellendi.")
            return redirect("home_page")
    return render(request, "home/chore_form.html", {
        "active_nav": "home_chores", "form": form, "is_edit": True, "chore": chore,
    })


@require_POST
def chore_delete(request, pk):
    chore = _user_chore(request, pk)
    chore.delete()
    messages.info(request, f"“{chore.title}” silindi.")
    return redirect("home_page")


@require_POST
def chore_toggle(request, pk):
    chore = _user_chore(request, pk)
    day = _parse_date(request.POST.get("date"), timezone.localdate())
    try:
        done = services.toggle_done(chore, day, request.user)
    except services.HomeError as error:
        messages.error(request, str(error))
    else:
        if done:
            messages.success(request, f"“{chore.title}” yapıldı. Eline sağlık! 🌿")
    if request.POST.get("next") == "home":
        return redirect("home")
    # İşaretlenen günün haftasına geri dön
    return redirect(_home_url(services.week_days(day)[0]))


@require_POST
def status_change(request, kind):
    family = get_active_family(request)
    if family is None:
        messages.info(request, "Ev durumu aile içindir; önce üstten bir aile seç.")
        return redirect("home_page")
    try:
        card = services.change_status(
            family, kind, request.user,
            expected=request.POST.get("expected"),
            new_status=request.POST.get("status") or None,
        )
    except services.HomeError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"{card.get_kind_display()}: {card.status_label}")
    return redirect("home" if request.POST.get("next") == "home" else "home_page")
