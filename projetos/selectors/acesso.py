from plataforma.models import PerfilPlataforma
from projetos.models import Empregados, Individual


ADMIN_TIPOS_ACESSO_EMPRESA = ("empresa_admin", "empresa_gestor")


def obter_contexto_admin_projetos(user):
    return (
        PerfilPlataforma.objects.filter(
            user=user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
        )
        .select_related("empresa")
        .first()
    )


def obter_empregado_por_user(user):
    return Empregados.objects.filter(user=user).select_related("empresa").first()


def resolver_empregado_por_user_ou_email(user):
    empregado = obter_empregado_por_user(user)
    if empregado:
        return empregado, False

    email = (getattr(user, "email", "") or "").strip()
    if not email:
        return None, False

    candidatos = Empregados.objects.filter(
        email__iexact=email,
        user__isnull=True,
    ).select_related("empresa")

    if candidatos.count() != 1:
        return None, False

    empregado = candidatos.first()
    empregado.user = user
    empregado.save(update_fields=["user"])
    return empregado, True


def obter_individual_por_user(user):
    return Individual.objects.filter(user=user).first()


def obter_perfil_ativo_por_user(user):
    return PerfilPlataforma.objects.filter(
        user=user,
        ativo=True,
    ).first()
