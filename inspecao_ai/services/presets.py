from inspecao_ai.models import AnaliseZonaPresetAI


def guardar_preset_zonas_service(*, empresa, user, nome, tipo_documento, zona_relatorio, zonas_texto):
    preset, _created = AnaliseZonaPresetAI.objects.update_or_create(
        empresa=empresa,
        tipo_documento=tipo_documento,
        nome=nome,
        defaults={
            "zona_relatorio": zona_relatorio or {},
            "zonas_texto": zonas_texto or [],
            "criado_por": user,
        },
    )
    return preset
