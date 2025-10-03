# @login_required
# def DocumentGeneratorView(request, template_slug):
#     template = get_object_or_404(Template, slug=template_slug)

#     if request.method == "POST":
#         # --- coleta dados do form ---
#         data = {
#             "tipo_documento": request.POST.get("tipo_documento"),
#             "modalidade": request.POST.get("modalidade"),
#             "objeto": request.POST.get("objeto"),
#             "orgao": request.POST.get("orgao"),
#             "valor_estimado": request.POST.get("valor_estimado"),
#             "prazo_execucao": request.POST.get("prazo_execucao"),
#             "responsavel": request.POST.get("responsavel"),
#             "observacoes": request.POST.get("observacoes"),
#         }

#         # --- seleciona snippets pela regra ---
#         snippets = []
#         rule = Rule.objects.filter(field_name="modalidade", match_value=data["modalidade"]).first()
#         if rule:
#             snippets.extend(rule.snippets.all())

#         # --- monta contexto final para o template ---
#         context = assemble_document_context(data)
#         context['template'] = template  
#         context.update(get_snippets_for_data(data))  
#         action = request.POST.get("action", "finalize")  # "save" ou "finalize"

#         # --- cria DocumentInstance como rascunho ---
#         inst = DocumentInstance.objects.create(
#             template=template,
#             owner=request.user,
#             data=data,
#             status="draft"
#         )

#         if action == "finalize":
#             tmpdir = tempfile.gettempdir()
#             try:
#                 # --- gera DOCX ---
#                 docx_path = render_docx_from_template(template.file.path, context, dest_dir=tmpdir)

#                 # --- gera PDF ---
#                 pdf_path = generate_pdf_from_docx(docx_path)

#                 # --- salva nos FileFields ---
#                 with open(docx_path, "rb") as f:
#                     inst.file_docx.save(os.path.basename(docx_path), File(f), save=False)
#                 with open(pdf_path, "rb") as f:
#                     inst.file_pdf.save(os.path.basename(pdf_path), File(f), save=False)

#                 inst.status = "final"
#                 inst.save()

#                 messages.success(request, "Documento finalizado e arquivos gerados com sucesso.")

#             except Exception as e:
#                 traceback.print_exc()
#                 messages.error(request, f"Erro ao gerar arquivos: {e}")

#         else:
#             messages.success(request, "Rascunho salvo com sucesso.")

#     # GET: renderiza form
#     return render(request, "document_generator.html", {
#         "template": template,
#         "form_data": data if request.method == "POST" else {}
#     })



