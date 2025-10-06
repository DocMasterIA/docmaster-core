from django import forms
from backend.app.models import Template
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

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
