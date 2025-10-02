from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Template, Clause, DocumentInstance
from .services import render_docx_from_template, convert_html_to_pdf  # seus serviços
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


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ("name", "short_content", "tags_display")
    search_fields = ("name", "content")
    list_filter = ("tags",)

    def short_content(self, obj):
        txt = (obj.content or "").strip()
        return txt[:120] + ("..." if len(txt) > 120 else "")
    short_content.short_description = "Conteúdo"

    def tags_display(self, obj):
        if not obj.tags:
            return "-"
        return ", ".join(obj.tags)
    tags_display.short_description = "Tags"


@admin.register(DocumentInstance)
class DocumentInstanceAdmin(admin.ModelAdmin):
    list_display = ("id_short", "template", "owner_email", "status", "created_at", "file_docx_link", "file_pdf_link")
    list_filter = ("status", "template", "created_at")
    search_fields = ("owner__email", "template__name", "data")
    # tornamos esses itens readonly porque alguns não são campos do modelo
    readonly_fields = (
        "created_at",
        "updated_at",
        "content_html",
        "data_pretty",
        "file_docx_link",
        "file_pdf_link",
    )
    actions = ("action_make_final", "action_make_draft", "action_regenerate_files")

    fieldsets = (
        (None, {"fields": ("template", "owner", "status")}),
        ("Dados preenchidos", {"fields": ("data_pretty",)}),
        ("Preview / Arquivos gerados", {"fields": ("content_html", "file_docx_link", "file_pdf_link")}),
        ("Metadados", {"fields": ("created_at", "updated_at")}),
    )

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "ID"

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = "Usuário"

    def data_pretty(self, obj):
        import json
        return mark_safe("<pre style='max-height:300px;overflow:auto;'>%s</pre>" % json.dumps(obj.data, ensure_ascii=False, indent=2))
    data_pretty.short_description = "Dados (JSON)"

    def file_docx_link(self, obj):
        if obj and obj.file_docx:
            url = obj.file_docx.url
            return format_html('<a href="{}" target="_blank">Download .docx</a>', url)
        return "-"
    file_docx_link.short_description = "DOCX"

    def file_pdf_link(self, obj):
        if obj and obj.file_pdf:
            url = obj.file_pdf.url
            return format_html('<a href="{}" target="_blank">Download .pdf</a>', url)
        return "-"
    file_pdf_link.short_description = "PDF"
    
    # Ações administrativas -------------------------------------------------
    def action_make_final(self, request, queryset):
        updated = queryset.update(status="final")
        self.message_user(request, f"{updated} documento(s) marcado(s) como FINAL.", messages.SUCCESS)
    action_make_final.short_description = "Marcar como FINAL"

    def action_make_draft(self, request, queryset):
        updated = queryset.update(status="draft")
        self.message_user(request, f"{updated} documento(s) revertido(s) para RASCUNHO.", messages.SUCCESS)
    action_make_draft.short_description = "Reverter para RASCUNHO"

    def action_regenerate_files(self, request, queryset):
        """
        Regenera os arquivos DOCX/PDF a partir do template e do JSON 'data'.
        Usa os serviços render_docx_from_template e convert_html_to_pdf.
        """
        success = 0
        failures = []
        for inst in queryset:
            try:
                ctx = inst.data or {}
                tpl = inst.template

                # gera docx temporário
                tmp_docx_path = render_docx_from_template(tpl, ctx, out_dir=tempfile.gettempdir())

                # tenta gerar preview html (se tiver content_html já gravado, usa)
                preview_html = inst.content_html or ""

                # gera pdf ao lado do docx
                tmp_pdf_path = os.path.splitext(tmp_docx_path)[0] + ".pdf"
                # preferimos converter via HTML preview quando possível
                if preview_html:
                    convert_html_to_pdf(preview_html, tmp_pdf_path)
                else:
                    # fallback: gerar um PDF simples a partir do docx não é trivial; aqui só copia
                    # recomenda-se implementar um convert_docx_to_pdf service (LibreOffice headless, etc.)
                    open(tmp_pdf_path, "wb").close()

                # salva os arquivos nos FileFields do DocumentInstance
                with open(tmp_docx_path, "rb") as f:
                    inst.file_docx.save(os.path.basename(tmp_docx_path), File(f), save=False)
                with open(tmp_pdf_path, "rb") as f:
                    inst.file_pdf.save(os.path.basename(tmp_pdf_path), File(f), save=False)

                inst.save()
                success += 1

                # limpa arquivos temporários (opcional)
                try:
                    os.remove(tmp_docx_path)
                    os.remove(tmp_pdf_path)
                except OSError:
                    pass

            except Exception as e:
                failures.append((str(inst.id), str(e)))

        if success:
            self.message_user(request, f"{success} arquivo(s) regenerado(s) com sucesso.", messages.SUCCESS)
        if failures:
            for id_, err in failures:
                self.message_user(request, f"Erro ao regenerar {id_}: {err}", messages.ERROR)

    action_regenerate_files.short_description = "Regenerar DOCX/PDF a partir do template"

