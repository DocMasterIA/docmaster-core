from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0035_pncpcotacaoanexoarquivo"),
    ]

    operations = [
        migrations.CreateModel(
            name="PncpFornecedorCadastro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo_pessoa", models.CharField(blank=True, default="", max_length=80)),
                ("cnpj", models.CharField(blank=True, default="", max_length=24)),
                ("razao_social", models.CharField(blank=True, default="", max_length=255)),
                ("tipo", models.CharField(blank=True, default="", max_length=120)),
                ("data_abertura", models.CharField(blank=True, default="", max_length=32)),
                ("porte", models.CharField(blank=True, default="", max_length=120)),
                ("nome_fantasia", models.CharField(blank=True, default="", max_length=255)),
                ("logradouro", models.CharField(blank=True, default="", max_length=255)),
                ("numero", models.CharField(blank=True, default="", max_length=64)),
                ("complemento", models.CharField(blank=True, default="", max_length=255)),
                ("cep", models.CharField(blank=True, default="", max_length=24)),
                ("bairro", models.CharField(blank=True, default="", max_length=120)),
                ("municipio", models.CharField(blank=True, default="", max_length=120)),
                ("uf", models.CharField(blank=True, default="", max_length=8)),
                ("email", models.CharField(blank=True, default="", max_length=255)),
                ("telefone", models.CharField(blank=True, default="", max_length=64)),
                ("situacao", models.CharField(blank=True, default="", max_length=120)),
                ("data_situacao", models.CharField(blank=True, default="", max_length=32)),
                ("motivo_situacao", models.CharField(blank=True, default="", max_length=255)),
                ("situacao_especial", models.CharField(blank=True, default="", max_length=255)),
                ("data_situacao_especial", models.CharField(blank=True, default="", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pncp_fornecedores_cadastrados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.AddIndex(
            model_name="pncpfornecedorcadastro",
            index=models.Index(fields=["usuario", "-id"], name="app_pncpforn_usuario_9ea161_idx"),
        ),
        migrations.AddIndex(
            model_name="pncpfornecedorcadastro",
            index=models.Index(fields=["usuario", "cnpj"], name="app_pncpforn_usuario_13db0a_idx"),
        ),
    ]
