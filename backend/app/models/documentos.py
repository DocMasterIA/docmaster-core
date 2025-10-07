from django.db import models
from django.conf import settings
import uuid
from backend.app.services.preview import generate_docx_preview_pdf, generate_docx_preview
from django.core.validators import MaxValueValidator, MinValueValidator

class TemplateTag(models.Model):
    tag = models.CharField(max_length=20)

class Template(models.Model):
    class RolesAccess(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        SERVIDOR = "SERVIDOR", "Servidor público"
        EMPRESA = "EMPRESA", "Empresa"
        TODOS = "TODOS", "Todos"


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, null=True, blank=True)
    file = models.FileField(upload_to='templates/docx/')
    preview_image = models.ImageField(upload_to="previews/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    preview_pdf = models.FileField(upload_to='templates/previews_pdf/', null=True, blank=True)
    role_can_access = models.CharField(max_length=16, choices=RolesAccess.choices, default=RolesAccess.TODOS)
    template_tag = models.ForeignKey(
        TemplateTag,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # salva o modelo primeiro
        # se ainda não tem preview_pdf, gera automaticamente
        if self.file and not self.preview_pdf:
            generate_docx_preview_pdf(self)
        if self.file and not self.preview_image:
            generate_docx_preview(self)


class TemplateSchema(models.Model):
    """
    Manifesto/mapeamento gerado pela IA (ou manual) para um Template.
    schema: lista de campos com block indices ou token strategy
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.OneToOneField(Template, on_delete=models.CASCADE, related_name='schema')
    strategy = models.CharField(max_length=32, choices=(('tokens','tokens'),('index','index')), default='index')
    schema = models.JSONField()  # lista de fields: [{key,label,block_indices,type,required}]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Schema {self.template.name}"

class SchemaAudit(models.Model):
    schema = models.ForeignKey(TemplateSchema, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)



class DocumentInstance(models.Model):
    """
    Documento gerado ou rascunho do usuário.
    """
    STATUS_CHOICES = (
        ('draft','Rascunho'),
        ('final','Finalizado'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(Template, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)  # mapeamento campo -> valor preenchido
    content_html = models.TextField(blank=True)  # preview HTML renderizado
    file_docx = models.FileField(upload_to='documents/docx/', blank=True, null=True)
    file_pdf = models.FileField(upload_to='documents/pdf/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.template.name} ({self.owner.email})"