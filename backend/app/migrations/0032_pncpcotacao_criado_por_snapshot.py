from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0031_pncp_cotacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="pncpcotacao",
            name="criado_por_email",
            field=models.CharField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="pncpcotacao",
            name="criado_por_nome",
            field=models.CharField(blank=True, default="", max_length=240),
        ),
    ]
