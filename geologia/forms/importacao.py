import json

from django import forms

from geologia.models import MissaoDroneFuro
from projetos.models import Furo


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


class ImportarMissaoDroneForm(forms.Form):
    furo = forms.ModelChoiceField(
        queryset=Furo.objects.none(),
        widget=forms.Select(attrs={"class": "border rounded px-3 py-2 w-full"}),
        label="Furo",
    )
    ficheiro_metadados = forms.FileField(
        widget=forms.FileInput(attrs={"class": "border rounded px-3 py-2 w-full", "accept": ".json,.txt"}),
        label="Ficheiro de metadados DJI",
        help_text="Importa um ficheiro JSON ou TXT exportado do voo para gerar uma missao automaticamente.",
    )
    titulo = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "border rounded px-3 py-2 w-full"}),
        label="Titulo da missao",
        help_text="Opcional. Se vazio, o titulo sera gerado com base no furo e nos metadados.",
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
        queryset = Furo.objects.select_related("projeto").order_by("projeto__nome", "nome")
        if empresa_id is not None:
            queryset = queryset.filter(empresa_id=empresa_id)
        self.fields["furo"].queryset = queryset

    def clean_ficheiro_metadados(self):
        ficheiro = self.cleaned_data.get("ficheiro_metadados")
        if not ficheiro:
            raise forms.ValidationError("Seleciona um ficheiro de metadados para importar.")

        try:
            conteudo = ficheiro.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise forms.ValidationError("O ficheiro de metadados deve estar em UTF-8.") from exc

        try:
            dados = json.loads(conteudo)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Ficheiro JSON invalido: {exc.msg}") from exc

        if not isinstance(dados, dict):
            raise forms.ValidationError("O ficheiro de metadados deve conter um objeto JSON.")

        return dados

    def save(self):
        metadados = self.cleaned_data["ficheiro_metadados"]
        furo = self.cleaned_data["furo"]
        titulo = self.cleaned_data.get("titulo", "").strip()

        missao = MissaoDroneFuro(
            empresa=furo.empresa,
            furo=furo,
            status="importada",
            titulo=titulo or f"Importacao DJI Mini 4 Pro - {furo.nome}",
        )
        missao.aplicar_metadados_importados(metadados)

        if not missao.titulo:
            missao.titulo = f"Importacao DJI Mini 4 Pro - {furo.nome}"

        missao.save()
        return missao
