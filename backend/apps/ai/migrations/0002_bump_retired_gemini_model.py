"""Retire ``gemini-2.0-flash``.

Google removed the model server-side (404: "no longer available"), so any
workspace still pointing at it — or at the equally retired 1.5 models — is
broken until the row is updated. Bumps the field default and rewrites stale
rows in place.
"""

from django.db import migrations, models

RETIRED = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
REPLACEMENT = "gemini-3.6-flash"


def bump_stale_models(apps, schema_editor):
    AISettings = apps.get_model("ai", "AISettings")
    AISettings.objects.filter(provider="gemini", chat_model__in=RETIRED).update(
        chat_model=REPLACEMENT
    )


def noop_reverse(apps, schema_editor):
    """Irreversible in practice: the old models no longer exist upstream."""


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aisettings",
            name="chat_model",
            field=models.CharField(default="gemini-3.6-flash", max_length=128),
        ),
        migrations.RunPython(bump_stale_models, noop_reverse),
    ]
