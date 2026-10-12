from django.conf import settings
from django.db import models

from core import limits


class Family(models.Model):
    name = models.CharField("aile adı", max_length=limits.FAMILY_NAME_MAX)
    invite_code = models.CharField("davet kodu", max_length=limits.INVITE_CODE_LENGTH, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_families",
        verbose_name="kurucu",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "aile"
        verbose_name_plural = "aileler"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FamilyMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Kurucu"
        MEMBER = "member", "Üye"

    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="memberships", verbose_name="aile")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="family_memberships", verbose_name="kullanıcı"
    )
    role = models.CharField("rol", max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField("katılma zamanı", auto_now_add=True)

    class Meta:
        verbose_name = "aile üyesi"
        verbose_name_plural = "aile üyeleri"
        ordering = ["joined_at", "pk"]
        constraints = [models.UniqueConstraint(fields=["family", "user"], name="unique_family_member")]

    def __str__(self):
        return f"{self.user} @ {self.family}"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER
