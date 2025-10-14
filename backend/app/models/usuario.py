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

def _profile_photo_filename(pk: int) -> str:
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
        """
        Fluxo:
        1) se for criação (sem pk) -> salva rápido para obter pk
        2) se tem arquivo novo em self.profile_photo -> processa, compõe filename estável,
           remove anterior se existir e salva o arquivo processado com save=False
        3) chama super().save() para persistir a referência
        """
        # Detecta se há um novo arquivo vindo do formulário (um InMemoryUploadedFile por ex.)
        has_new_uploaded_file = bool(self.profile_photo and getattr(self.profile_photo, "file", None))

        # Se for novo objeto, primeiro salva sem foto para obter pk
        is_create = self.pk is None
        if is_create and not has_new_uploaded_file:
            # nada especial, só cria normalmente
            return super().save(*args, **kwargs)

        if is_create and has_new_uploaded_file:
            # salva sem processar a imagem para obter pk (transação evita inconsistências)
            super().save(*args, **kwargs)  # agora self.pk existe

        # A partir daqui self.pk existe (tanto criação quanto update)
        storage = getattr(self.profile_photo, "storage", default_storage)
        final_name = _profile_photo_filename(self.pk)

        # Guarda nome antigo (se houver) para deletar depois, caso seja diferente
        old_name = None
        if self.pk:
            try:
                old_obj = User.objects.get(pk=self.pk)
            except User.DoesNotExist:
                old_obj = None
            if old_obj and old_obj.profile_photo:
                old_name = old_obj.profile_photo.name

        # Se não há novo arquivo, nada a fazer além de salvar normalmente
        if not has_new_uploaded_file:
            return super().save(*args, **kwargs)

        # PROCESSA IMAGEM
        try:
            # garante apontar para início do stream (caso já tenha sido lido)
            try:
                self.profile_photo.file.seek(0)
            except Exception:
                pass

            img = Image.open(self.profile_photo)
            img = img.convert("RGB")
            img = img.resize((300, 300), Image.LANCZOS)

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            content = ContentFile(buffer.read())
        except Exception:
            # se der erro no processamento, não sobrescreve nada — salva sem alterar
            return super().save(*args, **kwargs)

        # Deleta arquivo final se já existir (força overwrite)
        try:
            if storage.exists(final_name):
                storage.delete(final_name)
        except Exception:
            # falhar aqui não deve quebrar o save; só logue em produção
            pass

        # Salva o arquivo processado com o nome estável, sem salvar o model ainda
        try:
            self.profile_photo.save(final_name, content, save=False)
        except Exception:
            # fallback: apenas atribui o ContentFile sem usar .save(); menos ideal
            self.profile_photo = ContentFile(content.read(), name=final_name)

        # Agora que o field foi atualizado, persiste o modelo (faz update do profile_photo)
        super().save(*args, **kwargs)

        # Remove o arquivo antigo se for diferente do atual
        try:
            if old_name and old_name != self.profile_photo.name and storage.exists(old_name):
                storage.delete(old_name)
        except Exception:
            pass
