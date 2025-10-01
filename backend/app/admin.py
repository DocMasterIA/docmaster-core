from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

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
