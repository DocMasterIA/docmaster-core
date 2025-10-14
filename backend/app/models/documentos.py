from django.db import models
from django.conf import settings
import uuid
from backend.app.services.preview import generate_docx_preview_pdf, generate_docx_preview
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _


class TemplateTag(models.Model):
    tag = models.CharField(_("Tag"), max_length=20)

    class Meta:
        verbose_name = _("Tag de Template")
        verbose_name_plural = _("Tags de Template")


class Template(models.Model):
    class RolesAccess(models.TextChoices):
        ADMIN = "ADMIN", _("Administrador")
        SERVIDOR = "SERVIDOR", _("Servidor público")
        EMPRESA = "EMPRESA", _("Empresa")
        TODOS = "TODOS", _("Todos")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Nome"), max_length=180)
    slug = models.SlugField(_("Slug"), unique=True, null=True, blank=True)
    file = models.FileField(_("Arquivo DOCX"), upload_to='templates/docx/')
    preview_image = models.ImageField(_("Imagem de Preview"), upload_to="previews/", null=True, blank=True)
    created_at = models.DateTimeField(_("Data de Criação"), auto_now_add=True)
    preview_pdf = models.FileField(_("PDF de Preview"), upload_to='templates/previews_pdf/', null=True, blank=True)
    role_can_access = models.CharField(_("Acesso"), max_length=16, choices=RolesAccess.choices, default=RolesAccess.TODOS)
    template_tag = models.ForeignKey(
        TemplateTag,
        verbose_name=_("Tag do Template"),
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Documento Base")
        verbose_name_plural = _("Documentos Base")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.file and not self.preview_pdf:
            generate_docx_preview_pdf(self)
        if self.file and not self.preview_image:
            generate_docx_preview(self)

    def __str__(self):
        # Se tiver slug, mostra ele; senão, mostra o nome
        return self.slug


class TemplateSchema(models.Model):
    """
    Manifesto/mapeamento gerado pela IA (ou manual) para um Template.
    schema: lista de campos com block indices ou token strategy
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.OneToOneField(
        Template, verbose_name=_("Template"), on_delete=models.CASCADE, related_name='schema'
    )
    strategy = models.CharField(
        _("Estratégia"),
        max_length=32,
        choices=(('tokens', _("Tokens")), ('index', _("Índice"))),
        default='index'
    )
    schema = models.JSONField(_("Schema"))  # lista de fields: [{key,label,block_indices,type,required}]
    created_at = models.DateTimeField(_("Data de Criação"), auto_now_add=True)

    class Meta:
        verbose_name = _("Schema I.A de Documento Base")
        verbose_name_plural = _("Schemas I.A de Documentos Base")

    def __str__(self):
        return f"Schema {self.template.name}"


class SchemaAudit(models.Model):
    schema = models.ForeignKey(
        TemplateSchema, verbose_name=_("Schema"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Usuário"), on_delete=models.SET_NULL, null=True
    )
    payload = models.JSONField(_("Payload"))
    created_at = models.DateTimeField(_("Data de Criação"), auto_now_add=True)

    class Meta:
        verbose_name = _("Auditoria de Schema I.A")
        verbose_name_plural = _("Auditorias de Schema I.A")


class DocumentInstance(models.Model):
    """
    Documento gerado ou rascunho do usuário.
    """
    STATUS_CHOICES = (
        ('draft', _("Rascunho")),
        ('final', _("Finalizado")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(Template, verbose_name=_("Template"), on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Proprietário"), on_delete=models.CASCADE)
    prefeitura_owner = models.ForeignKey(
        "app.Prefeitura",                             # << referência em string para evitar import circular
        verbose_name=_("Prefeitura proprietária"),
        on_delete=models.CASCADE,
        related_name="documentos",
        null=True,                                    # opcionalmente permitir nulo até popular
        blank=True
    )
    data = models.JSONField(_("Dados"), default=dict)  # mapeamento campo -> valor preenchido
    content_html = models.TextField(_("Conteúdo HTML"), blank=True)  # preview HTML renderizado
    file_docx = models.FileField(_("Arquivo DOCX"), upload_to='documents/docx/', blank=True, null=True)
    file_pdf = models.FileField(_("Arquivo PDF"), upload_to='documents/pdf/', blank=True, null=True)
    status = models.CharField(_("Status"), max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(_("Data de Criação"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Data de Atualização"), auto_now=True)

    class Meta:
        verbose_name = _("Documento")
        verbose_name_plural = _("Documentos")

    def save(self, *args, **kwargs):
        # Se quiser preencher automaticamente pela prefeitura do owner (se existir)
        if not self.prefeitura_owner and getattr(self, "owner", None) and getattr(self.owner, "prefeitura", None):
            self.prefeitura_owner = self.owner.prefeitura
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template.name} ({self.owner.email})"
