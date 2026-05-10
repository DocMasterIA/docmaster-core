from django.db import migrations

# Mesmo conjunto que MODULE_ACCESS_CHOICES / default_allowed_modules (usuario.py).
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

_ALLOWED = frozenset(DEFAULT_MODULES)


def forwards(apps, schema_editor):
    """
    Utilizadores criados antes da 0037 podem ter allowed_modules = [] (default do JSONField)
    em vez de NULL, pelo que o RunPython da 0037 não os actualizou.

    Alinhar a BD ao comportamento de User.get_allowed_modules(): lista vazia, tipo inválido
    ou só chaves desconhecidas => conjunto completo (acesso implícito legado).
    """
    User = apps.get_model("app", "User")
    for user in User.objects.all().iterator(chunk_size=500):
        raw = user.allowed_modules
        if not isinstance(raw, list):
            User.objects.filter(pk=user.pk).update(allowed_modules=DEFAULT_MODULES)
            continue
        valid = [str(x).strip() for x in raw if str(x).strip() in _ALLOWED]
        valid = list(dict.fromkeys(valid))
        if not valid:
            User.objects.filter(pk=user.pk).update(allowed_modules=DEFAULT_MODULES)
        elif valid != raw:
            User.objects.filter(pk=user.pk).update(allowed_modules=valid)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0037_user_allowed_modules"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
