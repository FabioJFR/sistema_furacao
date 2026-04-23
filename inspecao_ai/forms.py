from django import forms
import json

from projetos.models import Furo, Projeto

from .models import AnaliseImagemAI


class AnaliseImagemAIForm(forms.ModelForm):
    RELATORIO_FOCUS_CHOICES = [
        ("", "Relatório completo"),
        ("cabecalho", "Cabeçalho"),
        ("data", "Data"),
        ("turno", "Turno"),
        ("equipa", "Equipa"),
        ("observacoes", "Observações"),
        ("rodape", "Rodapé"),
    ]

    ROTACAO_CHOICES = [
        ("0", "Sem rotação manual"),
        ("-15", "Rodar -15°"),
        ("-10", "Rodar -10°"),
        ("-5", "Rodar -5°"),
        ("5", "Rodar +5°"),
        ("10", "Rodar +10°"),
        ("15", "Rodar +15°"),
        ("90", "Rodar +90°"),
        ("180", "Rodar 180°"),
        ("270", "Rodar 270°"),
    ]

    auto_corrigir_inclinacao = forms.BooleanField(
        required=False,
        initial=True,
        label="Corrigir inclinação automaticamente",
    )
    rotacao_manual = forms.ChoiceField(
        choices=ROTACAO_CHOICES,
        required=False,
        initial="0",
        label="Rotação manual",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    area_x_percent = forms.FloatField(
        required=False,
        min_value=0,
        max_value=100,
        initial=0,
        label="Área X (%)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "100"}),
    )
    area_y_percent = forms.FloatField(
        required=False,
        min_value=0,
        max_value=100,
        initial=0,
        label="Área Y (%)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "100"}),
    )
    area_w_percent = forms.FloatField(
        required=False,
        min_value=0,
        max_value=100,
        initial=100,
        label="Área largura (%)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "100"}),
    )
    area_h_percent = forms.FloatField(
        required=False,
        min_value=0,
        max_value=100,
        initial=100,
        label="Área altura (%)",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "min": "0", "max": "100"}),
    )
    relatorio_focus = forms.ChoiceField(
        choices=RELATORIO_FOCUS_CHOICES,
        required=False,
        initial="",
        label="Campo prioritário do relatório",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    report_zone_json = forms.CharField(required=False, widget=forms.HiddenInput())
    custom_text_zones_json = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = AnaliseImagemAI
        fields = [
            "nome",
            "tipo_documento",
            "projeto",
            "furo",
            "imagem_original",
            "observacoes",
        ]
        widgets = {
            "nome": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex.: Caixa NQ Furo 3 - Foto 01"}
            ),
            "tipo_documento": forms.Select(attrs={"class": "form-control"}),
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "imagem_original": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Notas sobre a fotografia, caixa, marcador ou contexto do registo.",
                }
            ),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        if empresa is not None and not self.instance.empresa_id:
            self.instance.empresa = empresa

        projetos_qs = Projeto.objects.none()
        furos_qs = Furo.objects.none()
        if empresa is not None:
            projetos_qs = Projeto.objects.filter(empresa=empresa).order_by("nome")
            furos_qs = Furo.objects.filter(empresa=empresa).select_related("projeto").order_by(
                "projeto__nome", "nome"
            )

        self.fields["projeto"].queryset = projetos_qs
        self.fields["furo"].queryset = furos_qs
        self.fields["projeto"].required = False
        self.fields["furo"].required = False

    def clean(self):
        cleaned_data = super().clean()
        projeto = cleaned_data.get("projeto")
        furo = cleaned_data.get("furo")
        area_x = cleaned_data.get("area_x_percent")
        area_y = cleaned_data.get("area_y_percent")
        area_w = cleaned_data.get("area_w_percent")
        area_h = cleaned_data.get("area_h_percent")
        report_zone_json = cleaned_data.get("report_zone_json") or ""
        custom_text_zones_json = cleaned_data.get("custom_text_zones_json") or ""

        if furo and projeto and furo.projeto_id != projeto.pk:
            self.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")

        if any(value is not None for value in (area_x, area_y, area_w, area_h)):
            area_x = float(area_x or 0)
            area_y = float(area_y or 0)
            area_w = float(area_w or 0)
            area_h = float(area_h or 0)

            if area_w <= 0 or area_h <= 0:
                raise forms.ValidationError("A área prioritária precisa de largura e altura superiores a 0.")
            if area_x + area_w > 100.0 + 1e-6 or area_y + area_h > 100.0 + 1e-6:
                raise forms.ValidationError("A área prioritária deve caber dentro da imagem (0-100%).")

        cleaned_data["report_zone"] = self._clean_zone_json(report_zone_json, single=True, label="zona do relatório")
        cleaned_data["custom_text_zones"] = self._clean_zone_json(
            custom_text_zones_json,
            single=False,
            label="zonas personalizadas de leitura",
        )

        return cleaned_data

    def _clean_zone_json(self, raw_value, *, single, label):
        if not raw_value:
            return None if single else []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Não foi possível interpretar {label}.") from exc

        zones = [parsed] if single and isinstance(parsed, dict) else parsed
        if not isinstance(zones, list):
            raise forms.ValidationError(f"O formato de {label} é inválido.")

        cleaned = []
        for index, zone in enumerate(zones, start=1):
            if not isinstance(zone, dict):
                raise forms.ValidationError(f"A zona {index} de {label} é inválida.")
            try:
                x = float(zone.get("x_percent", 0))
                y = float(zone.get("y_percent", 0))
                w = float(zone.get("w_percent", 0))
                h = float(zone.get("h_percent", 0))
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"A zona {index} de {label} tem coordenadas inválidas.") from exc
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > 100.0 + 1e-6 or y + h > 100.0 + 1e-6:
                raise forms.ValidationError(f"A zona {index} de {label} está fora dos limites da imagem.")

            item = {
                "x_percent": round(x, 2),
                "y_percent": round(y, 2),
                "w_percent": round(w, 2),
                "h_percent": round(h, 2),
            }
            nome = (zone.get("name") or "").strip()
            if nome:
                item["name"] = nome[:80]
            cleaned.append(item)

        return cleaned[0] if single else cleaned
