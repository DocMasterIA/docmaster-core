from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Rule

def LoginView(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login realizado com sucesso!")
            return redirect(reverse("dashboard"))
        else:
            messages.error(request, "E-mail ou senha inválidos.")

    return render(request, "login_portal.html")

def RegisterView(request):
    return render(request,"register_portal.html")

def LogoutView(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect(reverse("login_panel"))

def DashboardView(request):
    return render(request, "dashboard.html")

def AreaDoUsuarioView(request):
    return render(request,"area_do_usuario.html")

from django.shortcuts import render, get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Template, DocumentInstance, Rule
from .services import render_docx_from_template, generate_pdf_from_docx, assemble_document_context, get_snippets_for_data
from django.core.files import File
import os, traceback
from django.template.loader import render_to_string
import tempfile
from django.contrib import messages

ALLOWED_TEMPLATE_EXTENSIONS = ('.docx',)
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

@login_required
def DocumentGeneratorView(request):
    """
    View para gerar documento sem template_slug na URL.
    - GET: mostra formulário com lista de templates disponíveis.
    - POST: recebe `template_id` ou `template_file` (upload por admin),
            processa dados e gera docx/pdf.
    """

    # Lista de templates visíveis ao usuário (ajuste se quiser filtrar por dono/empresa)
    templates_qs = Template.objects.all().order_by('-created_at')

    # Variáveis para render
    form_data = {}
    document_ready = False
    download_url = None

    if request.method == "POST":
        # Leitura do template (prefer template_id; se não, tenta upload)
        template = None
        template_id = request.POST.get("template_id")
        uploaded_file = request.FILES.get("template_file")

        # 1) Se template_id foi enviado, usar esse template
        if template_id:
            try:
                template = Template.objects.get(pk=template_id)
            except Template.DoesNotExist:
                messages.error(request, "Template selecionado não encontrado.")
                return redirect(request.path)

        # 2) Caso contrário, se houver upload, e usuário for staff, criar Template
        elif uploaded_file:
            if not request.user.is_staff:
                messages.error(request, "Somente administradores podem enviar templates via upload.")
                return redirect(request.path)

            # valida extensão e tamanho
            name_lower = uploaded_file.name.lower()
            if not any(name_lower.endswith(ext) for ext in ALLOWED_TEMPLATE_EXTENSIONS):
                messages.error(request, "Formato inválido. Faça upload de um arquivo .docx.")
                return redirect(request.path)
            if uploaded_file.size > MAX_UPLOAD_SIZE:
                messages.error(request, "Arquivo muito grande. Limite %d MB." % (MAX_UPLOAD_SIZE // (1024*1024)))
                return redirect(request.path)

            # cria um Template simples salvo no banco (pode ajustar para save=False se quiser temporário)
            template = Template.objects.create(
                name=request.POST.get("template_name") or uploaded_file.name,
                slug=request.POST.get("template_slug") or None,
                description=request.POST.get("template_description", ""),
                file=uploaded_file,
            )

        else:
            messages.error(request, "Nenhum template selecionado ou arquivo enviado.")
            return redirect(request.path)

        # --- coleta dados do form (se você mudar para prompt-only, adapte este bloco) ---
        # Mantive os campos originais para compatibilidade com o form atual
        data = {
            "tipo_documento": request.POST.get("tipo_documento"),
            "modalidade": request.POST.get("modalidade"),
            "objeto": request.POST.get("objeto"),
            "orgao": request.POST.get("orgao"),
            "valor_estimado": request.POST.get("valor_estimado"),
            "prazo_execucao": request.POST.get("prazo_execucao"),
            "responsavel": request.POST.get("responsavel"),
            "observacoes": request.POST.get("observacoes"),
            # Caso venha JSON do agente IA, você pode também tentar:
            # "ai_payload": json.loads(request.POST.get('ai_payload') or '{}')
        }

        # preenchendo form_data para re-render caso erro
        form_data = data.copy()

        # --- seleciona snippets pela regra (aqui mantive regra por 'modalidade') ---
        # get_snippets_for_data já retorna dict com áreas
        snippets_dict = get_snippets_for_data(data)  # {"intro": [...], "clause": [...], "conclusion": [...]}

        # --- monta contexto final para o template ---
        context = assemble_document_context(data)
        context['template'] = template
        # converte para listas de conteúdo se for necessário no template
        context['snippets_intro'] = [s.content for s in snippets_dict.get('intro', [])]
        context['snippets_clause'] = [s.content for s in snippets_dict.get('clause', [])]
        context['snippets_conclusion'] = [s.content for s in snippets_dict.get('conclusion', [])]

        action = request.POST.get("action", "finalize")  # "save" ou "finalize"

        # --- cria DocumentInstance como rascunho ---
        inst = DocumentInstance.objects.create(
            template=template,
            owner=request.user,
            data=data,
            status="draft"
        )

        if action == "finalize":
            tmpdir = tempfile.gettempdir()
            try:
                # --- gera DOCX ---
                docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)

                # --- gera PDF ---
                pdf_path = generate_pdf_from_docx(docx_path)

                # --- salva nos FileFields ---
                with open(docx_path, "rb") as f:
                    inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
                with open(pdf_path, "rb") as f:
                    inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

                inst.status = "final"
                inst.save()

                messages.success(request, "Documento finalizado e arquivos gerados com sucesso.")
                document_ready = True
                download_url = inst.file_pdf.url if inst.file_pdf else inst.file_docx.url

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Erro ao gerar arquivos: {e}")

        else:
            messages.success(request, "Rascunho salvo com sucesso.")

    # GET (ou re-render após POST)
    return render(request, "document_generator.html", {
        "templates": templates_qs,
        "form_data": form_data,
        "document_ready": document_ready,
        "document_download_url": download_url,
    })
