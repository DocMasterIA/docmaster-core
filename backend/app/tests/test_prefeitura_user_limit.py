from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from backend.app.admin import (
    PrefeituraAdmin,
    UserAdminForm,
    _resolve_prefeitura_from_inline_parent,
)
from backend.app.models import Prefeitura, Secretaria

User = get_user_model()


class PrefeituraUserLimitHelpersTest(TestCase):
    def setUp(self):
        self.pref = Prefeitura.objects.create(
            nome_municipio="Teste Limite",
            estado="SC",
            numero_usuarios_permitidos=2,
        )
        self.secretaria = Secretaria.objects.create(
            prefeitura=self.pref,
            nome="Administração",
        )

    def test_resolve_prefeitura_from_secretaria(self):
        resolved = _resolve_prefeitura_from_inline_parent(self.secretaria)
        self.assertEqual(resolved.pk, self.pref.pk)

    def test_third_user_allowed_after_limit_increase(self):
        User.objects.create_user(
            email="u1@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )
        User.objects.create_user(
            email="u2@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )

        self.pref.numero_usuarios_permitidos = 3
        self.pref.save()

        user = User(
            email="u3@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )
        user.save()

        self.assertEqual(User.objects.filter(prefeitura=self.pref).count(), 3)

    def test_third_user_blocked_when_limit_still_two(self):
        User.objects.create_user(
            email="u1@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )
        User.objects.create_user(
            email="u2@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )

        user = User(
            email="u3@test.com",
            prefeitura=self.pref,
            secretaria=self.secretaria,
        )
        with self.assertRaises(ValidationError):
            user.save()

    def test_save_formset_import_does_not_use_app_models(self):
        """Garante que PrefeituraAdmin não depende do import quebrado `app.models`."""
        import inspect

        source = inspect.getsource(PrefeituraAdmin.save_formset)
        self.assertNotIn("from app.models import", source)


class UserAdminFormPrefeituraTest(TestCase):
    def setUp(self):
        self.pref_a = Prefeitura.objects.create(
            nome_municipio="Municipio A",
            estado="SC",
            numero_usuarios_permitidos=5,
        )
        self.pref_b = Prefeitura.objects.create(
            nome_municipio="Municipio B",
            estado="SC",
            numero_usuarios_permitidos=2,
        )
        self.sec_a = Secretaria.objects.create(prefeitura=self.pref_a, nome="Sec A")
        self.sec_b = Secretaria.objects.create(prefeitura=self.pref_b, nome="Sec B")
        self.user = User.objects.create_user(
            email="moveme@test.com",
            prefeitura=self.pref_a,
            secretaria=self.sec_a,
        )
        User.objects.create_user(
            email="b1@test.com",
            prefeitura=self.pref_b,
            secretaria=self.sec_b,
        )
        User.objects.create_user(
            email="b2@test.com",
            prefeitura=self.pref_b,
            secretaria=self.sec_b,
        )

    def _form_data(self, **overrides):
        data = {
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "prefeitura": str(self.pref_b.pk),
            "secretaria": str(self.sec_b.pk),
            "role": self.user.role,
            "allowed_modules": list(self.user.get_allowed_modules()),
            "is_active": "on",
            "is_staff": "",
            "is_superuser": "",
            "date_joined": self.user.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data.update(overrides)
        return data

    def test_form_rejects_move_to_prefeitura_at_limit(self):
        form = UserAdminForm(data=self._form_data(), instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("prefeitura", form.errors)

    def test_form_allows_move_when_target_has_capacity(self):
        self.pref_b.numero_usuarios_permitidos = 3
        self.pref_b.save()
        form = UserAdminForm(data=self._form_data(), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_secretaria_from_other_prefeitura(self):
        self.pref_b.numero_usuarios_permitidos = 5
        self.pref_b.save()
        form = UserAdminForm(
            data=self._form_data(secretaria=str(self.sec_a.pk)),
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("secretaria", form.errors)
