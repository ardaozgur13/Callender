from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Ortak"

    def ready(self):
        from .db import enable_rls_on_public_tables

        # Her migrate sonunda yeni tablolarda da RLS açık olsun (bkz. core/db.py)
        post_migrate.connect(enable_rls_on_public_tables, dispatch_uid="core_enable_rls")
