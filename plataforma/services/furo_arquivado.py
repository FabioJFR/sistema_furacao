from django.db import transaction
from django.utils import timezone

from plataforma.models import FuroArquivadoPlataforma


def _lista_values(qs, campos_excluir=None):
    campos_excluir = set(campos_excluir or [])
    campos = [
        f.name
        for f in qs.model._meta.concrete_fields
        if f.name not in campos_excluir
    ]
    return list(qs.values(*campos))


def construir_snapshot_completo_furo(furo):
    snapshot = {
        "furo": _lista_values(furo.__class__.objects.filter(pk=furo.pk))[0],
        "medicoes": _lista_values(furo.medicoes.all()),
        "registos_diarios": _lista_values(furo.registos_furo.all()),
        "versoes_furo": _lista_values(furo.versoes.all()),
        "ligacoes_empregados": _lista_values(furo.ligacoes_empregados.all()),
        "levantamentos_materiais": _lista_values(furo.levantamentos_materiais.all()),
        "devolucoes_materiais": _lista_values(furo.devolucoes_materiais.all()),
        "materiais_associados": _lista_values(furo.materiais.all()),
        "maquinas_associadas": _lista_values(furo.maquinas.all()),
    }
    return snapshot


@transaction.atomic
def arquivar_furo_na_plataforma(
    *,
    furo,
    terminado_por=None,
    versao_arquivo=None,
    snapshot_override=None,
    estado_no_arquivo=None,
):
    if versao_arquivo is None:
        ultima_versao = (
            FuroArquivadoPlataforma.objects.filter(furo_id_origem=furo.pk)
            .order_by("-versao_arquivo")
            .values_list("versao_arquivo", flat=True)
            .first()
            or 0
        )
        versao_arquivo = ultima_versao + 1

    return FuroArquivadoPlataforma.objects.create(
        empresa_id=furo.empresa_id,
        furo_id_origem=furo.pk,
        projeto_id_origem=furo.projeto_id,
        nome_furo=furo.nome or "",
        estado_no_arquivo=estado_no_arquivo or furo.estado or "concluido",
        versao_arquivo=versao_arquivo,
        terminado_por=terminado_por,
        terminado_em=timezone.now(),
        dados_snapshot=snapshot_override or construir_snapshot_completo_furo(furo),
    )
