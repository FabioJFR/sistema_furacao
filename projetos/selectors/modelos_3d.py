from core.permissions import user_is_global_admin
from projetos.selectors.acesso import obter_empregado_por_user, obter_perfil_ativo_por_user


def resolver_empresa_modelos_3d(user):
    if user_is_global_admin(user):
        return None

    perfil = obter_perfil_ativo_por_user(user)
    if perfil and perfil.empresa_id:
        return perfil.empresa

    empregado = obter_empregado_por_user(user)
    if empregado and empregado.aprovado and empregado.empresa_id:
        return empregado.empresa

    return None


def obter_queryset_modelos_3d_autorizado(model_cls, user):
    qs = model_cls.objects.all()
    if user_is_global_admin(user):
        return qs

    empresa = resolver_empresa_modelos_3d(user)
    if not empresa:
        return qs.none()

    return qs.filter(empresa=empresa)
