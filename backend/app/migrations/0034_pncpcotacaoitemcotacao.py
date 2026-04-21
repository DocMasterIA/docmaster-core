from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0033_pncpcotacaoanexo"),
    ]

    operations = [
        migrations.CreateModel(
            name="PncpCotacaoItemCotacao",
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
                ("data_publicacao", models.CharField(blank=True, default="", max_length=64)),
                ("score_aprovacao", models.IntegerField(default=0)),
                ("confiabilidade", models.CharField(blank=True, default="", max_length=32)),
                ("risco", models.CharField(blank=True, default="", max_length=32)),
                ("status", models.CharField(blank=True, default="", max_length=32)),
                ("source", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cotacao",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cotacoes_itens",
                        to="app.pncpcotacao",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cotacoes",
                        to="app.pncpcotacaoitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.AddIndex(
            model_name="pncpcotacaoitemcotacao",
            index=models.Index(fields=["item", "-id"], name="app_pncpcot_item_id_9f7d15_idx"),
        ),
        migrations.AddIndex(
            model_name="pncpcotacaoitemcotacao",
            index=models.Index(fields=["cotacao", "-id"], name="app_pncpcot_cotacao_5f89c4_idx"),
        ),
    ]
