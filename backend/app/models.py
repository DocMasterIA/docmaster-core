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

from django.db import models
from django.conf import settings
import uuid

class Template(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True, null=True, blank=True)
    file = models.FileField(upload_to='templates/docx/')
    created_at = models.DateTimeField(auto_now_add=True)

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