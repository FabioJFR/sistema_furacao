from django import forms

from geologia.models import FonteCartograficaGeologica


class FonteCartograficaGeologicaForm(forms.ModelForm):
    class Meta:
        model = FonteCartograficaGeologica
        fields = [
            "nome",
            "descricao",
            "pais_regiao",
            "tipo_servico",
            "url_servico",
            "layer_names",
            "attribution",
            "formato_imagem",
            "transparencia",
            "opacidade",
            "centro_latitude",
            "centro_longitude",
            "zoom_inicial",
            "visivel_por_defeito",
            "ativo",
            "ordem",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "opacidade": forms.NumberInput(attrs={"step": "0.05", "min": "0", "max": "1"}),
            "centro_latitude": forms.NumberInput(attrs={"step": "0.000001", "min": "-90", "max": "90"}),
            "centro_longitude": forms.NumberInput(attrs={"step": "0.000001", "min": "-180", "max": "180"}),
            "zoom_inicial": forms.NumberInput(attrs={"min": "0", "max": "22"}),
            "ordem": forms.NumberInput(attrs={"min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {base_class}".strip()
        self.fields["nome"].help_text = "Ex.: Carta geológica Espanha 1:50 000"
        self.fields["pais_regiao"].help_text = "Ex.: Portugal, Espanha, Chile, Açores"
        self.fields["tipo_servico"].help_text = "WMS para serviços cartográficos; Tile XYZ para tiles prontos."
        self.fields["url_servico"].help_text = "Para WMS usa o endpoint do serviço; para Tile XYZ usa o template com {z}, {x} e {y}. Evita credenciais embutidas na URL."
        self.fields["layer_names"].help_text = "Obrigatório em WMS. Ex.: 2 ou geologia,estruturas"
        self.fields["attribution"].help_text = "Texto curto da fonte. Ex.: Fonte: LNEG"
        self.fields["centro_latitude"].help_text = "Opcional. Ajuda o mapa a abrir logo na zona certa."
        self.fields["centro_longitude"].help_text = "Opcional. Usa em conjunto com a latitude."
        self.fields["zoom_inicial"].help_text = "Opcional. Ex.: 6 para país, 10-12 para região, 13+ para detalhe local."
