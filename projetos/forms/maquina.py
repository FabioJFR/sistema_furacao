from django import forms

from ..models.maquina import Maquina



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _atribuir_empresa_maquina(instance, empresa=None):
    if empresa is not None:
        instance.empresa_id = _resolver_empresa_id(empresa)
    return instance



def _validar_empresa_objeto(form, campo, objeto, empresa_id, mensagem):
    if objeto and objeto.empresa_id != empresa_id:
        form.add_error(campo, mensagem)



def _validar_lista_objetos_empresa(form, campo, objetos, empresa_id, mensagem):
    if not objetos:
        return

    for objeto in objetos:
        if objeto.empresa_id != empresa_id:
            form.add_error(campo, mensagem)
            break



class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = [
            "projetos",
            "projeto_atual",
            "furos",
            "nome",
            "tipo",
            "marca",
            "modelo",
            "numero_serie",
            "data_compra",
            "data_registo",
            "data_revisao",
            "matricula",
            "seguro",
            "data_seguro",
            "data_iuc",
            "km",
            "horimetro",
            "ano_registo",
            "valor",
            "localizacao_atual",
            "observacoes",
            "estado",
            "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "numero_serie": forms.TextInput(attrs={"class": "form-control"}),
            "projetos": forms.SelectMultiple(attrs={"class": "form-control"}),
            "projeto_atual": forms.Select(attrs={"class": "form-control"}),
            "furos": forms.SelectMultiple(attrs={"class": "form-control"}),
            "data_compra": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "data_registo": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "data_revisao": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "matricula": forms.TextInput(attrs={"class": "form-control"}),
            "seguro": forms.TextInput(attrs={"class": "form-control"}),
            "data_seguro": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "data_iuc": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "km": forms.NumberInput(attrs={"class": "form-control"}),
            "horimetro": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "ano_registo": forms.NumberInput(attrs={"class": "form-control"}),
            "valor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "localizacao_atual": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estado": forms.Select(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nome": "Nome da Máquina",
            "tipo": "Tipo",
            "marca": "Marca",
            "modelo": "Modelo",
            "numero_serie": "Nº Série",
            "km": "Quilómetros",
            "horimetro": "Horímetro",
            "valor": "Valor (€)",
            "localizacao_atual": "Localização Atual",
            "projeto_atual": "Projeto Atual",
            "data_compra": "Data de Compra",
            "data_registo": "Data de Registo",
            "data_revisao": "Data de Revisão",
            "data_seguro": "Validade do Seguro",
            "data_iuc": "Validade do IUC",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        _atribuir_empresa_maquina(self.instance, empresa=self.empresa)

        empresa_id = _resolver_empresa_id(self.empresa) if self.empresa is not None else None

        if empresa_id is not None:
            self.fields["projetos"].queryset = self.fields["projetos"].queryset.filter(
                empresa_id=empresa_id
            ).order_by("nome")
            self.fields["furos"].queryset = self.fields["furos"].queryset.filter(
                empresa_id=empresa_id
            ).order_by("nome")
            self.fields["projeto_atual"].queryset = self.fields["projeto_atual"].queryset.filter(
                empresa_id=empresa_id
            ).order_by("nome")
        else:
            self.fields["projetos"].queryset = self.fields["projetos"].queryset.none()
            self.fields["furos"].queryset = self.fields["furos"].queryset.none()
            self.fields["projeto_atual"].queryset = self.fields["projeto_atual"].queryset.none()

        if self.instance and self.instance.pk and empresa_id is not None:
            self.fields["projeto_atual"].queryset = self.instance.projetos.filter(
                empresa_id=empresa_id
            ).order_by("nome")

    def clean_km(self):
        valor = self.cleaned_data.get("km")
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os quilómetros não podem ser negativos.")
        return valor

    def clean_horimetro(self):
        valor = self.cleaned_data.get("horimetro")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O horímetro não pode ser negativo.")
        return valor

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor is not None and valor < 0:
            raise forms.ValidationError("O valor não pode ser negativo.")
        return valor

    def clean_ano_registo(self):
        valor = self.cleaned_data.get("ano_registo")
        if valor is not None and valor < 1900:
            raise forms.ValidationError("Ano inválido.")
        return valor

    def clean(self):
        cleaned = super().clean()
        _atribuir_empresa_maquina(self.instance, empresa=self.empresa)

        projeto_atual = cleaned.get("projeto_atual")
        projetos = cleaned.get("projetos")
        furos = cleaned.get("furos")

        if self.empresa is not None:
            empresa_id = _resolver_empresa_id(self.empresa)
            _validar_empresa_objeto(
                self,
                "projeto_atual",
                projeto_atual,
                empresa_id,
                "O projeto atual não pertence à empresa atual.",
            )
            _validar_lista_objetos_empresa(
                self,
                "projetos",
                projetos,
                empresa_id,
                "Um dos projetos selecionados não pertence à empresa atual.",
            )
            _validar_lista_objetos_empresa(
                self,
                "furos",
                furos,
                empresa_id,
                "Um dos furos selecionados não pertence à empresa atual.",
            )

        if projeto_atual and projetos and projeto_atual not in projetos:
            self.add_error(
                "projeto_atual",
                "O projeto atual deve estar na lista de projetos da máquina.",
            )

        if furos and projetos:
            projetos_ids = {projeto.id for projeto in projetos}
            for furo in furos:
                if furo.projeto_id and furo.projeto_id not in projetos_ids:
                    self.add_error(
                        "furos",
                        "Todos os furos selecionados devem pertencer aos projetos associados à máquina.",
                    )
                    break

        data_compra = cleaned.get("data_compra")
        data_revisao = cleaned.get("data_revisao")

        if data_compra and data_revisao and data_revisao < data_compra:
            self.add_error("data_revisao", "A revisão não pode ser anterior à compra.")

        return cleaned
