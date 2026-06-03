from django.db import models
import unicodedata
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from backend.defaults.secretarias import DEFAULT_SECRETARIAS

# Modelo principal de locatário (tenant) do sistema.
# Cada instância representa uma prefeitura e determina o escopo multi-tenant.
class Prefeitura(models.Model):

    class BrazilianStates(models.TextChoices):
        AC = "AC", _("Acre")
        AL = "AL", _("Alagoas")
        AP = "AP", _("Amapá")
        AM = "AM", _("Amazonas")
        BA = "BA", _("Bahia")
        CE = "CE", _("Ceará")
        DF = "DF", _("Distrito Federal")
        ES = "ES", _("Espírito Santo")
        GO = "GO", _("Goiás")
        MA = "MA", _("Maranhão")
        MT = "MT", _("Mato Grosso")
        MS = "MS", _("Mato Grosso do Sul")
        MG = "MG", _("Minas Gerais")
        PA = "PA", _("Pará")
        PB = "PB", _("Paraíba")
        PR = "PR", _("Paraná")
        PE = "PE", _("Pernambuco")
        PI = "PI", _("Piauí")
        RJ = "RJ", _("Rio de Janeiro")
        RN = "RN", _("Rio Grande do Norte")
        RS = "RS", _("Rio Grande do Sul")
        RO = "RO", _("Rondônia")
        RR = "RR", _("Roraima")
        SC = "SC", _("Santa Catarina")
        SP = "SP", _("São Paulo")
        SE = "SE", _("Sergipe")
        TO = "TO", _("Tocantins")

    # Nome legível do município (exibido no admin e telas)
    nome_municipio = models.CharField(
        "Nome do Município",
        max_length=40,
        help_text="Nome completo do município. Ex: São Bernardo do Campo"
    )

    estado = models.CharField(
        max_length=30,
        choices=BrazilianStates.choices,
        blank=True,
        null=True
    )
    
    # Slug/URL canônica usada na rota multi-tenant (gerada no save)
    url = models.CharField(
        "URL do Município",
        max_length=40,
        unique=True,
        editable=False,
        help_text="Gerado automaticamente a partir do nome do município (ex: sao_bernardo_do_campo)"
    )
    # Limite de usuários vinculados a esta prefeitura (usado em validações atômicas)
    numero_usuarios_permitidos = models.IntegerField(
        "Número de Usuários Permitidos",
        help_text="Quantidade máxima de usuários autorizados para esta prefeitura"
    )


    class Meta:
        verbose_name = "Prefeitura"
        verbose_name_plural = "Prefeituras"
        ordering = ["nome_municipio"]

    def __str__(self):
        return self.nome_municipio

    @staticmethod
    def _strip_prefeitura_prefix(nome: str) -> str:
        """Admin e imports: guarda só o município (ex. Itajá), sem «Prefeitura de …»."""
        nome = (nome or "").strip()
        for prefix in (
            "Prefeitura Municipal de ",
            "Prefeitura Municipal da ",
            "Prefeitura de ",
            "Prefeitura da ",
        ):
            if nome.casefold().startswith(prefix.casefold()):
                return nome[len(prefix) :].strip()
        return nome

    # Gera/atualiza o slug `url` a partir do nome do município.
    # Remove acentuação, espaços e normaliza para padrão seguro de URL.
    def save(self, *args, **kwargs):
        self.nome_municipio = self._strip_prefeitura_prefix(self.nome_municipio)
        # Normaliza (remove acentos e espaços)
        nome = unicodedata.normalize("NFKD", self.nome_municipio)
        nome = nome.encode("ASCII", "ignore").decode("ASCII")
        nome = nome.lower().replace(" ", "_")

        # Garante formato seguro
        self.url = nome.strip("_").replace("__", "_")

        super().save(*args, **kwargs)

    # Cria secretarias padrão para a prefeitura a partir de `DEFAULT_SECRETARIAS`.
    # Usa transação atômica; ignora/cria conforme existência anterior (case-insensitive).
    def create_default_secretarias(self):
        from django.db import transaction, IntegrityError
        default = DEFAULT_SECRETARIAS
        created = []
        skipped = []
        

        with transaction.atomic():
            for item in default:
                nome = item.get("nome")
                descricao = item.get("descricao", "")

                qs = Secretaria.objects.filter(prefeitura=self, nome__iexact=nome)
                if qs.exists():
                    skipped.append(nome)
                    continue
                try:
                    s = Secretaria.objects.create(prefeitura=self, nome=nome, descricao=descricao)
                    created.append(s)
                except IntegrityError:
                    skipped.append(nome)
        return created, skipped
    
# Tipos globais de secretarias, reutilizáveis entre prefeituras.
class SecretariaTipo(models.Model):
    nome = models.CharField(max_length=70, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome
    
# Secretaria pertencente a uma prefeitura específica.
class Secretaria(models.Model):
    prefeitura = models.ForeignKey(
        "app.Prefeitura",
        on_delete=models.CASCADE,
        related_name="secretarias",
        verbose_name="Prefeitura"
    )
    nome = models.CharField(
        max_length=70,
        verbose_name="Nome da Secretaria"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição ou observações"
    )

    tipo = models.ForeignKey(SecretariaTipo, on_delete=models.PROTECT, related_name="secretarias", blank=True, null=True)


    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"
        unique_together = ("prefeitura", "nome")
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.prefeitura.nome_municipio})"

    # Validação para impedir nomes duplicados de secretaria dentro da mesma prefeitura.
    def clean(self):
        # Garante que não exista secretaria duplicada na mesma prefeitura
        qs = Secretaria.objects.filter(prefeitura=self.prefeitura, nome__iexact=self.nome)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"nome": "Já existe uma secretaria com este nome nesta prefeitura."})

# Subtópicos categóricos vinculados ao tipo de secretaria (catálogo global).
class SubtopicoSecretaria(models.Model):
    tipo_secretaria = models.ForeignKey(SecretariaTipo, on_delete=models.CASCADE, related_name="subtopicos", blank=True, null=True)

    nome = models.CharField(
        max_length=30,
        verbose_name="Nome do Subtópico"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição do Subtópico"
    )

    class Meta:
        verbose_name = "Subtópico de Secretaria"
        verbose_name_plural = "Subtópicos de Secretarias"
        unique_together = ("tipo_secretaria", "nome")
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.tipo_secretaria.nome})"


