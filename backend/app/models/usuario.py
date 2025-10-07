import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

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

def user_profile_photo_path(instance, filename):
    # salva sempre como 'profile_photos/{user_id}.ext'
    ext = filename.split('.')[-1]
    filename = f'{instance.id}.{ext}'
    return os.path.join('profile_photos', filename)


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

    profile_photo = models.ImageField(upload_to=user_profile_photo_path, null=True, blank=True, default='defaults/default_photo.png')
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # ao criar superuser, só pedirá email e senha

    def save(self, *args, **kwargs):
        # pegar instância antiga (se existir) para comparar nomes
        old = None
        if self.pk:
            try:
                old = User.objects.get(pk=self.pk)
            except User.DoesNotExist:
                old = None

        # se existe novo arquivo (ou foi removido via form)
        has_new_file = bool(self.profile_photo and getattr(self.profile_photo, "file", None))

        # se trocaram de arquivo (comparando nome) — delete o antigo via storage
        if old and old.profile_photo and (not self.profile_photo or old.profile_photo.name != self.profile_photo.name):
            try:
                # usa o storage do campo — funciona com S3, GCS, local, etc.
                old.profile_photo.delete(save=False)
            except Exception:
                # não falhar por causa da deleção
                pass

        # se houver um arquivo novo, redimensiona antes de salvar
        if has_new_file:
            try:
                img = Image.open(self.profile_photo)
                img = img.convert("RGB")
                img = img.resize((300, 300), Image.LANCZOS)

                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=95)
                # monte um nome que evita colisão (ex: id.jpg se tiver id, senão timestamp/nome)
                filename = f"{self.pk or 'tmp'}_{os.path.splitext(self.profile_photo.name)[0]}.jpg"
                self.profile_photo.save(filename, ContentFile(buffer.getvalue()), save=False)
            except Exception:
                # se redimensionamento falhar, não bloqueie o save (opcional: log)
                pass

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()