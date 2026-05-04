from django.db import migrations, models


DEFAULT_MODULES = [
    "dispensa",
    "dispensa_eletronica",
    "pregao",
    "pregao_eletronico",
    "inexigibilidade",
    "etp",
    "analisador",
    "pesquisa",
    "contratos",
    "controle_interno",
    "impugnacao",
    "recurso",
    "usuario",
]


def fill_allowed_modules(apps, schema_editor):
    User = apps.get_model("app", "User")
    User.objects.filter(allowed_modules__isnull=True).update(allowed_modules=DEFAULT_MODULES)


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0036_pncpfornecedorcadastro"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="allowed_modules",
            field=models.JSONField(blank=True, default=list, verbose_name="Módulos permitidos"),
        ),
        migrations.RunPython(fill_allowed_modules, migrations.RunPython.noop),
    ]

