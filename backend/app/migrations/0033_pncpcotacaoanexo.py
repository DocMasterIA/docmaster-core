from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0032_pncpcotacao_criado_por_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="PncpCotacaoAnexo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("arquivo_pdf", models.FileField(upload_to="pncp/cotacoes/anexos_fornecedor/")),
                ("nome_original", models.CharField(blank=True, default="", max_length=255)),
                ("tamanho_bytes", models.BigIntegerField(default=0)),
                ("content_type", models.CharField(blank=True, default="application/pdf", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cotacao",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anexo_fornecedor",
                        to="app.pncpcotacao",
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
    ]
