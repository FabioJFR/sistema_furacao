from django.shortcuts import get_object_or_404

from dispositivos.models import Dispositivo, LeituraBrutaDispositivo, SessaoDispositivo, SurveyShot
from plataforma.models import Empresa
from projetos.models import Empregados, Furo


def filtrar_por_empresa_id(queryset, empresa_id=None):
    if empresa_id:
        return queryset.filter(empresa_id=empresa_id)
    return queryset


def resolver_empresa_para_registo_por_furo(furo_id):
    if furo_id:
        furo = get_object_or_404(Furo.objects.select_related("empresa", "projeto__empresa"), pk=furo_id)
        empresa = furo.empresa or getattr(furo.projeto, "empresa", None)
        if empresa:
            return empresa

    empresas = Empresa.objects.filter(ativo=True).order_by("nome")
    if empresas.count() == 1:
        return empresas.first()
    raise ValueError("Selecione um furo com empresa associada para guardar o dispositivo.")


def obter_dispositivo_ativo(dispositivo_id, empresa_id=None):
    qs = filtrar_por_empresa_id(Dispositivo.objects.filter(ativo=True), empresa_id)
    return get_object_or_404(qs, pk=dispositivo_id)


def obter_furo(furo_id, empresa_id=None):
    qs = filtrar_por_empresa_id(Furo.objects.all(), empresa_id)
    return get_object_or_404(qs, pk=furo_id)


def obter_empregado_por_user_empresa(user, empresa_id=None):
    qs = Empregados.objects.filter(user=user).select_related("empresa")
    if empresa_id:
        qs = qs.filter(empresa_id=empresa_id)
    return qs.first()


def obter_dispositivos_qs(empresa_id=None):
    return filtrar_por_empresa_id(Dispositivo.objects.all(), empresa_id)


def obter_sessoes_qs(empresa_id=None):
    return filtrar_por_empresa_id(SessaoDispositivo.objects.all(), empresa_id)


def obter_leituras_qs(empresa_id=None):
    return filtrar_por_empresa_id(LeituraBrutaDispositivo.objects.all(), empresa_id)


def obter_shots_qs(empresa_id=None):
    return filtrar_por_empresa_id(SurveyShot.objects.all(), empresa_id)


def obter_furos_qs(empresa_id=None):
    return filtrar_por_empresa_id(Furo.objects.all(), empresa_id)


def obter_sessao_detail(pk, empresa_id=None):
    qs = obter_sessoes_qs(empresa_id).select_related("dispositivo", "empresa", "empregado", "furo")
    return get_object_or_404(qs, pk=pk)


def obter_leitura_detail(pk, empresa_id=None):
    qs = obter_leituras_qs(empresa_id).select_related(
        "sessao",
        "empresa",
        "sessao__dispositivo",
        "sessao__furo",
        "sessao__empregado",
    )
    return get_object_or_404(qs, pk=pk)


def construir_contexto_captura_dispositivo(empresa_id=None):
    dispositivos = obter_dispositivos_qs(empresa_id).filter(ativo=True).order_by("nome")
    furos = obter_furos_qs(empresa_id).select_related("projeto").order_by("nome")
    sessoes_ativas = (
        obter_sessoes_qs(empresa_id)
        .filter(status__in=["criada", "ligando", "ligado"])
        .select_related("dispositivo", "furo", "empregado")
        .order_by("-iniciado_em")
    )
    sessoes_recentes = (
        obter_sessoes_qs(empresa_id)
        .select_related("dispositivo", "furo", "empregado")
        .order_by("-iniciado_em")[:10]
    )
    sessoes_importacao = (
        obter_sessoes_qs(empresa_id)
        .filter(furo__isnull=False)
        .select_related("dispositivo", "furo")
        .order_by("-iniciado_em")[:30]
    )
    return {
        "dispositivos": dispositivos,
        "furos": furos,
        "sessoes_ativas": sessoes_ativas,
        "sessoes_recentes": sessoes_recentes,
        "sessoes_importacao": sessoes_importacao,
    }


def anexar_sessao_ao_preview(preview_data, empresa_id=None):
    if not preview_data:
        return preview_data
    preview_sessao = None
    sessao_id = preview_data.get("sessao_id")
    if sessao_id:
        try:
            preview_sessao = obter_sessao_detail(pk=sessao_id, empresa_id=empresa_id)
        except Exception:
            preview_sessao = None
    preview_data["sessao"] = preview_sessao
    return preview_data
