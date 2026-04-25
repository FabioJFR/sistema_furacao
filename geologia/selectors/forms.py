from geologia.models import ModuloDroneSF
from projetos.models import Furo, Medicao


def resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def listar_furos_importacao_qs(empresa=None):
    queryset = Furo.objects.select_related("projeto").order_by("projeto__nome", "nome")
    if empresa is not None:
        queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
    return queryset


def listar_medicoes_furo_qs(furo):
    if furo is None:
        return Medicao.objects.none()
    return Medicao.objects.filter(furo=furo).order_by("-criado_em", "-profundidade_medida")


def listar_missoes_furo_qs(furo):
    if furo is None:
        return []
    return furo.missoes_drone_geologia.all().order_by("-data_voo", "-criado_em")


def listar_modulos_sensor_form_qs(drone=None):
    if drone is None:
        return ModuloDroneSF.objects.none()
    return drone.modulos.all().order_by("tipo", "nome")
