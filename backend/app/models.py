import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Usuários devem ter um e-mail")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # permite criar convites sem senha e definir depois
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa is_superuser=True")

        return self._create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        SERVIDOR = "SERVIDOR", "Servidor público"
        EMPRESA = "EMPRESA", "Empresa"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)

    role = models.CharField(max_length=16, choices=Roles.choices, default=Roles.EMPRESA)
    organization = models.CharField(max_length=160, blank=True)  # órgão/empresa
    # campos obrigatórios do Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # ao criar superuser, só pedirá email e senha

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

from django.conf import settings
import uuid

class Template(models.Model):
    """
    Template mestre: um arquivo .docx com placeholders Jinja ou HTML template.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='templates/docx/')  # .docx com placeholders
    preview_html = models.TextField(blank=True)
    required_fields = models.JSONField(default=list)  # lista de placeholder names obrigatórios
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Clause(models.Model):
    """
    Cláusulas padrões reutilizáveis.
    """
    name = models.CharField(max_length=150)
    content = models.TextField()
    tags = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name


class DocumentInstance(models.Model):
    """
    Documento gerado ou rascunho do usuário.
    """
    STATUS = (('draft','Rascunho'),('final','Finalizado'))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(Template, on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data = models.JSONField()  # map campo -> valor preenchido
    content_html = models.TextField(blank=True)  # rendered HTML preview
    file_docx = models.FileField(upload_to='documents/docx/', blank=True, null=True)
    file_pdf = models.FileField(upload_to='documents/pdf/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def __str__(self):
        return self.name

class Rule(models.Model):
    """
    Regra simples que mapeia uma condição (campo == valor) para snippets.
    Ex.: field_name='modalidade', match_value='concorrencia' -> snippets=[...]
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_name = models.CharField(max_length=80)  # ex: 'modalidade'
    match_value = models.CharField(max_length=180)  # ex: 'concorrencia' or '*' para default
    snippets = models.ManyToManyField(Snippet, blank=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.field_name} == {self.match_value}"
