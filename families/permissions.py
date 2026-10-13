"""
Aile içi düzenleme yetkisi (docs/callender.md bölüm 6): üyeler kendi eklediklerini düzenler/siler,
kurucu ailedeki her şeyi yönetir. Görme yetkisi ayrıdır; o `for_user()` kapsamıyla sağlanır.
"""
from .models import FamilyMember


def owned_family_ids(user):
    """Kullanıcının kurucusu olduğu ailelerin id'leri."""
    return set(
        FamilyMember.objects.filter(user=user, role=FamilyMember.Role.OWNER).values_list("family_id", flat=True)
    )


def can_manage(user, obj):
    """
    `owner` ve `family` alanı olan bir nesneyi (takvim öğesi, gıda) düzenleyip silebilir mi?
    Kişisel nesne: sadece sahibi. Aile nesnesi: ekleyen ya da aile kurucusu
    (ekleyen hesabını sildiyse sadece kurucu).
    """
    if obj.family_id is None:
        return obj.owner_id == user.pk
    if obj.owner_id is not None and obj.owner_id == user.pk:
        return True
    return FamilyMember.objects.filter(
        family_id=obj.family_id, user=user, role=FamilyMember.Role.OWNER
    ).exists()
