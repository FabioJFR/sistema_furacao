from projetos.models import Furo, Projeto


def obter_querysets_analise_form(empresa=None):
    if empresa is None:
        return Projeto.objects.none(), Furo.objects.none()
    projetos_qs = Projeto.objects.filter(empresa=empresa).order_by("nome")
    furos_qs = Furo.objects.filter(empresa=empresa).select_related("projeto").order_by("projeto__nome", "nome")
    return projetos_qs, furos_qs
