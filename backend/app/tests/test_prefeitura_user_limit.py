from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from backend.app.admin import (
    PrefeituraAdmin,
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
