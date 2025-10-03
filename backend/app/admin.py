from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from backend.app.models import User, Template, DocumentInstance
from backend.app.services.render import render_docx_from_template
from backend.app.services.services import convert_html_to_pdf  # seus serviços
from django.core.files import File
import os
import tempfile
import uuid

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "organization")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("first_name", "last_name", "organization", "role")}),
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "is_staff", "is_active"),
        }),
    )
from django.contrib import admin, messages
from django.utils.html import format_html, mark_safe
from django.core.files import File
import os, tempfile
from backend.app.services.render import render_docx_from_template
from backend.app.services.services import convert_html_to_pdf

# ------------------ TEMPLATE ------------------
@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at", "preview_available")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "file")}),
        ("Configuração", {"fields": ("required_fields", "preview_html")}),
        ("Metadados", {"fields": ("created_at",)}),
    )

    def preview_available(self, obj):
        return bool(obj.preview_html)
    preview_available.boolean = True
    preview_available.short_description = "Preview"


# ------------------ DOCUMENT INSTANCE ------------------
@admin.register(DocumentInstance)
class DocumentInstanceAdmin(admin.ModelAdmin):
    list_display = ("id_short", "template", "owner_email", "status", "created_at", "file_docx_link", "file_pdf_link")
    list_filter = ("status", "template", "created_at")
    search_fields = ("owner__email", "template__name", "data")
    readonly_fields = ("created_at", "updated_at", "content_html", "file_docx_link", "data_pretty", "file_pdf_link")
    actions = ("action_make_final", "action_make_draft", "action_regenerate_files")

    fieldsets = (
        (None, {"fields": ("template", "owner", "status")}),
        ("Dados preenchidos", {"fields": ("data",)}),
        ("Preview / Arquivos gerados", {"fields": ("content_html", "file_docx_link", "file_pdf_link")}),
        ("Metadados", {"fields": ("created_at", "updated_at")}),
    )

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


