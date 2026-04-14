from django.contrib.auth.decorators import user_passes_test
from projetos.models import Empregados


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Administradores").exists()
    )


def is_empregado(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser or user.groups.filter(name="Administradores").exists():
        return False

    return Empregados.objects.filter(
        user=user,
        aprovado=True,
    ).exists()


def admin_required(view_func):
    return user_passes_test(is_admin, login_url="/login/")(view_func)


def empregado_required(view_func):
    return user_passes_test(is_empregado, login_url="/login/")(view_func)