from django.db import models
from django.conf import settings
import unicodedata
from django.core.exceptions import ValidationError

class Prefeitura(models.Model):
    nome_municipio = models.CharField(
        "Nome do Município",
        max_length=40,
        help_text="Nome completo do município. Ex: São Bernardo do Campo"
    )
    url = models.CharField(
        "URL do Município",
        max_length=40,
        unique=True,
        editable=False,
        help_text="Gerado automaticamente a partir do nome do município (ex: sao_bernardo_do_campo)"
    )
    numero_usuarios_permitidos = models.IntegerField(
        "Número de Usuários Permitidos",
        help_text="Quantidade máxima de usuários autorizados para esta prefeitura"
    )

    

    class Meta:
        verbose_name = "Prefeitura"
        verbose_name_plural = "Prefeituras"
        ordering = ["nome_municipio"]

    def __str__(self):
        return f"Prefeitura de {self.nome_municipio}"

    def save(self, *args, **kwargs):
        # Normaliza (remove acentos e espaços)
        nome = unicodedata.normalize("NFKD", self.nome_municipio)
        nome = nome.encode("ASCII", "ignore").decode("ASCII")
        nome = nome.lower().replace(" ", "_")

        # Garante formato seguro
        self.url = nome.strip("_").replace("__", "_")

        super().save(*args, **kwargs)

    def create_default_secretarias(self, nomes=None):
        """
        Cria secretarias padrão para esta prefeitura.
        nomes: iterable de strings. Se None, usa DEFAULT_SECRETARIAS do settings.
        Retorna (created_list, skipped_list)
        """
        from django.conf import settings
        from django.db import transaction, IntegrityError
        default = nomes if nomes is not None else getattr(settings, "DEFAULT_SECRETARIAS", [])
        created = []
        skipped = []

        with transaction.atomic():
            for nome in default:
                qs = Secretaria.objects.filter(prefeitura=self, nome__iexact=nome)
                if qs.exists():
                    skipped.append(nome)
                    continue
                try:
                    s = Secretaria.objects.create(prefeitura=self, nome=nome, descricao=nome.descricao)
                    created.append(s)
                except IntegrityError:
                    skipped.append(nome)
        return created, skipped
    

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

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"
        unique_together = ("prefeitura", "nome")
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.prefeitura.nome_municipio})"

    def clean(self):
        # Garante que não exista secretaria duplicada na mesma prefeitura
        qs = Secretaria.objects.filter(prefeitura=self.prefeitura, nome__iexact=self.nome)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"nome": "Já existe uma secretaria com este nome nesta prefeitura."})

class SubtopicoSecretaria(models.Model):
    secretaria = models.ForeignKey(
        Secretaria,
        on_delete=models.CASCADE,
        related_name="subtopicos",
        verbose_name="Secretaria"
    )
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
        unique_together = ("secretaria", "nome")
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.secretaria.nome})"

    def clean(self):
        qs = SubtopicoSecretaria.objects.filter(secretaria=self.secretaria, nome__iexact=self.nome)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"nome": "Já existe um subtopico com este nome nesta secretaria."})
