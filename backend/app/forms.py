from django import forms
from backend.app.models import Template

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