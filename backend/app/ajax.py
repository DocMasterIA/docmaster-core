from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import DocumentInstance
from django.core.paginator import Paginator

@login_required
def area_do_usuario_ajax(request):
    user = request.user
    query = request.GET.get("q", "")
    page_number = request.GET.get("page", 1)

    docs = DocumentInstance.objects.filter(owner=user)
    if query:
        docs = docs.filter(template__name__icontains=query)

    docs = docs.order_by("-updated_at")
    paginator = Paginator(docs, 10)
    page_obj = paginator.get_page(page_number)

    html = render_to_string("partials/document_list.html", {"page_obj": page_obj})
    return JsonResponse({"html": html})
