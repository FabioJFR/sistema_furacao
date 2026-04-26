from plataforma.models import Empresa, PerfilPlataforma
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

    perfil = obter_perfil_ativo_por_user(user)
    if perfil and perfil.tipo_acesso == "individual":
        individual = obter_individual_por_user(user)
        nome_base = (
            (individual.nome if individual else "").strip()
            or (user.get_full_name() or "").strip()
            or user.username
            or user.email
            or "Conta Individual"
        )
        email_base = (
            (individual.email if individual else "").strip()
            or (user.email or "").strip()
        )
        telefone_base = (individual.telefone if individual else None) or ""

        empresa_nome = f"Individual · {nome_base} · {user.pk}"
        empresa, _ = Empresa.objects.get_or_create(
            nome=empresa_nome,
            defaults={
                "nome_comercial": nome_base,
                "email": email_base,
                "telefone": telefone_base,
                "status": "teste",
                "ativo": True,
                "observacoes": "Empresa técnica criada automaticamente para conta individual.",
            },
        )

        empregado = Empregados.objects.create(
            user=user,
            empresa=empresa,
            nome=nome_base,
            email=email_base,
            telefone=telefone_base,
            funcao="outro",
            aprovado=True,
        )
        return empregado, True

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
