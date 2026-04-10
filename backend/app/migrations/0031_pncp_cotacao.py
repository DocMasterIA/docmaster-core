from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0030_slotformstate"),
    ]

    operations = [
        migrations.CreateModel(
            name="PncpCotacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=500)),
                ("termo_busca", models.CharField(max_length=2000)),
                ("modelo_cotacao", models.CharField(default="pesquisa_precos_padrao", max_length=120)),
                ("status", models.CharField(default="aberta", max_length=32)),
                ("filtros", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "prefeitura",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pncp_cotacoes",
                        to="app.prefeitura",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pncp_cotacoes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.CreateModel(
            name="PncpCotacaoItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero_pncp", models.CharField(blank=True, default="", max_length=256)),
                ("ano_compra", models.IntegerField(blank=True, null=True)),
                ("sequencial_compra", models.IntegerField(blank=True, null=True)),
                ("numero_item", models.CharField(blank=True, default="", max_length=64)),
                ("descricao_item", models.TextField(blank=True, default="")),
                ("quantidade", models.FloatField(blank=True, null=True)),
                ("unidade_medida", models.CharField(blank=True, default="", max_length=64)),
                ("valor_unitario", models.FloatField(blank=True, null=True)),
                ("valor_total", models.FloatField(blank=True, null=True)),
                ("orgao", models.CharField(blank=True, default="", max_length=512)),
                ("municipio", models.CharField(blank=True, default="", max_length=256)),
                ("uf", models.CharField(blank=True, default="", max_length=8)),
                ("modalidade", models.CharField(blank=True, default="", max_length=256)),
                ("source", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cotacao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens",
                        to="app.pncpcotacao",
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="pncpcotacao",
            index=models.Index(fields=["usuario", "-id"], name="pncp_cot_usuario_id_desc"),
        ),
        migrations.AddIndex(
            model_name="pncpcotacaoitem",
            index=models.Index(fields=["cotacao", "-id"], name="pncp_item_cotacao_id_desc"),
        ),
    ]
