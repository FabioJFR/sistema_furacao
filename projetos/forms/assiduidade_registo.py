from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from projetos.models import AssiduidadeRegisto, Empregados, Projeto
from projetos.selectors.forms import resolver_empresa_id


class AssiduidadeRegistoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["empregado"].queryset = Empregados.objects.none()
            self.fields["projeto"].queryset = Projeto.objects.none()
            return
        self.instance.empresa_id = empresa_id
        self.fields["empregado"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")

    class Meta:
        model = AssiduidadeRegisto
        fields = [
            "empregado",
            "projeto",
            "tipo",
            "estado",
            "data_inicio",
            "data_fim",
            "horas",
            "motivo",
            "notas",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class PedidoFeriasCalendarioForm(forms.Form):
    ano = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        widget=forms.HiddenInput(),
    )
    datas_selecionadas = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )
    motivo = forms.CharField(
        required=False,
        max_length=220,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ex.: férias planeadas / férias de verão",
            }
        ),
    )
    notas = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Notas opcionais para a empresa aprovar o pedido.",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["motivo"].widget.attrs.update(
            {
                "class": "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-800 shadow-sm focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-100",
            }
        )
        self.fields["notas"].widget.attrs.update(
            {
                "class": "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-800 shadow-sm focus:border-violet-400 focus:outline-none focus:ring-2 focus:ring-violet-100",
            }
        )

    def clean_datas_selecionadas(self):
        bruto = (self.cleaned_data.get("datas_selecionadas") or "").strip()
        if not bruto:
            raise ValidationError("Seleciona pelo menos um dia no calendário.")

        hoje = timezone.localdate()
        datas = []
        vistos = set()

        for item in bruto.split(","):
            valor = item.strip()
            if not valor:
                continue
            try:
                dia = date.fromisoformat(valor)
            except ValueError as exc:
                raise ValidationError("Existe pelo menos uma data inválida no pedido.") from exc
            if dia < hoje:
                raise ValidationError("Só é possível pedir férias para dias de hoje em diante.")
            if dia not in vistos:
                vistos.add(dia)
                datas.append(dia)

        if not datas:
            raise ValidationError("Seleciona pelo menos um dia no calendário.")

        return sorted(datas)

    def clean(self):
        cleaned_data = super().clean()
        ano = cleaned_data.get("ano")
        datas = cleaned_data.get("datas_selecionadas") or []
        if ano and datas:
            invalidas = [dia for dia in datas if dia.year != ano]
            if invalidas:
                raise ValidationError("Todas as datas selecionadas devem pertencer ao ano visível no calendário.")
        return cleaned_data
