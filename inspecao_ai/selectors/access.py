from plataforma.models import Empresa, PerfilPlataforma


ADMIN_TIPOS_ACESSO_EMPRESA = ("empresa_admin", "empresa_gestor")


def listar_empresas_inspecao_qs():
    return Empresa.objects.all().order_by("nome")


def obter_primeira_empresa_inspecao():
    return listar_empresas_inspecao_qs().first()


def obter_empresa_inspecao_por_id(empresa_id):
    if not empresa_id:
        return None
    return listar_empresas_inspecao_qs().filter(pk=empresa_id).first()


def obter_perfil_admin_inspecao(user):
    return (
        PerfilPlataforma.objects.filter(
            user=user,
            ativo=True,
            tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
        )
        .select_related("empresa")
        .first()
    )
