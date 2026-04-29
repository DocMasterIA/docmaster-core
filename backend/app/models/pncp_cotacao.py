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


class PncpCotacaoAnexo(models.Model):
    """Anexo PDF do fornecedor para composição do relatório final."""

    cotacao = models.OneToOneField(
        PncpCotacao,
        on_delete=models.CASCADE,
        related_name="anexo_fornecedor",
    )
    arquivo_pdf = models.FileField(upload_to="pncp/cotacoes/anexos_fornecedor/")
    nome_original = models.CharField(max_length=255, blank=True, default="")
    tamanho_bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True, default="application/pdf")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]


class PncpCotacaoAnexoArquivo(models.Model):
    """Anexos PDF múltiplos do fornecedor para composição do relatório final."""

    cotacao = models.ForeignKey(
        PncpCotacao,
        on_delete=models.CASCADE,
        related_name="anexos_fornecedor_arquivos",
    )
    arquivo_pdf = models.FileField(upload_to="pncp/cotacoes/anexos_fornecedor/")
    nome_original = models.CharField(max_length=255, blank=True, default="")
    tamanho_bytes = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True, default="application/pdf")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["cotacao", "-id"]),
        ]


class PncpFornecedorCadastro(models.Model):
    """Cadastro persistente de fornecedores para reutilização em cotações diretas."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pncp_fornecedores_cadastrados",
    )
    tipo_pessoa = models.CharField(max_length=80, blank=True, default="")
    cnpj = models.CharField(max_length=24, blank=True, default="")
    razao_social = models.CharField(max_length=255, blank=True, default="")
    tipo = models.CharField(max_length=120, blank=True, default="")
    data_abertura = models.CharField(max_length=32, blank=True, default="")
    porte = models.CharField(max_length=120, blank=True, default="")
    nome_fantasia = models.CharField(max_length=255, blank=True, default="")
    logradouro = models.CharField(max_length=255, blank=True, default="")
    numero = models.CharField(max_length=64, blank=True, default="")
    complemento = models.CharField(max_length=255, blank=True, default="")
    cep = models.CharField(max_length=24, blank=True, default="")
    bairro = models.CharField(max_length=120, blank=True, default="")
    municipio = models.CharField(max_length=120, blank=True, default="")
    uf = models.CharField(max_length=8, blank=True, default="")
    email = models.CharField(max_length=255, blank=True, default="")
    telefone = models.CharField(max_length=64, blank=True, default="")
    situacao = models.CharField(max_length=120, blank=True, default="")
    data_situacao = models.CharField(max_length=32, blank=True, default="")
    motivo_situacao = models.CharField(max_length=255, blank=True, default="")
    situacao_especial = models.CharField(max_length=255, blank=True, default="")
    data_situacao_especial = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["usuario", "-id"]),
            models.Index(fields=["usuario", "cnpj"]),
        ]


class PncpCotacaoItemCotacao(models.Model):
    """Cotação de preço coletada para um item manual da cotação."""

    cotacao = models.ForeignKey(
        PncpCotacao,
        on_delete=models.CASCADE,
        related_name="cotacoes_itens",
    )
    item = models.ForeignKey(
        PncpCotacaoItem,
        on_delete=models.CASCADE,
        related_name="cotacoes",
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
    data_publicacao = models.CharField(max_length=64, blank=True, default="")
    score_aprovacao = models.IntegerField(default=0)
    confiabilidade = models.CharField(max_length=32, blank=True, default="")
    risco = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=32, blank=True, default="")
    source = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["item", "-id"]),
            models.Index(fields=["cotacao", "-id"]),
        ]
