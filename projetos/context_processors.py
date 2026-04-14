from projetos.models import Empregados


def menu_context(request):
    user = request.user

    if not user.is_authenticated:
        return {
            "is_admin_user": False,
            "is_empregado_user": False,
            "empregado_menu_obj": None,
        }

    is_admin_user = user.is_staff
    empregado_menu_obj = Empregados.objects.filter(user=user).first()
    is_empregado_user = empregado_menu_obj is not None and not is_admin_user

    return {
        "is_admin_user": is_admin_user,
        "is_empregado_user": is_empregado_user,
        "empregado_menu_obj": empregado_menu_obj,
    }