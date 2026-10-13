"""
Aile iş kuralları: kurma, kodla katılma, ayrılma, kurucu işlemleri.
Limitler burada, sunucu tarafında zorlanır (bkz. docs/callender.md bölüm 5-6).
"""
import secrets

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core import attempts, limits
from core.models import AuthAttempt

from .models import Family, FamilyMember


class FamilyError(Exception):
    """Kullanıcıya gösterilecek nazik bir mesaj taşıyan aile hatası."""


def generate_invite_code():
    """Benzersiz davet kodu: büyük harf + rakam, karışabilen 0/O/1/I hariç."""
    while True:
        code = "".join(secrets.choice(limits.INVITE_CODE_ALPHABET) for _ in range(limits.INVITE_CODE_LENGTH))
        if not Family.objects.filter(invite_code=code).exists():
            return code


def normalize_code(code):
    """Kullanıcının yazdığı kodu büyük harfe çevirir, boşluk ve tireleri atar."""
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def user_families(user):
    return Family.objects.filter(memberships__user=user).order_by("name")


def get_membership(user, family_id):
    """Kullanıcının o ailedeki üyeliği; üye değilse None."""
    return FamilyMember.objects.select_related("family").filter(user=user, family_id=family_id).first()


def _lock_user(user):
    get_user_model().objects.select_for_update().only("pk").get(pk=user.pk)


def _check_family_limit(user):
    if FamilyMember.objects.filter(user=user).count() >= limits.MAX_FAMILIES_PER_USER:
        raise FamilyError(f"En fazla {limits.MAX_FAMILIES_PER_USER} aileye üye olabilirsin.")


INVALID_CODE_MESSAGE = "Kod geçersiz. Kodu kontrol edip tekrar dener misin?"


def create_family(user, name):
    with transaction.atomic():
        _lock_user(user)
        _check_family_limit(user)
        # Kötüye kullanım önleme: bugün (yerel saatle) kurulan aile sayısı. Kuruluşlar ayrı kaydedilir;
        # aile sonradan silinse de sayılır, yoksa kur-sil döngüsüyle sınır delinirdi.
        day_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        created_today = AuthAttempt.objects.filter(
            kind=AuthAttempt.Kind.FAMILY_CREATE, key=str(user.pk), created_at__gte=day_start
        )
        if created_today.count() >= limits.FAMILY_CREATE_PER_DAY:
            raise FamilyError(f"Bir günde en fazla {limits.FAMILY_CREATE_PER_DAY} aile kurabilirsin. Yarın tekrar dene.")
        family = Family.objects.create(name=name, invite_code=generate_invite_code(), created_by=user)
        FamilyMember.objects.create(family=family, user=user, role=FamilyMember.Role.OWNER)
        AuthAttempt.objects.filter(kind=AuthAttempt.Kind.FAMILY_CREATE, created_at__lt=day_start).delete()
        AuthAttempt.objects.create(kind=AuthAttempt.Kind.FAMILY_CREATE, key=str(user.pk))
    return family


def join_family(user, code):
    """
    Kodla katılma. Yanlış kod denemeleri kullanıcı başına sınırlıdır (JOIN_MAX_ATTEMPTS).
    Kod yoksa da aile doluysa da aynı mesaj verilir; kodun geçerli olup olmadığı sızmaz.
    """
    key = str(user.pk)
    if attempts.is_locked(AuthAttempt.Kind.JOIN, key):
        raise FamilyError(attempts.lockout_message(AuthAttempt.Kind.JOIN))
    code = normalize_code(code)
    with transaction.atomic():
        _lock_user(user)
        _check_family_limit(user)
        family = Family.objects.select_for_update().filter(invite_code=code).first()
        if family and FamilyMember.objects.filter(family=family, user=user).exists():
            raise FamilyError(f"Zaten “{family.name}” ailesinin üyesisin.")
        if family and family.memberships.count() < limits.MAX_FAMILY_MEMBERS:
            FamilyMember.objects.create(family=family, user=user, role=FamilyMember.Role.MEMBER)
        else:
            family = None
    if family is None:
        # Deneme kaydı işlem dışında yazılır (hata ile birlikte geri alınmasın)
        attempts.record_failure(AuthAttempt.Kind.JOIN, key)
        raise FamilyError(INVALID_CODE_MESSAGE)
    attempts.clear(AuthAttempt.Kind.JOIN, key)
    return family


def leave_family(membership):
    """
    Üyeyi aileden çıkarır. Kurucu ayrılırsa en eski üye kurucu olur;
    kimse kalmazsa aile (ve aile kayıtları) silinir. Aile silindiyse True döner.
    """
    with transaction.atomic():
        family = Family.objects.select_for_update().get(pk=membership.family_id)
        was_owner = membership.is_owner
        membership.delete()
        _unassign_chores(membership.family_id, membership.user)
        remaining = family.memberships.order_by("joined_at", "pk")
        if not remaining.exists():
            family.delete()
            return True
        if was_owner:
            successor = remaining.first()
            successor.role = FamilyMember.Role.OWNER
            successor.save(update_fields=["role"])
    return False


def _unassign_chores(family_id, user):
    """Ayrılan/çıkarılan üyenin ev işleri 'herkes'e döner."""
    from home.services import unassign_member

    unassign_member(family_id, user)


def leave_all_families(user):
    """Hesap silinmeden önce: tüm ailelerden kurallara uygun şekilde ayrıl."""
    for membership in list(FamilyMember.objects.filter(user=user)):
        leave_family(membership)


def remove_member(owner_membership, member_id):
    if not owner_membership.is_owner:
        raise FamilyError("Bu işlemi sadece aile kurucusu yapabilir.")
    member_id = str(member_id or "")
    target = None
    if member_id.isdigit():
        target = FamilyMember.objects.filter(family_id=owner_membership.family_id, pk=member_id).first()
    if not target:
        raise FamilyError("Bu kişi ailede değil.")
    if target.pk == owner_membership.pk:
        raise FamilyError("Kendini çıkaramazsın; aileden ayrılmayı kullan.")
    target.delete()
    _unassign_chores(target.family_id, target.user)
    return target


def regenerate_code(owner_membership):
    if not owner_membership.is_owner:
        raise FamilyError("Bu işlemi sadece aile kurucusu yapabilir.")
    family = owner_membership.family
    family.invite_code = generate_invite_code()
    family.save(update_fields=["invite_code"])
    return family.invite_code


def delete_family(owner_membership):
    if not owner_membership.is_owner:
        raise FamilyError("Bu işlemi sadece aile kurucusu yapabilir.")
    owner_membership.family.delete()
