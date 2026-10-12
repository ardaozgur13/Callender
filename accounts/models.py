from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from core import limits


def normalize_email(email):
    """E-postayı tamamen küçük harfe çevirir ve baştaki/sondaki boşlukları atar."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    def create_user(self, email, display_name, password=None, **extra_fields):
        if not email:
            raise ValueError("E-posta zorunludur.")
        user = self.model(email=normalize_email(email), display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, display_name, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Girişte e-posta büyük/küçük harf duyarsız eşleşsin
        return self.get(email=normalize_email(email))


class User(AbstractBaseUser, PermissionsMixin):
    """E-posta ile giriş yapan Callender kullanıcısı (username alanı yok)."""

    email = models.EmailField("e-posta", unique=True)
    display_name = models.CharField(
        "isim",
        max_length=limits.USER_NAME_MAX,
        validators=[MinLengthValidator(limits.USER_NAME_MIN)],
    )
    is_active = models.BooleanField("aktif", default=True)
    is_staff = models.BooleanField("yönetici paneli erişimi", default=False)
    date_joined = models.DateTimeField("katılma tarihi", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"

    def __str__(self):
        return f"{self.display_name} <{self.email}>"

    def clean(self):
        super().clean()
        self.email = normalize_email(self.email)

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name
