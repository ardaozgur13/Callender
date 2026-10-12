from django.db import migrations

from fridge.seed_shelf_life import SHELF_LIFE_RULES, load_rules


def seed(apps, schema_editor):
    load_rules(apps.get_model("fridge", "ShelfLifeRule"))


def unseed(apps, schema_editor):
    ShelfLifeRule = apps.get_model("fridge", "ShelfLifeRule")
    ShelfLifeRule.objects.filter(key__in=[row[0] for row in SHELF_LIFE_RULES]).delete()


class Migration(migrations.Migration):
    """Başlangıç raf ömrü önerilerini yükler (docs/callender.md bölüm 8)."""

    dependencies = [
        ("fridge", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
