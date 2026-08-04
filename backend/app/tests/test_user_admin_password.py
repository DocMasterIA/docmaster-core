"""Admin de usuário: senha somente-leitura e criação com hash."""
from __future__ import annotations

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.test import TestCase
from django.urls import reverse

from backend.app.admin import AdminUserCreationForm, UserAdmin, UserAdminForm

User = get_user_model()


class UserAdminPasswordFormTests(TestCase):
    def test_change_form_password_is_readonly_hash(self):
        user = User.objects.create_user(
            email="adminform@teste.local",
            password="SenhaAtual123!",
            first_name="A",
            last_name="B",
        )
        form = UserAdminForm(instance=user)
        self.assertIsInstance(form.fields["password"], ReadOnlyPasswordHashField)

    def test_password_change_button_links_to_admin_form(self):
        user = User.objects.create_user(
            email="adminbtn@teste.local",
            password="SenhaAtual123!",
            first_name="A",
            last_name="B",
        )
        admin = UserAdmin(User, site)
        html = admin.password_change_button(user)
        expected = reverse("admin:auth_user_password_change", args=[user.pk])
        self.assertIn(expected, html)
        self.assertIn("Alterar / definir senha", html)

    def test_change_form_ignores_posted_password_plaintext(self):
        user = User.objects.create_user(
            email="adminform2@teste.local",
            password="SenhaAtual123!",
            first_name="A",
            last_name="B",
        )
        old_hash = user.password
        form = UserAdminForm(
            data={
                "email": user.email,
                "first_name": "A",
                "last_name": "B",
                "role": user.role,
                "password": "TextoPuroNaoDeveSalvar!",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "date_joined": user.date_joined.isoformat(),
                "allowed_modules": list(user.get_allowed_modules()),
            },
            instance=user,
        )
        # Pode falhar por campos obrigatórios extras; o importante é clean_password.
        cleaned = form.clean_password()
        self.assertEqual(cleaned, old_hash)
        self.assertNotEqual(cleaned, "TextoPuroNaoDeveSalvar!")

    def test_add_form_hashes_password(self):
        form = AdminUserCreationForm(
            data={
                "email": "novo@teste.local",
                "first_name": "Novo",
                "last_name": "User",
                "role": User.Roles.SERVIDOR,
                "password1": "NovaSenha456!",
                "password2": "NovaSenha456!",
                "is_active": True,
                "is_staff": False,
                "allowed_modules": ["pesquisa"],
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("NovaSenha456!"))
        self.assertFalse(user.password.startswith("NovaSenha"))
