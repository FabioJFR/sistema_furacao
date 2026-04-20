from django import forms

from ..models.furo import Furo
from ..models.material import DevolucaoMaterial, LevantamentoMaterial, Material
from ..models.projeto import Projeto


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _validar_empresa_objeto(form, campo, objeto, empresa_id):
    if objeto and objeto.empresa_id != empresa_id:
        form.add_error(campo, f"O {campo} selecionado não pertence à empresa atual.")


def _validar_relacao_furo_projeto(form, projeto, furo):
    if furo and projeto and furo.projeto_id != projeto.id:
        form.add_error("furo", "O furo selecionado não pertence ao projeto.")


def _obter_queryset_projetos_empresa(empresa):
    if empresa is None:
        return Projeto.objects.none()

    empresa_id = _resolver_empresa_id(empresa)
    return Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")


def _obter_queryset_furos_por_projeto(projeto_id, empresa=None):
    queryset = Furo.objects.filter(projeto_id=projeto_id)

    if empresa is not None:
        queryset = queryset.filter(empresa_id=_resolver_empresa_id(empresa))

    return queryset.order_by("nome")


def _obter_queryset_furos_empregado(empregado, empresa=None):
    if not empregado:
        return Furo.objects.none()

    projetos_atuais = empregado.projetos_atuais
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

    if empresa_id is not None:
        projetos_atuais = projetos_atuais.filter(empresa_id=empresa_id)
        return Furo.objects.filter(
            empresa_id=empresa_id,
            projeto__in=projetos_atuais,
        ).distinct().order_by("nome")

    return Furo.objects.filter(projeto__in=projetos_atuais).distinct().order_by("nome")


def _obter_queryset_projetos_empregado(empregado, empresa=None):
    if not empregado:
        return Projeto.objects.none()

    projetos_atuais = empregado.projetos_atuais
    if empresa is not None:
        projetos_atuais = projetos_atuais.filter(empresa_id=_resolver_empresa_id(empresa))

    return projetos_atuais


class SaidaMaterialForm(forms.Form):
    quantidade = forms.IntegerField(min_value=1, label="Quantidade a retirar")


class EntradaMaterialForm(forms.Form):
    quantidade = forms.IntegerField(min_value=1, label="Quantidade a adicionar")


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = "__all__"
        widgets = {
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "numero_serie": forms.TextInput(attrs={"class": "form-control"}),
            "quantidade": forms.NumberInput(attrs={"class": "form-control"}),
            "unidade": forms.TextInput(attrs={"class": "form-control"}),
            "diametro": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "fornecedor": forms.TextInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-control"}),
            "localizacao": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "data_compra": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nome": "Nome do Material",
            "tipo": "Tipo",
            "marca": "Marca",
            "numero_serie": "Nº Série",
            "quantidade": "Quantidade",
            "unidade": "Unidade",
            "diametro": "Diâmetro",
            "valor": "Valor (€)",
            "fornecedor": "Fornecedor",
            "localizacao": "Localização",
            "data_compra": "Data de Compra",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        if "empresa" in self.fields:
            self.fields["empresa"].widget = forms.HiddenInput()
            self.fields["empresa"].required = False

        self.fields["furo"].required = False
        self.fields["projeto"].queryset = _obter_queryset_projetos_empresa(self.empresa)

        if self.instance and self.instance.pk and self.instance.projeto_id:
            self.fields["furo"].queryset = _obter_queryset_furos_por_projeto(
                self.instance.projeto_id,
                empresa=self.empresa,
            )
        else:
            self.fields["furo"].queryset = Furo.objects.none()

    def clean_quantidade(self):
        valor = self.cleaned_data.get("quantidade")
        if valor is not None and valor < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")
        return valor

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_diametro(self):
        valor = self.cleaned_data.get("diametro")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O diâmetro não pode ser negativo.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        furo = cleaned.get("furo")

        if self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            _validar_empresa_objeto(self, "projeto", projeto, empresa_id)
            _validar_empresa_objeto(self, "furo", furo, empresa_id)

        _validar_relacao_furo_projeto(self, projeto, furo)
        return cleaned


class BaseMovimentoMaterialForm(forms.ModelForm):
    class Meta:
        fields = ["material", "projeto", "furo", "quantidade", "data", "observacoes"]
        widgets = {
            "material": forms.Select(attrs={"class": "form-control"}),
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "quantidade": forms.NumberInput(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado
        self.empresa = getattr(empregado, "empresa", None) if empregado else None

        self.fields["furo"].required = False
        self.fields["projeto"].required = False
        self.fields["projeto"].queryset = _obter_queryset_projetos_empregado(
            self.empregado,
            empresa=self.empresa,
        )
        self.fields["furo"].queryset = _obter_queryset_furos_empregado(
            self.empregado,
            empresa=self.empresa,
        )

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get("quantidade")
        if quantidade is None or quantidade <= 0:
            raise forms.ValidationError("A quantidade deve ser maior que zero.")
        return quantidade

    def _get_material_queryset(self):
        return Material.objects.none()

    def _validar_quantidade_material(self, quantidade, material):
        return quantidade

    def _executar_validacoes_comuns(self, cleaned):
        projeto = cleaned.get("projeto")
        furo = cleaned.get("furo")
        material = cleaned.get("material")

        if material and getattr(material, "projeto_id", None):
            projeto = material.projeto
            cleaned["projeto"] = projeto

        if self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            _validar_empresa_objeto(self, "material", material, empresa_id)
            _validar_empresa_objeto(self, "projeto", projeto, empresa_id)
            _validar_empresa_objeto(self, "furo", furo, empresa_id)

        _validar_relacao_furo_projeto(self, projeto, furo)

    def clean(self):
        cleaned = super().clean()
        self._executar_validacoes_comuns(cleaned)
        return cleaned


class LevantamentoMaterialForm(BaseMovimentoMaterialForm):
    class Meta(BaseMovimentoMaterialForm.Meta):
        model = LevantamentoMaterial

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, empregado=empregado, **kwargs)
        self.fields["material"].queryset = self._get_material_queryset()

    def _get_material_queryset(self):
        materiais_qs = Material.objects.filter(ativo=True, quantidade__gt=0)
        if self.empresa is not None:
            materiais_qs = materiais_qs.filter(empresa_id=_resolver_empresa_id(self.empresa))
        else:
            materiais_qs = materiais_qs.none()
        return materiais_qs.order_by("nome")

    def clean_quantidade(self):
        quantidade = super().clean_quantidade()
        material = self.cleaned_data.get("material")
        return self._validar_quantidade_material(quantidade, material)

    def _validar_quantidade_material(self, quantidade, material):
        if material and quantidade > material.quantidade:
            raise forms.ValidationError("Quantidade superior ao stock disponível.")
        return quantidade


class DevolucaoMaterialForm(BaseMovimentoMaterialForm):
    class Meta(BaseMovimentoMaterialForm.Meta):
        model = DevolucaoMaterial

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, empregado=empregado, **kwargs)
        self.fields["material"].queryset = self._get_material_queryset()

    def _get_material_queryset(self):
        materiais_qs = Material.objects.filter(ativo=True)
        if self.empresa is not None:
            materiais_qs = materiais_qs.filter(empresa_id=_resolver_empresa_id(self.empresa))
        else:
            materiais_qs = materiais_qs.none()
        return materiais_qs.order_by("nome")