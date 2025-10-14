import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("Usuários devem ter um e-mail"))
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
            raise ValueError(_("Superusuário precisa is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superusuário precisa is_superuser=True"))

        return self._create_user(email, password, **extra_fields)


def user_profile_photo_path(instance, filename):
    # salva sempre como 'profile_photos/{user_id}.ext'
    ext = filename.split('.')[-1]
    filename = f'{instance.id}.{ext}'
    return os.path.join('profile_photos', filename)

def profile_photo_filename(pk: int) -> str:
    # caminho dentro de MEDIA_ROOT; escolha a pasta que preferir
    return f"profile_photos/user_{pk}.jpg"

from django.core.files.storage import default_storage
from django.db import transaction

class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", _("Administrador")
        SERVIDOR = "SERVIDOR", _("Servidor público")
        EMPRESA = "EMPRESA", _("Empresa")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("E-mail"), unique=True, db_index=True)
    first_name = models.CharField(_("Nome"), max_length=120, blank=True)
    last_name = models.CharField(_("Sobrenome"), max_length=120, blank=True)

    role = models.CharField(_("Função"), max_length=16, choices=Roles.choices, default=Roles.EMPRESA)
    organization = models.CharField(_("Organização"), max_length=160, blank=True)

    prefeitura = models.ForeignKey("app.Prefeitura", on_delete=models.CASCADE)
    # campos obrigatórios do Django
    is_active = models.BooleanField(_("Ativo"), default=True)
    is_staff = models.BooleanField(_("Equipe/Admin"), default=False)
    date_joined = models.DateTimeField(_("Data de Cadastro"), default=timezone.now)

    profile_photo = models.ImageField(_("Foto de Perfil"), upload_to="profile_photos/", null=True, blank=True, default='defaults/default_photo.png')
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")

    def __str__(self):
        return self.email

    @transaction.atomic
    def save(self, *args, **kwargs):
        has_new_file = bool(self.profile_photo and getattr(self.profile_photo, "file", None))

        # Salva primeiro para garantir que self.pk existe
        is_create = self.pk is None
        if is_create:
            super().save(*args, **kwargs)

        # Guarda nome antigo para possível exclusão
        old_name = None
        if self.pk:
            try:
                old_obj = User.objects.get(pk=self.pk)
                if old_obj.profile_photo:
                    old_name = old_obj.profile_photo.name
            except User.DoesNotExist:
                pass

        # Se não há novo arquivo, apenas salva normalmente
        if not has_new_file:
            super().save(*args, **kwargs)
            return

        # PROCESSA A IMAGEM
        try:
            self.profile_photo.file.seek(0)
        except Exception:
            pass

        try:
            img = Image.open(self.profile_photo)
            img = img.convert("RGB")
            img = img.resize((300, 300), Image.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            content = ContentFile(buffer.read())
        except Exception:
            # fallback: salva sem processamento
            super().save(*args, **kwargs)
            return

        # Nome determinístico
        final_name = profile_photo_filename(self.pk)

        # Deleta arquivo antigo se diferente do final
        storage = self.profile_photo.storage
        try:
            if old_name and old_name != final_name and storage.exists(old_name):
                storage.delete(old_name)
        except Exception:
            pass

        # Salva a imagem processada
        self.profile_photo.save(final_name, content, save=False)

        # Salva o modelo
        super().save(*args, **kwargs)