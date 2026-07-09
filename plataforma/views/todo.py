from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from plataforma.decorators import platform_admin_required
from plataforma.selectors.todo import (
    listar_todo_areas,
    obter_notas_transversais_todo,
    obter_todo_area,
)


@login_required
@platform_admin_required
def todo_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, _("Esta área está reservada ao superutilizador."))
        return redirect("plataforma:dashboard")

    context = {
        "areas": listar_todo_areas(),
        "notas": obter_notas_transversais_todo(),
    }
    return render(request, "plataforma/todo_dashboard.html", context)


@login_required
@platform_admin_required
def todo_area_detail(request, area_slug):
    if not request.user.is_superuser:
        messages.error(request, _("Esta área está reservada ao superutilizador."))
        return redirect("plataforma:dashboard")

    context = {
        "area": obter_todo_area(area_slug),
        "notas": obter_notas_transversais_todo(),
    }
    return render(request, "plataforma/todo_area_detail.html", context)
