from projetos.models import PreferenciasUser


def obter_ou_criar_preferencias_user(user):
    return PreferenciasUser.objects.get_or_create(user=user)


def garantir_preferencias_empresa(preferencias, empresa):
    if preferencias.empresa_id == getattr(empresa, "pk", empresa):
        return preferencias

    preferencias.empresa = empresa
    preferencias.save(update_fields=["empresa"])
    return preferencias
