from django import forms

from projetos.models import Despesa, Furo, Maquina, Projeto


class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = [
            "categoria",
            "tipo",
            "descricao",
            "valor",
            "data",
            "observacoes",
            "comprovativo",
            "projeto",
            "furo",
            "maquina",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, empresa=None, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["projeto"].required = False
        self.fields["furo"].required = False
        self.fields["maquina"].required = False

        if empresa is not None:
            self.fields["projeto"].queryset = Projeto.objects.filter(empresa=empresa).order_by("nome")
            self.fields["furo"].queryset = Furo.objects.filter(empresa=empresa).order_by("nome")
            self.fields["maquina"].queryset = Maquina.objects.filter(empresa=empresa).order_by("nome")

        if empregado is not None:
            projetos_ligacoes_ativas = (
                empregado.ligacoes_projetos.filter(ativo=True)
                .values_list("projeto_id", flat=True)
            )
            projetos_registos = empregado.registos_diarios.filter(
                projeto__isnull=False,
                empresa=empregado.empresa,
            ).values_list("projeto_id", flat=True)
            projetos_ids = set(projetos_ligacoes_ativas).union(set(projetos_registos))

            self.fields["projeto"].queryset = self.fields["projeto"].queryset.filter(pk__in=projetos_ids)
            self.fields["furo"].queryset = self.fields["furo"].queryset.filter(projeto_id__in=projetos_ids)
            self.fields["maquina"].queryset = self.fields["maquina"].queryset.filter(
                projeto_atual_id__in=projetos_ids
            ) | self.fields["maquina"].queryset.filter(projeto_atual__isnull=True)
