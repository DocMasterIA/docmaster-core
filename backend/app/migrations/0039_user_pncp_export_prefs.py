from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0038_fill_legacy_empty_allowed_modules"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="pncp_export_prefs",
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name="Preferências de exportação PNCP",
            ),
        ),
    ]
