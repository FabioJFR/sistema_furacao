from django import forms

from projetos.models import Empregados, Equipa


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


class EquipaForm(forms.ModelForm):
    class Meta:
        model = Equipa
        fields = ["nome", "membros", "ativo"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Equipa Turno A",
                }
            ),
            "membros": forms.SelectMultiple(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nome": "Nome da equipa",
            "membros": "Pertencentes à equipa",
            "ativo": "Equipa ativa",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None

        if empresa_id is not None:
            self.instance.empresa_id = empresa_id
            self.fields["membros"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        else:
            self.fields["membros"].queryset = Empregados.objects.none()

        self.fields["nome"].help_text = "Usa um nome simples para identificar a equipa no terreno."
        self.fields["membros"].required = False
        self.fields["membros"].help_text = "Seleciona empregados desta empresa. Podes editar a equipa a qualquer altura."
        self.fields["ativo"].initial = True if self.instance._state.adding else self.fields["ativo"].initial

    def clean_nome(self):
        nome = (self.cleaned_data.get("nome") or "").strip()
        if not nome:
            raise forms.ValidationError("O nome da equipa é obrigatório.")

        if self.empresa is not None:
            existe = Equipa.objects.filter(
                empresa_id=_resolver_empresa_id(self.empresa),
                nome__iexact=nome,
            )
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                raise forms.ValidationError("Já existe uma equipa com este nome nesta empresa.")

        return nome

    def clean_membros(self):
        membros = self.cleaned_data.get("membros")
        if self.empresa is None or not membros:
            return membros

        empresa_id = _resolver_empresa_id(self.empresa)
        for empregado in membros:
            if empregado.empresa_id != empresa_id:
                raise forms.ValidationError("Só podes selecionar empregados da empresa atual.")
        return membros

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.empresa is not None:
            instance.empresa_id = _resolver_empresa_id(self.empresa)
        if commit:
            instance.save()
            self.save_m2m()
        return instance
