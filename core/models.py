from django.db import models


class AuthAttempt(models.Model):
    """
    Sınırlanan olay kaydı (docs/callender.md bölüm 7 ve 12.4): başarısız giriş, başarısız davet kodu
    denemesi ve aile kurma. Anahtar IP'ye değil hesaba bağlıdır: giriş için küçük harfli e-posta,
    diğerleri için kullanıcı id'si. Aile kurma kaydı aile silinse de kalır (günlük sınır delinmesin).
    """

    class Kind(models.TextChoices):
        LOGIN = "login", "Giriş"
        JOIN = "join", "Aileye katılma"
        FAMILY_CREATE = "create", "Aile kurma"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    key = models.CharField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "sınırlı olay kaydı"
        verbose_name_plural = "sınırlı olay kayıtları"
        indexes = [models.Index(fields=["kind", "key", "created_at"])]
