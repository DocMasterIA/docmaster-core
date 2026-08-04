"""Testes da API de alteração de senha do usuário logado."""
from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class ChangePasswordApiTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(
            email="usuario@teste.local",
            password="SenhaAtual123!",
            first_name="Usuario",
            last_name="Teste",
        )
        self.client.force_login(self.user)
        self.url = "/api/me/password/"

    def test_requires_authentication(self):
        self.client.logout()
        res = self.client.post(
            self.url,
            data=json.dumps({"current_password": "x", "new_password": "y", "confirm_password": "y"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)

    def test_success_changes_password(self):
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaAtual123!",
                "new_password": "NovaSenha456!",
                "confirm_password": "NovaSenha456!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload.get("ok"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha456!"))
        self.assertFalse(self.user.check_password("SenhaAtual123!"))

    def test_wrong_current_password(self):
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "Errada!",
                "new_password": "NovaSenha456!",
                "confirm_password": "NovaSenha456!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("current_password", errors)

    def test_mismatch_confirmation(self):
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaAtual123!",
                "new_password": "NovaSenha456!",
                "confirm_password": "OutraSenha789!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("new_password2", errors)

    def test_same_as_current_password(self):
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaAtual123!",
                "new_password": "SenhaAtual123!",
                "confirm_password": "SenhaAtual123!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("new_password1", errors)

    def test_weak_password_rejected(self):
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaAtual123!",
                "new_password": "123",
                "confirm_password": "123",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("new_password1", errors)

    def test_rate_limit_after_wrong_current_password(self):
        payload = json.dumps({
            "current_password": "Errada!",
            "new_password": "NovaSenha456!",
            "confirm_password": "NovaSenha456!",
        })
        for _ in range(5):
            res = self.client.post(self.url, data=payload, content_type="application/json")
            self.assertEqual(res.status_code, 400)

        res = self.client.post(self.url, data=payload, content_type="application/json")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Muitas tentativas", res.json().get("error", ""))

    def test_weak_new_password_does_not_trigger_lock(self):
        payload = json.dumps({
            "current_password": "SenhaAtual123!",
            "new_password": "123",
            "confirm_password": "123",
        })
        for _ in range(6):
            res = self.client.post(self.url, data=payload, content_type="application/json")
            self.assertEqual(res.status_code, 400)

    def test_oversized_password_rejected(self):
        long_pwd = "A" * 129 + "1!"
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaAtual123!",
                "new_password": long_pwd,
                "confirm_password": long_pwd,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("new_password1", errors)

    def test_unusable_password_cannot_self_change(self):
        self.user.set_unusable_password()
        self.user.save(update_fields=["password"])
        self.client.force_login(self.user)
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "qualquer",
                "new_password": "NovaSenha456!",
                "confirm_password": "NovaSenha456!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        errors = res.json().get("errors") or {}
        self.assertIn("current_password", errors)
        msg = " ".join(str(x) for x in errors["current_password"])
        self.assertIn("administrador", msg.lower())

    def test_plaintext_corrupted_hash_fails_current_password(self):
        """Simula admin que salvou senha em texto puro no campo password."""
        User.objects.filter(pk=self.user.pk).update(password="SenhaEmTextoPuro123!")
        self.user.refresh_from_db()
        self.client.force_login(self.user)
        res = self.client.post(
            self.url,
            data=json.dumps({
                "current_password": "SenhaEmTextoPuro123!",
                "new_password": "NovaSenha456!",
                "confirm_password": "NovaSenha456!",
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("current_password", res.json().get("errors") or {})
