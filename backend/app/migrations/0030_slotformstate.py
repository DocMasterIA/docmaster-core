from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0029_slotvaluecatalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="SlotFormState",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slot_package_key", models.CharField(default="tr_dfd_generico", max_length=120, verbose_name="Pacote de Slots")),
                ("data", models.JSONField(default=dict, verbose_name="Dados do Formulário")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slot_form_states", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Estado do Formulário de Slots",
                "verbose_name_plural": "Estados do Formulário de Slots",
                "unique_together": {("owner", "slot_package_key")},
            },
        ),
        migrations.AddIndex(
            model_name="slotformstate",
            index=models.Index(fields=["owner", "slot_package_key"], name="slotstate_owner_pkg_idx"),
        ),
    ]
