from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0028_prefeitura_estado_alter_template_related_subtopico"),
    ]

    operations = [
        migrations.CreateModel(
            name="SlotValueCatalog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("field_key", models.CharField(max_length=120, verbose_name="Chave do Campo")),
                ("value", models.TextField(verbose_name="Valor")),
                ("normalized_value", models.TextField(verbose_name="Valor Normalizado")),
                ("usage_count", models.PositiveIntegerField(default=1, verbose_name="Quantidade de Uso")),
                ("last_used_at", models.DateTimeField(auto_now=True, verbose_name="Último Uso")),
                ("is_active", models.BooleanField(default=True, verbose_name="Ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slot_values",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Catálogo de Valor de Slot",
                "verbose_name_plural": "Catálogo de Valores de Slot",
                "unique_together": {("owner", "field_key", "normalized_value")},
            },
        ),
        migrations.AddIndex(
            model_name="slotvaluecatalog",
            index=models.Index(
                fields=["owner", "field_key", "-usage_count", "-last_used_at"],
                name="slotcat_owner_field_idx",
            ),
        ),
    ]
