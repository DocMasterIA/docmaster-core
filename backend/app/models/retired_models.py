# modelos em desuso

from django.db import models
import uuid

class Clause(models.Model):
    """
    Cláusulas padrões reutilizáveis.
    """
    name = models.CharField(max_length=150)
    content = models.TextField()
    tags = models.JSONField(default=list, blank=True)  # lista de tags para busca/organização

    def __str__(self):
        return self.name

class Snippet(models.Model):
    """
    Bloco de texto reutilizável (cláusula). Conteúdo com placeholders Jinja.
    """
    KEY_AREAS = [
        ('intro','Introdução'),
        ('clause','Cláusula'),
        ('conclusion','Conclusão'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    area = models.CharField(max_length=40, choices=KEY_AREAS, default='clause')
    slug = models.SlugField(unique=True)
    content = models.TextField(help_text="Use placeholders tipo {{ objeto }}, {{ orgao }}, {{ modalidade_label }}")
    tags = models.JSONField(default=list, blank=True)  # ajuda na busca
    active = models.BooleanField(default=True)
    order = models.IntegerField(default=100)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Rule(models.Model):
    """
    Regra simples que mapeia uma condição (campo == valor) para snippets.
    Ex.: field_name='modalidade', match_value='concorrencia' -> snippets=[...]
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_name = models.CharField(max_length=80)  # ex: 'modalidade'
    match_value = models.CharField(max_length=180)  # ex: 'concorrencia' ou '*' para default
    snippets = models.ManyToManyField(Snippet, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.field_name} == {self.match_value}"
