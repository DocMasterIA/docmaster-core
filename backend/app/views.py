from django.http import HttpResponse
from backend.app.models import Template, DocumentInstance
from django.db.models import Q


def favicon_view(request):
    """
    Responde a /favicon.ico para evitar que dispare fluxos de login.
    Mantido apenas para evitar 404 no frontend/Vue.
    """
    return HttpResponse(status=204)


def dashboard_callback(request, context):
    """
    Callback usado pelo painel admin para montar métricas (cards, gráficos, listas).
    Mantido para não quebrar o admin; não renderiza HTML custom.
    """
    from django.db.models import Count
    from django.contrib.auth import get_user_model

    User = get_user_model()

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    templates = Template.objects.all()
    documents = DocumentInstance.objects.all()
    users = User.objects.all()

    if start_date:
        documents = documents.filter(created_at__date__gte=start_date)
    if end_date:
        documents = documents.filter(created_at__date__lte=end_date)

    top_users_qs = (
        User.objects.annotate(
            doc_count=Count("documentinstance", filter=Q(documentinstance__in=documents))
        ).order_by("-doc_count")[:5]
    )

    context.update(
        {
            "total_users": users.count(),
            "active_users": users.filter(is_active=True).count(),
            "inactive_users": users.filter(is_active=False).count(),
            "total_templates": templates.count(),
            "template_names": [t.name for t in templates],
            "documents_per_template": [documents.filter(template=t).count() for t in templates],
            "total_documents": documents.count(),
            "documents_finalizados": documents.filter(status="final").count(),
            "latest_documents": documents.order_by("-created_at")[:5],
            "top_users": top_users_qs,
            "top_users_names": [u.email for u in top_users_qs],
            "top_users_docs": [u.doc_count for u in top_users_qs],
        }
    )

    context["cards"] = [
        {"title": "Usuários", "value": users.count(), "chart": "chartUsers", "bg": "oklch(62.7% .28 235)"},
        {"title": "Templates", "value": templates.count(), "chart": "chartTemplates", "bg": "oklch(55.8% .29 235)"},
        {"title": "Documentos", "value": documents.count(), "chart": "chartDocuments", "bg": "oklch(49.6% .27 235)"},
    ]

    return context

