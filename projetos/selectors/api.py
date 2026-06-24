from django.shortcuts import get_object_or_404

from plataforma.models import Empresa, PerfilPlataforma
from projetos.models import Empregados, Furo, FuroVersao


ADMIN_TIPOS_ACESSO_EMPRESA = ("empresa_admin", "empresa_gestor")


def resolver_empresa_api(user, *, empresa_id=""):
    if user.is_superuser:
        empresas = Empresa.objects.all().order_by("nome")
        if empresa_id:
            empresa = empresas.filter(pk=empresa_id).first()
            if empresa:
                return empresa, None
            return None, "empresa_invalida"
        empresa = empresas.first()
        if empresa:
            return empresa, None
        return None, "sem_empresas"

    perfil = (
        PerfilPlataforma.objects.filter(
            user=user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
        )
        .select_related("empresa")
        .first()
    )
    if perfil and perfil.empresa_id:
        return perfil.empresa, None

    empregado = (
        Empregados.objects.filter(user=user, aprovado=True)
        .select_related("empresa")
        .first()
    )
    if empregado and empregado.empresa_id:
        return empregado.empresa, None

    return None, "sem_empresa_associada"


def listar_furos_api_qs(empresa):
    return Furo.objects.filter(empresa=empresa).select_related("projeto").order_by("-data", "nome")


def obter_furo_api(pk, empresa):
    return get_object_or_404(Furo.objects.select_related("projeto"), pk=pk, empresa=empresa)


def listar_versoes_furo_api_qs(furo, empresa):
    return (
        FuroVersao.objects.filter(furo=furo, empresa=empresa)
        .select_related("projeto", "furo", "criado_por")
        .order_by("-versao_numero")
    )
