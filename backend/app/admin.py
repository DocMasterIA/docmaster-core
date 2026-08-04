import nested_admin
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from backend.app.models import Template, DocumentInstance, TemplateSchema, SchemaAudit, Prefeitura, Secretaria, SubtopicoSecretaria, SecretariaTipo
from backend.app.services.render import render_docx_from_template
from backend.app.services.services import convert_html_to_pdf  # seus serviços
from django.core.files import File
import os
import tempfile
import uuid
from django.utils.html import format_html
from django.contrib.auth import get_user_model
import logging
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password
from dal import autocomplete
from backend.app.models.usuario import MODULE_ACCESS_CHOICES

logger = logging.getLogger(__name__)
User = get_user_model()


def _prefeitura_user_limit_message(prefeitura, *, exclude_user_id=None):
    """Retorna mensagem de erro se a prefeitura já atingiu o limite de usuários."""
    if not prefeitura or not prefeitura.pk:
        return None
    qs = User.objects.filter(prefeitura_id=prefeitura.pk)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    if qs.count() >= prefeitura.numero_usuarios_permitidos:
        return (
            f"Limite de usuários atingido para {prefeitura.nome_municipio} "
            f"({prefeitura.numero_usuarios_permitidos})."
        )
    return None


def _user_password_change_url(user) -> str:
    """URL absoluta do formulário admin de alteração de senha.

    Django UserAdmin fixa o nome como auth_user_password_change mesmo com
    custom user (path continua /admin/app/user/<id>/password/).
    """
    return reverse("admin:auth_user_password_change", args=[user.pk])


class UserAdminForm(forms.ModelForm):
    """
    Edição de usuário no admin.

    O campo password DEVE ser somente-leitura (hash). Editar texto puro aqui
    corrompe o hash (autofill/salvar vazio) e quebra login + troca de senha
    no frontend para esses usuários.
    """

    password = ReadOnlyPasswordHashField(
        label=_("Senha"),
        help_text=_(
            "Senhas não são armazenadas em texto puro. "
            "Use o botão «Alterar senha» abaixo (não edite o hash)."
        ),
    )
    allowed_modules = forms.MultipleChoiceField(
        label="Módulos permitidos",
        required=False,
        choices=[(k, k.replace("_", " ").title()) for k in MODULE_ACCESS_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        help_text="Selecione os módulos liberados para este usuário.",
    )

    class Meta:
        model = User
        fields = "__all__"
        widgets = {
            'secretaria': autocomplete.ModelSelect2(
                url='secretaria-autocomplete',
                forward=['prefeitura']  # envia o campo 'prefeitura' para o autocomplete
            )
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, "get_allowed_modules"):
            self.fields["allowed_modules"].initial = self.instance.get_allowed_modules()

        prefeitura = None
        prefeitura_raw = self.data.get("prefeitura") if self.data else None
        if prefeitura_raw:
            prefeitura = Prefeitura.objects.filter(pk=prefeitura_raw).first()
        elif self.instance and self.instance.prefeitura_id:
            prefeitura = self.instance.prefeitura

        if prefeitura:
            self.fields["secretaria"].queryset = Secretaria.objects.filter(prefeitura=prefeitura)
        else:
            self.fields["secretaria"].queryset = Secretaria.objects.none()

        password = self.fields.get("password")
        if password and self.instance and self.instance.pk and not self.instance.has_usable_password():
            password.help_text = _(
                "Este usuário ainda não tem senha utilizável. "
                "Use o botão «Alterar senha» abaixo para definir uma."
            )

    def clean_password(self):
        # Nunca aceitar texto digitado/autofill no formulário de edição.
        return self.initial.get("password") or getattr(self.instance, "password", "")

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        prefeitura = cleaned_data.get("prefeitura")
        secretaria = cleaned_data.get("secretaria")

        if secretaria and prefeitura and secretaria.prefeitura_id != prefeitura.pk:
            raise ValidationError({
                "secretaria": "A secretaria selecionada não pertence à prefeitura escolhida.",
            })

        if not prefeitura:
            return cleaned_data

        assigning_prefeitura = (
            self.instance.pk is None or self.instance.prefeitura_id != prefeitura.pk
        )
        if assigning_prefeitura:
            msg = _prefeitura_user_limit_message(prefeitura)
            if msg:
                raise ValidationError({"prefeitura": msg})

        return cleaned_data

    def clean_allowed_modules(self):
        vals = self.cleaned_data.get("allowed_modules") or []
        normalized = [v for v in vals if v in MODULE_ACCESS_CHOICES]
        return normalized or list(MODULE_ACCESS_CHOICES)


class AdminUserCreationForm(forms.ModelForm):
    """Criação de usuário no admin com password1/password2 (hash via set_password)."""

    password1 = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Mínimo 8 caracteres."),
    )
    password2 = forms.CharField(
        label=_("Confirmação da senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    allowed_modules = forms.MultipleChoiceField(
        label="Módulos permitidos",
        required=False,
        choices=[(k, k.replace("_", " ").title()) for k in MODULE_ACCESS_CHOICES],
        widget=forms.CheckboxSelectMultiple,
        help_text="Selecione os módulos liberados para este usuário.",
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "profile_photo",
            "role",
            "prefeitura",
            "secretaria",
            "allowed_modules",
            "is_staff",
            "is_active",
        )
        widgets = {
            "secretaria": autocomplete.ModelSelect2(
                url="secretaria-autocomplete",
                forward=["prefeitura"],
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["allowed_modules"].initial = list(MODULE_ACCESS_CHOICES)
        prefeitura = None
        prefeitura_raw = self.data.get("prefeitura") if self.data else None
        if prefeitura_raw:
            prefeitura = Prefeitura.objects.filter(pk=prefeitura_raw).first()
        if prefeitura:
            self.fields["secretaria"].queryset = Secretaria.objects.filter(prefeitura=prefeitura)
        else:
            self.fields["secretaria"].queryset = Secretaria.objects.none()

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("Este e-mail já está cadastrado."))
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError(_("As senhas não conferem."))
        return p2

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if password:
            validate_password(password, user=User(email=self.data.get("email") or ""))
        return password

    def clean_allowed_modules(self):
        vals = self.cleaned_data.get("allowed_modules") or []
        normalized = [v for v in vals if v in MODULE_ACCESS_CHOICES]
        return normalized or list(MODULE_ACCESS_CHOICES)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        prefeitura = cleaned.get("prefeitura")
        secretaria = cleaned.get("secretaria")
        if secretaria and prefeitura and secretaria.prefeitura_id != prefeitura.pk:
            raise ValidationError({
                "secretaria": "A secretaria selecionada não pertence à prefeitura escolhida.",
            })
        if prefeitura:
            msg = _prefeitura_user_limit_message(prefeitura)
            if msg:
                raise ValidationError({"prefeitura": msg})
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


# Admin de usuários customizados, com autocomplete de secretaria e inline de leitura.
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    add_form = AdminUserCreationForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "profile_photo", "prefeitura","secretaria", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "prefeitura")
    readonly_fields = ("password_change_button",)

    fieldsets = (
        (None, {"fields": ("email", "password", "password_change_button")}),
        (_("Informações pessoais"), {"fields": ("first_name", "last_name", "prefeitura", "secretaria", "role", "allowed_modules")}),
        (_("Perfil"), {"fields": ("profile_photo",)}),  # tupla de um elemento
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("first_name", "last_name", "email", "profile_photo","password1", "password2", "role", "prefeitura", "secretaria", "allowed_modules", "is_staff", "is_active"),
        }),
    )

    @admin.display(description=_("Alterar senha"))
    def password_change_button(self, obj):
        if not obj or not obj.pk:
            return "—"
        return format_html(
            '<a class="button" href="{}">Alterar / definir senha</a>',
            _user_password_change_url(obj),
        )

from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.core.files import File
import os, tempfile
from backend.app.services.render import render_docx_from_template
from backend.app.services.services import convert_html_to_pdf
from backend.app.services.preview import generate_docx_preview



# Admin de Templates com card de preview PDF incorporado e slug automático.
@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "preview_card", "role_can_access", "related_subtopico", "prefeitura", "template_tag")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    #readonly_fields = ('preview_card',)  # campo só leitura
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'slug', 'file', 'role_can_access', 'prefeitura', 'related_subtopico', 'template_tag')
        }),
        ('Preview', {
            'fields': ('preview_image', 'preview_pdf'),
            'classes': ('collapse',)
        }),
    )
        # mostra o PDF em iframe direto

    
    def preview_card(self, obj):
        if obj.preview_pdf:
            return format_html(
                '''
                <div style="
                    border-radius: 0.75rem;
                    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
                    padding: 0.5rem;
                    max-width: 320px;
                    margin: 0.5rem 0;
                    background: var(--unfold-surface, #f9fafb);
                    color: var(--unfold-text-default, #111);
                    transition: background 0.3s, color 0.3s;
                    display:flex; flex-direction:column; align-items:center;
                ">
                    <strong style="display:block;margin-bottom:0.5rem;color:var(--unfold-text-heading, #111);">{name}</strong>
                    <div style="
                        width:100%;
                        height:250px;
                        overflow:hidden;
                        border-radius:0.5rem;
                        border:1px solid var(--unfold-border-color, #ddd);
                        background: var(--unfold-bg-body, #fff);
                    ">
                        <embed src="{url}" type="application/pdf" width="100%" height="100%">
                    </div>
                    <a href="{url}" target="_blank" style="
                        display:inline-block;
                        margin-top:0.5rem;
                        padding:0.25rem 0.5rem;
                        background: var(--primary-600, #3b82f6);
                        color:white;
                        border-radius:0.25rem;
                        text-decoration:none;
                        font-size:0.875rem;
                    ">Abrir/Download PDF</a>
                </div>
                ''',
                name=obj.name,
                url = obj.preview_pdf.url.replace('localhost', '127.0.0.1')
            )
        return "-"


    preview_card.short_description = "Preview PDF"
    preview_card.allow_tags = True


    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

# Admin de TemplateSchema (schema IA) com leitura básica.
@admin.register(TemplateSchema)
class TemplateSchemaAdmin(admin.ModelAdmin):
    list_display = ("template_name", "strategy", "created_at")
    search_fields = ("template__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def template_name(self, obj):
        return obj.template.name
    template_name.short_description = "Template"

# Admin de auditoria de schemas IA.
@admin.register(SchemaAudit)
class SchemaAuditAdmin(admin.ModelAdmin):
    list_display = ("schema_template_name", "user", "created_at")
    search_fields = ("schema__template__name", "user__username")
    readonly_fields = ("created_at", "payload")
    ordering = ("-created_at",)

    def schema_template_name(self, obj):
        return obj.schema.template.name
    schema_template_name.short_description = "Template"

# ------------------ DOCUMENT INSTANCE ------------------
# Admin de documentos gerados, com ações de mudar status e regenerar arquivos.
@admin.register(DocumentInstance)
class DocumentInstanceAdmin(admin.ModelAdmin):
    list_display = ("id_short", "template", "owner_email", "status", "created_at", "file_docx", "file_pdf")
    list_filter = ("status", "template", "created_at")
    search_fields = ("owner__email", "template__name", "data")
    readonly_fields = ("created_at", "updated_at", "content_html","data_pretty",)
    actions = ("action_make_final", "action_make_draft", "action_regenerate_files")

    fieldsets = (
        (None, {"fields": ("template", "owner", "status")}),
        ("Dados preenchidos", {"fields": ("data",)}),
        ("Preview / Arquivos gerados", {"fields": ("content_html", "file_docx", "file_pdf")}),
        ("Metadados", {"fields": ("created_at", "updated_at")}),
    )


   
    # def preview_card(self, obj):
    #     if obj.file_pdf:
    #         return format_html(
    #             '''
    #             <div style="
    #                 border-radius: 0.75rem;
    #                 box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    #                 padding: 0.5rem;
    #                 max-width: 320px;
    #                 margin: 0.5rem 0;
    #                 background: var(--unfold-surface, #f9fafb);
    #                 color: var(--unfold-text-default, #111);
    #                 transition: background 0.3s, color 0.3s;
    #                 display:flex; flex-direction:column; align-items:center;
    #             ">
    #                 <strong style="display:block;margin-bottom:0.5rem;color:var(--unfold-text-heading, #111);">{name}</strong>
    #                 <div style="
    #                     width:100%;
    #                     height:250px;
    #                     overflow:hidden;
    #                     border-radius:0.5rem;
    #                     border:1px solid var(--unfold-border-color, #ddd);
    #                     background: var(--unfold-bg-body, #fff);
    #                 ">
    #                     <embed src="{url}" type="application/pdf" width="100%" height="100%">
    #                 </div>
    #                 <a href="{url}" target="_blank" style="
    #                     display:inline-block;
    #                     margin-top:0.5rem;
    #                     padding:0.25rem 0.5rem;
    #                     background: var(--primary-600, #3b82f6);
    #                     color:white;
    #                     border-radius:0.25rem;
    #                     text-decoration:none;
    #                     font-size:0.875rem;
    #                 ">Abrir/Download PDF</a>
    #             </div>
    #             ''',
    #             name=obj.template.name,
    #             url = obj.file_pdf.url.replace('localhost', '127.0.0.1')
    #         )
    #     return "-"



    # preview_card.short_description = "Preview PDF"
    # preview_card.allow_tags = True

    # ------------------ DISPLAY HELPERS ------------------
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "ID"

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = "Usuário"

    @admin.display(description="Dados (JSON)", ordering="created_at")
    def data_pretty(self, obj):
        import json
        return mark_safe("<textarea style='width:100%;height:250px;'>%s</textarea>" % json.dumps(obj.data, ensure_ascii=False, indent=2))

    def file_docx_link(self, obj):
        if obj.file_docx:
            return format_html('<a href="{}" target="_blank">Download .docx</a>', obj.file_docx.url)
        return "-"
    file_docx_link.short_description = "DOCX"

    def file_pdf_link(self, obj):
        if obj.file_pdf:
            return format_html('<a href="{}" target="_blank">Download .pdf</a>', obj.file_pdf.url)
        return "-"
    file_pdf_link.short_description = "PDF"

    # ------------------ ACTIONS ------------------
    def action_make_final(self, request, queryset):
        updated = queryset.update(status="final")
        self.message_user(request, f"{updated} documento(s) marcado(s) como FINAL.", messages.SUCCESS)
    action_make_final.short_description = "Marcar como FINAL"

    def action_make_draft(self, request, queryset):
        updated = queryset.update(status="draft")
        self.message_user(request, f"{updated} documento(s) revertido(s) para RASCUNHO.", messages.SUCCESS)
    action_make_draft.short_description = "Reverter para RASCUNHO"

    def action_regenerate_files(self, request, queryset):
        success = 0
        failures = []
        for inst in queryset:
            try:
                ctx = inst.data or {}
                tpl = inst.template

                tmp_docx_path = render_docx_from_template(tpl.file.path, ctx, out_dir=tempfile.gettempdir())

                preview_html = inst.content_html or ""

                tmp_pdf_path = os.path.splitext(tmp_docx_path)[0] + ".pdf"
                if preview_html:
                    convert_html_to_pdf(preview_html, tmp_pdf_path)
                else:
                    open(tmp_pdf_path, "wb").close()

                with open(tmp_docx_path, "rb") as f:
                    inst.file_docx.save(os.path.basename(tmp_docx_path), File(f), save=False)
                with open(tmp_pdf_path, "rb") as f:
                    inst.file_pdf.save(os.path.basename(tmp_pdf_path), File(f), save=False)

                inst.save()
                success += 1

                os.remove(tmp_docx_path)
                os.remove(tmp_pdf_path)

            except Exception as e:
                failures.append((str(inst.id), str(e)))

        if success:
            self.message_user(request, f"{success} arquivo(s) regenerado(s) com sucesso.", messages.SUCCESS)
        if failures:
            for id_, err in failures:
                self.message_user(request, f"Erro ao regenerar {id_}: {err}", messages.ERROR)
    action_regenerate_files.short_description = "Regenerar DOCX/PDF"




from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.admin import AdminSite
from backend.app.models import User, Template, DocumentInstance

# função view
# Dashboard custom do admin com contadores resumidos.
def dashboard_view(request):
    total_users = User.objects.count()
    total_templates = Template.objects.count()
    total_documents = DocumentInstance.objects.count()
    documents_finalizados = DocumentInstance.objects.filter(status='final').count()

    context = dict(
        total_users=total_users,
        total_templates=total_templates,
        total_documents=total_documents,
        documents_finalizados=documents_finalizados,
    )
    return TemplateResponse(request, "admin/index.html", context)

from django.forms.models import BaseInlineFormSet
from django.db import transaction


def _resolve_prefeitura_from_inline_parent(parent):
    """Resolve a prefeitura a partir do objeto pai de um inline (Prefeitura ou Secretaria)."""
    if parent is None:
        return None
    if isinstance(parent, Prefeitura):
        return parent
    prefeitura_id = getattr(parent, "prefeitura_id", None)
    if prefeitura_id:
        return Prefeitura.objects.filter(pk=prefeitura_id).first()
    return None


def _count_new_users_in_formset(formset):
    novos = 0
    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue
        if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
            if form.instance.pk is None:
                novos += 1
    return novos


# Formset inline para validar limites de usuários por prefeitura.
class UsuarioInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Limite é validado em PrefeituraAdmin.save_formset após salvar o novo
        # numero_usuarios_permitidos; aqui só garantimos e-mail único por formulário.

    def save_new(self, form, commit=True):
        obj = form.save(commit=False)
        if obj.secretaria_id and not obj.prefeitura_id:
            obj.prefeitura = obj.secretaria.prefeitura
        # Inline não coleta senha: marcar unusable (evita password="" que quebra auth).
        if not obj.has_usable_password():
            obj.set_unusable_password()
        if commit:
            obj.save()
            form.save_m2m()
        return obj


# Inline de usuários dentro de Secretarias (nested).
class UsuarioInline(nested_admin.NestedTabularInline):
    model = User
    formset = UsuarioInlineFormSet
    fk_name = "secretaria"
    fields = ("first_name", "last_name", "email", "is_active")
    extra = 0
    show_change_link = True
    can_delete = True
    verbose_name_plural = (
        "Usuários (sem senha aqui — após criar, abra o usuário e use "
        "«Alterar senha» / formulário de senha)"
    )

from dal import autocomplete

class SecretariaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Secretaria.objects.all()

        # filtro por GET['prefeitura'] passado via AJAX
        prefeitura_id = self.forwarded.get('prefeitura', None)
        if prefeitura_id:
            qs = qs.filter(prefeitura_id=prefeitura_id)

        return qs

# Inline de Secretarias dentro da Prefeitura, incluindo usuários como nested inline read-only.
class SecretariaInline(nested_admin.NestedStackedInline):
    model = Secretaria
    fk_name = "prefeitura"   # ajuste se o FK no User tiver outro nome
    fields = ("nome","descricao")  # escolha os campos que quer ver
    extra = 0                # não mostrar formulários vazios extras

    inlines = [UsuarioInline]


# Inline de Subtópicos dentro do Tipo de Secretaria.
class SubtopicoSecretariaInLine(admin.StackedInline):
    model = SubtopicoSecretaria
    fk_name = "tipo_secretaria"   # ajuste se o FK no User tiver outro nome
    fields = ("nome","descricao")  # escolha os campos que quer ver
    extra = 0                # não mostrar formulários vazios extras


# Admin de Tipos de Secretaria com inline de Subtópicos.
@admin.register(SecretariaTipo)
class SecretariaTipoAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao")
    readonly_fields = ("nome", "descricao")
    search_fields = ("nome",)
    ordering = ("nome",)

    inlines = [SubtopicoSecretariaInLine]



# Admin de Prefeituras com inline de Secretarias e validação de limite de usuários.
@admin.register(Prefeitura)
class PrefeituraAdmin(nested_admin.NestedModelAdmin):
    list_display = ("nome_municipio", "estado", "url", "numero_usuarios_permitidos")
    search_fields = ("nome_municipio", "estado",)
    ordering = ("nome_municipio", "estado",)
    readonly_fields = ("url",)

    fieldsets = (
        (None, {
            "fields": ("nome_municipio", "estado", "numero_usuarios_permitidos")
        }),
        ("Informações automáticas", {
            "fields": ("url",),
            "description": "A URL é gerada automaticamente a partir do nome do município."
        }),
    )

    inlines = [SecretariaInline]


    def has_delete_permission(self, request, obj=None):
        # opcional: impede exclusão acidental no admin
        return True  # ou False se quiser bloquear exclusões
    
    def save_formset(self, request, form, formset, change):
        if formset.model != User:
            return super().save_formset(request, form, formset, change)

        prefeitura = _resolve_prefeitura_from_inline_parent(form.instance)
        if not prefeitura or not prefeitura.pk:
            return super().save_formset(request, form, formset, change)

        novos = _count_new_users_in_formset(formset)
        if novos == 0:
            return super().save_formset(request, form, formset, change)

        with transaction.atomic():
            pref_locked = Prefeitura.objects.select_for_update().get(pk=prefeitura.pk)
            existentes = User.objects.filter(prefeitura=pref_locked).count()
            logger.debug(
                "Admin save_formset: pref=%s existentes=%s novos=%s limite=%s",
                pref_locked.pk,
                existentes,
                novos,
                pref_locked.numero_usuarios_permitidos,
            )
            if existentes + novos > pref_locked.numero_usuarios_permitidos:
                msg = (
                    f"Não foi possível adicionar {novos} usuário(s): limite de "
                    f"{pref_locked.numero_usuarios_permitidos} atingido "
                    f"(existem {existentes})."
                )
                self.message_user(request, msg, level=messages.ERROR)
                return

            for f in formset.forms:
                if not getattr(f, "cleaned_data", None) or f.cleaned_data.get("DELETE"):
                    continue
                if f.instance.pk is None:
                    f.instance.prefeitura = pref_locked

            return super().save_formset(request, form, formset, change)
