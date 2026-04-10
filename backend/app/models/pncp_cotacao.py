from django.conf import settings
from django.db import models


class PncpCotacao(models.Model):
    """Ordem de pesquisa / cotação PNCP persistida no Django (fonte de verdade)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pncp_cotacoes",
    )
    prefeitura = models.ForeignKey(
        "app.Prefeitura",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pncp_cotacoes",
    )
    titulo = models.CharField(max_length=500)
    termo_busca = models.CharField(max_length=2000)
    modelo_cotacao = models.CharField(max_length=120, default="pesquisa_precos_padrao")
    status = models.CharField(max_length=32, default="aberta")
    filtros = models.JSONField(default=dict, blank=True)
    # Snapshot no momento da criação (cadastro não muda se o usuário alterar o perfil depois)
    criado_por_nome = models.CharField(max_length=240, blank=True, default="")
    criado_por_email = models.CharField(max_length=254, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["usuario", "-id"]),
        ]

    def __str__(self) -> str:
        return f"{self.titulo[:60]} (#{self.pk})"


class PncpCotacaoItem(models.Model):
    """Item de contratação vinculado a uma cotação PNCP."""

    cotacao = models.ForeignKey(
        PncpCotacao,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    numero_pncp = models.CharField(max_length=256, blank=True, default="")
    ano_compra = models.IntegerField(null=True, blank=True)
    sequencial_compra = models.IntegerField(null=True, blank=True)
    numero_item = models.CharField(max_length=64, blank=True, default="")
    descricao_item = models.TextField(blank=True, default="")
    quantidade = models.FloatField(null=True, blank=True)
    unidade_medida = models.CharField(max_length=64, blank=True, default="")
    valor_unitario = models.FloatField(null=True, blank=True)
    valor_total = models.FloatField(null=True, blank=True)
    orgao = models.CharField(max_length=512, blank=True, default="")
    municipio = models.CharField(max_length=256, blank=True, default="")
    uf = models.CharField(max_length=8, blank=True, default="")
    modalidade = models.CharField(max_length=256, blank=True, default="")
    source = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["cotacao", "-id"]),
        ]
