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
            # apagar foto antiga se houver mudança
            try:
                this = User.objects.get(pk=self.pk)
                if this.profile_photo and this.profile_photo != self.profile_photo:
                    if os.path.isfile(this.profile_photo.path):
                        os.remove(this.profile_photo.path)
            except User.DoesNotExist:
                pass  # usuário novo, sem foto antiga

            # redimensionar a imagem para 300x300
            if self.profile_photo:
                img = Image.open(self.profile_photo)
                img = img.convert('RGB')
                img = img.resize((300, 300), Image.LANCZOS)

                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=95)
                self.profile_photo.save(f'{self.id}.jpg', ContentFile(buffer.getvalue()), save=False)

            super().save(*args, **kwargs)
            
    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()