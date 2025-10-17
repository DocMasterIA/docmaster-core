from django.db import models
from django.conf import settings
import unicodedata

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

class Secretaria(models.Model):
    prefeitura = models.ForeignKey(Prefeitura, on_delete=models.CASCADE)
    nome_prefeitura = models.CharField(max_length="70")
    

class SubtopicoSecretaria(models.Model):
    secretaria = models.ForeignKey(Secretaria, on_delete=models.CASCADE)
    nome_subtopico = models.CharField(max_length=30)