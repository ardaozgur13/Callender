from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core import limits

from . import services
from .context import SESSION_KEY, set_active_family
from .forms import FamilyNameForm, JoinFamilyForm
from .models import FamilyMember


def _membership_or_404(request, family_id):
    """Kullanıcının o ailedeki üyeliği; üye değilse 404 (ailenin varlığı bile sızmasın)."""
    membership = services.get_membership(request.user, family_id)
    if membership is None:
        raise Http404("Aile bulunamadı")
    return membership


def family_list(request):
    create_form = FamilyNameForm(prefix="create")
    join_form = JoinFamilyForm(prefix="join")

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "create":
                create_form = FamilyNameForm(request.POST, prefix="create")
                if create_form.is_valid():
                    family = services.create_family(request.user, create_form.cleaned_data["name"])
                    set_active_family(request, family)
                    messages.success(request, f"“{family.name}” ailesi kuruldu. Davet kodunu paylaşabilirsin 🌼")
                    return redirect("family_detail", family.pk)
            elif action == "join":
                join_form = JoinFamilyForm(request.POST, prefix="join")
                if join_form.is_valid():
                    family = services.join_family(request.user, join_form.cleaned_data["code"])
                    set_active_family(request, family)
                    messages.success(request, f"“{family.name}” ailesine katıldın. Hoş geldin!")
                    return redirect("family_detail", family.pk)
        except services.FamilyError as error:
            (create_form if action == "create" else join_form).add_error(None, str(error))

    memberships = FamilyMember.objects.filter(user=request.user).select_related("family").order_by("family__name")
    return render(request, "families/list.html", {
        "active_nav": "family",
        "memberships": memberships,
        "create_form": create_form,
        "join_form": join_form,
        "can_add": memberships.count() < limits.MAX_FAMILIES_PER_USER,
        "max_families": limits.MAX_FAMILIES_PER_USER,
    })


def family_detail(request, family_id):
    membership = _membership_or_404(request, family_id)
    family = membership.family
    rename_form = FamilyNameForm(instance=family, prefix="rename")

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "rename" and membership.is_owner:
                rename_form = FamilyNameForm(request.POST, instance=family, prefix="rename")
                if rename_form.is_valid():
                    rename_form.save()
                    messages.success(request, "Aile adı güncellendi.")
                    return redirect("family_detail", family.pk)
            elif action == "regenerate":
                services.regenerate_code(membership)
                messages.success(request, "Yeni davet kodu oluşturuldu; eski kod artık geçersiz.")
                return redirect("family_detail", family.pk)
            elif action == "remove":
                removed = services.remove_member(membership, request.POST.get("member_id"))
                messages.info(request, f"{removed.user.display_name} aileden çıkarıldı.")
                return redirect("family_detail", family.pk)
            elif action == "rename":
                raise services.FamilyError("Bu işlemi sadece aile kurucusu yapabilir.")
        except services.FamilyError as error:
            messages.error(request, str(error))
            return redirect("family_detail", family.pk)

    members = family.memberships.select_related("user").order_by("joined_at", "pk")
    return render(request, "families/detail.html", {
        "active_nav": "family",
        "family": family,
        "membership": membership,
        "members": members,
        "rename_form": rename_form,
        "max_members": limits.MAX_FAMILY_MEMBERS,
    })


@require_POST
def family_leave(request, family_id):
    membership = _membership_or_404(request, family_id)
    name = membership.family.name
    deleted = services.leave_family(membership)
    if request.session.get(SESSION_KEY) == family_id:
        set_active_family(request, None)
    if deleted:
        messages.info(request, f"“{name}” ailesinden ayrıldın. Son üye sen olduğun için aile silindi.")
    else:
        messages.info(request, f"“{name}” ailesinden ayrıldın.")
    return redirect("family_list")


@require_POST
def family_delete(request, family_id):
    membership = _membership_or_404(request, family_id)
    name = membership.family.name
    try:
        services.delete_family(membership)
    except services.FamilyError as error:
        messages.error(request, str(error))
        return redirect("family_detail", family_id)
    set_active_family(request, None)
    messages.info(request, f"“{name}” ailesi silindi.")
    return redirect("family_list")


@require_POST
def switch_context(request):
    """Bağlam seçici: boş değer = Bireysel, aksi halde üyesi olunan bir aile."""
    family_id = request.POST.get("family") or None
    family = None
    if family_id:
        membership = services.get_membership(request.user, family_id) if family_id.isdigit() else None
        if membership is None:
            messages.error(request, "Bu aileye erişimin yok.")
        else:
            family = membership.family
    set_active_family(request, family)

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    return redirect(next_url)
