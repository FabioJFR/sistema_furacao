from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Não tens permissão para aceder a esta área.")
        return redirect("projetos:area_empregado")

    return wrapper