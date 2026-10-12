import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core import limits
from families.context import get_active_family

from . import services
from .forms import CalendarItemForm


WEEKDAY_NAMES = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
MIN_YEAR, MAX_YEAR = 1900, 2200


def _user_item(request, pk):
    """Kullanıcının erişebildiği öğe (kişisel ya da üyesi olduğu aileninki); değilse 404."""
    return get_object_or_404(services.accessible_items(request.user), pk=pk)


def _day_url(day):
    return reverse("calendar_day", args=[day.year, day.month, day.day])


def _safe_date(year, month, day=1):
    try:
        result = date(year, month, day)
    except ValueError:
        raise Http404("Geçersiz tarih")
    if not MIN_YEAR <= result.year <= MAX_YEAR:
        raise Http404("Geçersiz tarih")
    return result


def month_view(request, year=None, month=None):
    today = timezone.localdate()
    first = _safe_date(year, month) if year else today.replace(day=1)

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    by_date = services.occurrences_between(request.user, weeks[0][0], weeks[-1][-1], get_active_family(request))

    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)

    return render(request, "calendar_app/month.html", {
        "active_nav": "calendar",
        "month_start": first,
        "weekday_names": WEEKDAY_NAMES,
        "weeks": [
            [{"date": d, "in_month": d.month == first.month, "is_today": d == today,
              "occurrences": by_date.get(d, [])} for d in week]
            for week in weeks
        ],
        "prev_month": prev_month,
        "next_month": next_month,
        "today": today,
    })


def day_view(request, year, month, day):
    current = _safe_date(year, month, day)
    occurrences = services.occurrences_on(request.user, current, get_active_family(request))
    return render(request, "calendar_app/day.html", {
        "active_nav": "calendar",
        "day": current,
        "occurrences": occurrences,
        "today": timezone.localdate(),
        "prev_day": current - timedelta(days=1),
        "next_day": current + timedelta(days=1),
        "count": services.items_on_date_count(request.user, current),
        "max_items": limits.MAX_ITEMS_PER_DAY,
    })


def _save_form(request, form, success_message, family=None):
    """Formu servis üzerinden kaydeder; limit aşılırsa forma hata ekler."""
    item = form.save(commit=False)
    if item.pk is None:
        item.family = family  # Yeni öğe seçili bağlama (Bireysel ya da aile) eklenir
    try:
        services.save_item(request.user, item)
    except services.DailyLimitError as error:
        form.add_error("date", str(error))
        return None
    messages.success(request, success_message)
    return item


def item_create(request):
    initial = {}
    raw_date = request.GET.get("tarih")
    if raw_date:
        try:
            initial["date"] = date.fromisoformat(raw_date)
        except ValueError:
            pass
    initial.setdefault("date", timezone.localdate())

    form = CalendarItemForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        item = _save_form(request, form, "Kaydedildi 🌼", family=get_active_family(request))
        if item:
            return redirect(_day_url(item.date))
    return render(request, "calendar_app/item_form.html", {
        "active_nav": "calendar",
        "form": form,
        "is_edit": False,
        "back_url": _day_url(form.initial.get("date") or timezone.localdate()),
    })


def item_edit(request, pk):
    item = _user_item(request, pk)
    form = CalendarItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        saved = _save_form(request, form, "Güncellendi.")
        if saved:
            return redirect(_day_url(saved.date))
    return render(request, "calendar_app/item_form.html", {
        "active_nav": "calendar",
        "form": form,
        "item": item,
        "is_edit": True,
        "back_url": _day_url(item.date),
    })


@require_POST
def item_delete(request, pk):
    item = _user_item(request, pk)
    item.delete()
    messages.info(request, f"“{item.title}” silindi.")
    return redirect(_next_or_day(request, item.date))


@require_POST
def item_toggle_done(request, pk):
    item = _user_item(request, pk)
    if item.is_checkable:
        item.is_done = not item.is_done
        item.save(update_fields=["is_done", "updated_at"])
    return redirect(_next_or_day(request, item.date))


def _next_or_day(request, fallback_day):
    """Formdan gelen `next` sadece site içi bir yol ise kullanılır."""
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return _day_url(fallback_day)
