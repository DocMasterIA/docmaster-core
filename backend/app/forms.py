from django import forms
from backend.app.models import Template
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import MaxLengthValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from backend.app.services.auth_security import PASSWORD_MAX_LENGTH

class TemplateUploadForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ["name", "file"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 border rounded-xl",
                "placeholder": "Nome do Documento"
            }),
            "file": forms.ClearableFileInput(attrs={
                "class": "w-full px-4 py-3 border rounded-xl"
            }),
        }
        labels = {
            "name": "Nome do Template",
            "file": "Arquivo do Documento (.docx)"
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.endswith(".docx"):
            raise forms.ValidationError("O arquivo precisa ser .docx")
        return uploaded_file
    

class LoginForm(forms.Form):
    email_or_username = forms.CharField(
        label=_("Email ou usuário"),
        widget=forms.TextInput(attrs={"autocomplete": "username", "class":"form-input"}),
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class":"form-input"}),
    )
    remember = forms.BooleanField(label=_("Lembrar de mim"), required=False)

    # opcional: token do reCAPTCHA (se usar)
    recaptcha_token = forms.CharField(widget=forms.HiddenInput(), required=False)

    error_messages = {
        "invalid_login": _("E-mail/usuário ou senha inválidos."),
        "inactive": _("Conta inativa. Verifique seu e-mail para ativar."),
        "locked": _("Muitas tentativas inválidas. Tente novamente em alguns minutos."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        self.user_cache = None

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("email_or_username")
        password = cleaned.get("password")

        if username and password:
            # você pode autenticar por email ou username
            # primeiro resgata usuário por e-mail se houver
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_qs = User.objects.filter(email__iexact=username)
            if user_qs.exists():
                # pega primeiro usuário com esse e-mail
                candidate = user_qs.first().get_username()
                user = authenticate(self.request, username=candidate, password=password)
            else:
                # tenta autenticação por username diretamente
                user = authenticate(self.request, username=username, password=password)

            if user is None:
                raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")

            if not user.is_active:
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")

            self.user_cache = user
        return cleaned

    def get_user(self):
        return self.user_cache

User = get_user_model()

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput,
        min_length=8,
        help_text="Mínimo 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'organization']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')

        if p1 and p2 and p1 != p2:
            raise ValidationError("As senhas não conferem.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'profile_photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Sobrenome'}),
        }


class ChangePasswordForm(forms.Form):
    _password_validators = [MaxLengthValidator(PASSWORD_MAX_LENGTH)]

    current_password = forms.CharField(
        label=_("Senha atual"),
        strip=False,
        validators=_password_validators,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    new_password1 = forms.CharField(
        label=_("Nova senha"),
        strip=False,
        validators=_password_validators,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label=_("Confirmar nova senha"),
        strip=False,
        validators=_password_validators,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get("current_password")
        if not self.user.has_usable_password():
            raise ValidationError(
                _("Sua conta ainda não possui senha definida. Entre em contato com o administrador.")
            )
        if not self.user.check_password(current):
            raise ValidationError(_("Senha atual incorreta."))
        return current

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if password:
            validate_password(password, user=self.user)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", _("As senhas não conferem."))
        current = cleaned.get("current_password")
        if p1 and current and p1 == current:
            self.add_error("new_password1", _("A nova senha deve ser diferente da senha atual."))
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user