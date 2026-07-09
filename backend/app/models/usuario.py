import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class UserManager(BaseUserManager):
    use_in_migrations = True

    # Cria usuário genérico (pode ter senha ou permanecer como convite sem senha).
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

    # Cria superusuário administrativo (força flags is_staff/is_superuser = True).
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
    # Caminho de upload para foto de perfil: 'profile_photos/{user_id}.ext'
    ext = filename.split('.')[-1]
    filename = f'{instance.id}.{ext}'
    return os.path.join('profile_photos', filename)

def profile_photo_filename(pk: int) -> str:
    # Nome determinístico do arquivo de foto no storage/media
    return f"profile_photos/user_{pk}.jpg"

from django.core.files.storage import default_storage
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile

MODULE_ACCESS_CHOICES = (
    "dispensa",
    "dispensa_eletronica",
    "pregao",
    "pregao_eletronico",
    "inexigibilidade",
    "etp",
    "analisador",
    "pesquisa",
    "contratos",
    "controle_interno",
    "impugnacao",
    "recurso",
    "usuario",
)


def default_allowed_modules() -> list[str]:
    return list(MODULE_ACCESS_CHOICES)


class User(AbstractBaseUser, PermissionsMixin):

    class RolePrefeitura(models.TextChoices):
        GABINETE_PREFEITO = "GABINETE DO PREFEITO", _("Gabinete do Prefeito")
        SEC_DE_ADM_E_FIN = "SECRETARIA DE ADMINISTRAÇÃO E FINANÇAS",_("Secretaria de Administração e Finanças")
        SEC_DE_PLAN_E_GES = "SECRETARIA DE PLANEJAMENTO E GESTÃO",_("Secretaria de Planejamento e Gestão")
        SEC_DE_OBRAS_E_INFRA= "SECRETARIA DE OBRAS E INFRAESTRUTURA", _("Secretaria de obras e infraestrutura")
        SEC_DE_MAMB_E_AGRO = "SECRETARIA DE MEIO AMBIENTE E AGRICULTURA", _("Secretaria de Meio Ambiente e Agricultura")
        SEC_DE_EDU = "SECRETARIA DE EDUCAÇÃO", _("Secretaria de Educação")
        SEC_DE_SAUDE = "SECRETARIA DE SAÚDE", _("Secretaria de Saúde")
        SEC_DE_ASS_SOCIAL = "SECRETARIA DE ASSISTÊNCIA SOCIAL", _("Secretaria de Assistência Social")
        SEC_DE_SEG_E_TR = "SECRETARIA DE SEGURANÇA E TRÂNSITO", _("Secretaria de Segurança e Trânsito")
        SEC_DE_CUL_ESP_E_LAZER = "SECRETARIA DE CULTURA, ESPORTE E LAZER", _("Secretaria de Cultura, Esporte e Lazer")
        SEC_DA_FAZENDA = "SECRETARIA DA FAZENDA", _("Secretaria da fazenda")
        
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", _("Administrador")
        SERVIDOR = "SERVIDOR", _("Servidor público")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("E-mail"), unique=True, db_index=True)
    first_name = models.CharField(_("Nome"), max_length=120, blank=True)
    last_name = models.CharField(_("Sobrenome"), max_length=120, blank=True)

    role = models.CharField(_("Função"), max_length=16, choices=Roles.choices, default=Roles.SERVIDOR)

    organization = models.CharField(_("Organização"), max_length=160, blank=True)

    prefeitura = models.ForeignKey("app.Prefeitura", on_delete=models.CASCADE, blank=True, null=True)
    secretaria = models.ForeignKey("app.Secretaria", on_delete=models.CASCADE, blank=True, null=True)
    
    # campos obrigatórios do Django
    is_active = models.BooleanField(_("Ativo"), default=True)
    is_staff = models.BooleanField(_("Equipe/Admin"), default=False)
    date_joined = models.DateTimeField(_("Data de Cadastro"), default=timezone.now)

    profile_photo = models.ImageField(_("Foto de Perfil"), upload_to="profile_photos/", null=True, blank=True, default='defaults/default_photo.png')
    allowed_modules = models.JSONField(_("Módulos permitidos"), default=default_allowed_modules, blank=True)
    # Preferências reutilizáveis do usuário (ex.: CNPJ/Telefone p/ relatórios de cotação PNCP)
    pncp_export_prefs = models.JSONField(_("Preferências de exportação PNCP"), default=dict, blank=True)
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")

    def __str__(self):
        return self.email

    def get_allowed_modules(self) -> list[str]:
        """Resolve módulos efectivos; vazio ou inválido na BD = todos (legado). Ver migração 0038."""
        raw = self.allowed_modules
        if self.is_superuser:
            return list(MODULE_ACCESS_CHOICES)
        if not isinstance(raw, list):
            return list(MODULE_ACCESS_CHOICES)
        allowed = [str(x).strip() for x in raw if str(x).strip() in MODULE_ACCESS_CHOICES]
        if not allowed:
            return list(MODULE_ACCESS_CHOICES)
        return list(dict.fromkeys(allowed))
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Save robusto que:
        - valida e aplica lock na Prefeitura para checar limite (evita race conditions)
        - trata criação (precisa de PK para nome de arquivo determinístico)
        - processa imagem de profile_photo (resize, convert to JPEG)
        - remove arquivo antigo quando necessário
        """

        # 1) Validações do modelo (levanta ValidationError se inválido)
        # Nota: se você usar forms/serializers que já fazem full_clean, isso é redundante,
        # mas garante segurança caso alguém chame save() diretamente.
        self.full_clean(exclude=None)

        # Se não há prefeitura definida, segue normalmente (ou levante se for obrigatório)
        if not self.prefeitura_id:
            # continua para salvar normalmente (tratamento de foto abaixo ainda será aplicado)
            pass
        else:
            # 2) Checar limite quando criando ou mudando de prefeitura
            is_creating = self.pk is None
            changed_prefeitura = False
            if not is_creating:
                old = type(self).objects.filter(pk=self.pk).only("prefeitura").first()
                if old and old.prefeitura_id != self.prefeitura_id:
                    changed_prefeitura = True

            if is_creating or changed_prefeitura:
                # Lock na prefeitura para evitar condição de corrida
                from backend.app.models import Prefeitura  # import local pra evitar circular import
                pref = Prefeitura.objects.select_for_update().get(pk=self.prefeitura_id)
                current_count = type(self).objects.filter(prefeitura=pref).count()
                # se estamos mudando de prefeitura e o usuário já estava na mesma prefeitura,
                # current_count já reflete corretamente (self ainda não está nessa prefeitura)
                if current_count >= pref.numero_usuarios_permitidos:
                    raise ValidationError({
                        "prefeitura": f"Limite de usuários atingido para {pref.nome_municipio} "
                                    f"({pref.numero_usuarios_permitidos})."
                    })

        # 3) Detecta se há novo arquivo de profile_photo (UploadedFile)
        has_new_file = isinstance(getattr(self.profile_photo, "file", None), UploadedFile)

        # 4) Em criação com nova foto: salva primeiro para garantir PK
        need_pk_for_filename = has_new_file and (self.pk is None)
        if need_pk_for_filename:
            # salva sem arquivo (garante pk)
            file_backup = self.profile_photo
            self.profile_photo = None
            super().save(*args, **kwargs)
            # restaura o arquivo para processamento abaixo
            self.profile_photo = file_backup

        # 5) Guarda nome antigo para remoção posterior (se houver)
        old_name = None
        if self.pk:
            try:
                old_obj = type(self).objects.get(pk=self.pk)
                if old_obj.profile_photo:
                    old_name = old_obj.profile_photo.name
            except type(self).DoesNotExist:
                old_name = None

        # 6) Sem novo arquivo de foto: siga com save normal
        if not has_new_file:
            super().save(*args, **kwargs)
            return

        # 7) Processa imagem (resize, converte para JPEG)
        try:
            # garante cursor no início
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
            # fallback: tenta salvar o arquivo original
            super().save(*args, **kwargs)
            return

        # 8) Gera nome determinístico usando self.pk
        final_name = profile_photo_filename(self.pk)

        # 9) Remove arquivo antigo se for diferente do novo
        storage = self.profile_photo.storage
        try:
            if old_name and old_name != final_name and storage.exists(old_name):
                storage.delete(old_name)
        except Exception:
            # não falha o save por problemas de storage
            pass

        # 10) Salva imagem processada no campo (save=False para consolidar alterações)
        self.profile_photo.save(final_name, content, save=False)

        # 11) Salva o modelo (na mesma transação)
        super().save(*args, **kwargs)
