import nested_admin
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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
from dal import autocomplete

logger = logging.getLogger(__name__)
User = get_user_model()

class UserAdminForm(forms.ModelForm):
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
        # se já existe uma prefeitura selecionada no form (edit)
        if self.instance and self.instance.prefeitura:
            self.fields["secretaria"].queryset = Secretaria.objects.filter(prefeitura=self.instance.prefeitura)
        else:
            # se não, nenhum disponível
            self.fields["secretaria"].queryset = Secretaria.objects.none()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "profile_photo", "prefeitura","secretaria", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "prefeitura")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("first_name", "last_name", "prefeitura", "secretaria", "role")}),
        (_("Perfil"), {"fields": ("profile_photo",)}),  # tupla de um elemento
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("first_name", "last_name", "email", "profile_photo","password1", "password2", "role", "prefeitura", "secretaria", "is_staff", "is_active"),
        }),
    )
from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.core.files import File
import os, tempfile
from backend.app.services.render import render_docx_from_template
from backend.app.services.services import convert_html_to_pdf
from backend.app.services.preview import generate_docx_preview



@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "preview_card", "role_can_access",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ('preview_display',)  # campo só leitura
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

@admin.register(TemplateSchema)
class TemplateSchemaAdmin(admin.ModelAdmin):
    list_display = ("template_name", "strategy", "created_at")
    search_fields = ("template__name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def template_name(self, obj):
        return obj.template.name
    template_name.short_description = "Template"

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
from django.core.exceptions import ValidationError
from django.db import transaction

class UsuarioInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        prefeitura = self.instance
        if not prefeitura.pk:
            return

        usuarios_existentes = prefeitura.user_set.count()
        novos = 0
        for form in self.forms:
            # formulário pode ser invalido / vazio: pule
            if not getattr(form, "cleaned_data", None):
                continue
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                # novo se não tem PK (vai ser criado)
                if form.instance.pk is None:
                    novos += 1
        total = usuarios_existentes + novos
        if total > prefeitura.numero_usuarios_permitidos:
            raise ValidationError(
                f"Limite excedido! Esta prefeitura permite no máximo {prefeitura.numero_usuarios_permitidos} usuários."
            )
        
class UsuarioInline(nested_admin.NestedTabularInline):
    model = User
    fk_name = "secretaria"   # ajuste se o FK no User tiver outro nome
    fields = ("first_name", "last_name","email", "is_active")  # escolha os campos que quer ver
    readonly_fields = ("first_name", "last_name", "email", "is_active")  
    extra = 0                # não mostrar formulários vazios extras
    show_change_link = False  # link para editar o usuário
    can_delete = True

    def has_add_permission(self, request, obj=None):
        # desativa a adição via inline
        return False

from dal import autocomplete

class SecretariaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Secretaria.objects.all()

        # filtro por GET['prefeitura'] passado via AJAX
        prefeitura_id = self.forwarded.get('prefeitura', None)
        if prefeitura_id:
            qs = qs.filter(prefeitura_id=prefeitura_id)

        return qs

class SecretariaInline(nested_admin.NestedStackedInline):
    model = Secretaria
    fk_name = "prefeitura"   # ajuste se o FK no User tiver outro nome
    fields = ("nome","descricao")  # escolha os campos que quer ver
    extra = 0                # não mostrar formulários vazios extras

    inlines = [UsuarioInline]

@admin.register(SecretariaTipo)
class SecretariaTipoAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao")
    readonly_fields = ("nome", "descricao")
    search_fields = ("nome",)
    ordering = ("nome",)

@admin.register(Prefeitura)
class PrefeituraAdmin(nested_admin.NestedModelAdmin):
    list_display = ("nome_municipio", "url", "numero_usuarios_permitidos")
    search_fields = ("nome_municipio",)
    ordering = ("nome_municipio",)
    readonly_fields = ("url",)

    fieldsets = (
        (None, {
            "fields": ("nome_municipio", "numero_usuarios_permitidos")
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
        # aplicar apenas para o inline de usuários (use comparação robusta)
        if formset.model != User:
            return super().save_formset(request, form, formset, change)

        prefeitura = form.instance
        if not prefeitura.pk:
            return super().save_formset(request, form, formset, change)

        # Conta quantos novos serão criados no formset
        novos = 0
        for f in formset.forms:
            if not getattr(f, "cleaned_data", None):
                continue
            if f.cleaned_data and not f.cleaned_data.get("DELETE", False):
                if f.instance.pk is None:
                    novos += 1

        if novos == 0:
            return super().save_formset(request, form, formset, change)

        # checagem atômica com lock na prefeitura
        from app.models import Prefeitura as PrefModel  # ajuste se necessário
        with transaction.atomic():
            pref_locked = PrefModel.objects.select_for_update().get(pk=prefeitura.pk)
            existentes = User.objects.filter(prefeitura=pref_locked).count()
            logger.debug("Admin save_formset: pref=%s existentes=%s novos=%s limite=%s",
                         pref_locked.pk, existentes, novos, pref_locked.numero_usuarios_permitidos)
            if existentes + novos > pref_locked.numero_usuarios_permitidos:
                msg = (f"Não foi possível adicionar os {novos} usuário(s): limite de "
                       f"{pref_locked.numero_usuarios_permitidos} atingido (existem {existentes}).")
                self.message_user(request, msg, level=messages.ERROR)
                # interrompe salvamento do formset lançando ValidationError que o admin exibe
                raise ValidationError(msg)
            # tudo ok — salva o formset dentro da mesma transação
            return super().save_formset(request, form, formset, change)
