from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0034_pncpcotacaoitemcotacao"),
    ]

    operations = [
        migrations.CreateModel(
            name="PncpCotacaoAnexoArquivo",
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
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anexos_fornecedor_arquivos",
                        to="app.pncpcotacao",
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="pncpcotacaoanexoarquivo",
            index=models.Index(fields=["cotacao", "-id"], name="app_pncpcot_cotacao_336716_idx"),
        ),
    ]
