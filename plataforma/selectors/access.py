from plataforma.models import PerfilPlataforma


def obter_perfil_plataforma_ativo(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return PerfilPlataforma.objects.filter(user=user, ativo=True).first()
