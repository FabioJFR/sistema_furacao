from datetime import datetime, timedelta

from django import forms

from projetos.models import Empregados, Projeto, Furo, RegistoDiarioEmpregado

from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)

        return result

def _juntar_data_hora(hora):
    return datetime.combine(datetime.today(), hora)


def _hora_apos(base_hora, hora_para_validar):
    """
    Converte uma hora em datetime e, se necessário,
    assume que passou para o dia seguinte.
    """
    base_dt = _juntar_data_hora(base_hora)
    hora_dt = _juntar_data_hora(hora_para_validar)

    if hora_dt < base_dt:
        hora_dt += timedelta(days=1)

    return hora_dt


class RegistoDiarioForm(forms.Form):
    empregado = forms.ModelChoiceField(
        queryset=Empregados.objects.all().order_by("nome"),
        label="Empregado"
    )
    projeto = forms.ModelChoiceField(
        queryset=Projeto.objects.all().order_by("nome"),
        label="Projeto"
    )
    furo = forms.ModelChoiceField(
        queryset=Furo.objects.all().order_by("nome"),
        label="Furo"
    )
    data = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Data"
    )

    hora_inicio = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de início"
    )
    hora_inicio_pausa = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de início da pausa"
    )
    hora_fim_pausa = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de fim da pausa"
    )
    hora_fim = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de fim"
    )

    horas_paragem = forms.FloatField(
        required=False,
        min_value=0,
        initial=0,
        label="Horas de paragem"
    )
    tipo_paragem = forms.ChoiceField(
        required=False,
        choices=RegistoDiarioEmpregado.TIPO_PARAGEM_CHOICES,
        label="Tipo de paragem"
    )

    metros_furados = forms.FloatField(
        min_value=0,
        initial=0,
        label="Metros furados"
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Observações"
    )
    relatorio_foto = forms.ImageField(
        required=False,
        label="Foto do relatório"
    )

    def clean(self):
        cleaned_data = super().clean()

        projeto = cleaned_data.get("projeto")
        furo = cleaned_data.get("furo")

        hora_inicio = cleaned_data.get("hora_inicio")
        hora_inicio_pausa = cleaned_data.get("hora_inicio_pausa")
        hora_fim_pausa = cleaned_data.get("hora_fim_pausa")
        hora_fim = cleaned_data.get("hora_fim")

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")

        horarios_preenchidos = [
            hora_inicio,
            hora_inicio_pausa,
            hora_fim_pausa,
            hora_fim,
        ]
        total_horarios = sum(1 for h in horarios_preenchidos if h is not None)

        if 0 < total_horarios < 4:
            raise forms.ValidationError(
                "Preencha todos os horários do turno ou deixe todos em branco."
            )

        if total_horarios == 4:
            inicio_dt = _juntar_data_hora(hora_inicio)
            inicio_pausa_dt = _hora_apos(hora_inicio, hora_inicio_pausa)
            fim_pausa_dt = _hora_apos(hora_inicio_pausa, hora_fim_pausa)
            fim_dt = _hora_apos(hora_fim_pausa, hora_fim)

            if inicio_pausa_dt < inicio_dt:
                self.add_error(
                    "hora_inicio_pausa",
                    "A pausa deve começar depois da hora de início."
                )

            if fim_pausa_dt < inicio_pausa_dt:
                self.add_error(
                    "hora_fim_pausa",
                    "A pausa deve terminar depois de começar."
                )

            if fim_dt < fim_pausa_dt:
                self.add_error(
                    "hora_fim",
                    "A hora de fim deve ser posterior ao fim da pausa."
                )

        return cleaned_data


class RegistoDiarioEmpregadoForm(forms.ModelForm):
    fotos_amostra = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "accept": "image/*",
            "multiple": True,
        }),
        label="Fotos da amostra"
    )
    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            "projeto",
            "furo",
            "data",
            "hora_inicio",
            "hora_inicio_pausa",
            "hora_fim_pausa",
            "hora_fim",
            "horas_paragem",
            "tipo_paragem",
            "metros_furados",
            "relatorio_foto",
            "observacoes",
        ]
        widgets = {
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_inicio_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "horas_paragem": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "Horas de paragem"
            }),
            "tipo_paragem": forms.Select(attrs={"class": "form-control"}),
            "metros_furados": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "relatorio_foto": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, empregado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado

        if empregado:
            projetos_atuais = empregado.projetos_atuais
            self.fields["projeto"].queryset = projetos_atuais
            self.fields["furo"].queryset = Furo.objects.filter(
                projeto__in=projetos_atuais
            ).distinct()

    def clean_metros_furados(self):
        valor = self.cleaned_data.get("metros_furados")
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os metros furados não podem ser negativos.")
        return valor

    def clean_horas_paragem(self):
        valor = self.cleaned_data.get("horas_paragem")
        if valor is not None and valor < 0:
            raise forms.ValidationError("As horas de paragem não podem ser negativas.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        furo = cleaned.get("furo")
        hora_inicio = cleaned.get("hora_inicio")
        hora_inicio_pausa = cleaned.get("hora_inicio_pausa")
        hora_fim_pausa = cleaned.get("hora_fim_pausa")
        hora_fim = cleaned.get("hora_fim")
        horas_paragem = cleaned.get("horas_paragem")
        tipo_paragem = cleaned.get("tipo_paragem")

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")

        horarios = [hora_inicio, hora_inicio_pausa, hora_fim_pausa, hora_fim]
        total_horarios = sum(1 for h in horarios if h is not None)

        if 0 < total_horarios < 4:
            raise forms.ValidationError(
                "Preencha todos os horários do turno ou deixe todos em branco."
            )

        if total_horarios == 4:
            inicio_dt = _juntar_data_hora(hora_inicio)
            inicio_pausa_dt = _hora_apos(hora_inicio, hora_inicio_pausa)
            fim_pausa_dt = _hora_apos(hora_inicio_pausa, hora_fim_pausa)
            fim_dt = _hora_apos(hora_fim_pausa, hora_fim)

            if inicio_pausa_dt < inicio_dt:
                self.add_error(
                    "hora_inicio_pausa",
                    "A pausa deve começar depois da hora de início."
                )

            if fim_pausa_dt < inicio_pausa_dt:
                self.add_error(
                    "hora_fim_pausa",
                    "A pausa deve terminar depois de começar."
                )

            if fim_dt < fim_pausa_dt:
                self.add_error(
                    "hora_fim",
                    "A hora de fim deve ser posterior ao fim da pausa."
                )

        if horas_paragem is not None and horas_paragem > 0 and not tipo_paragem:
            self.add_error("tipo_paragem", "Selecione se a paragem é Cliente ou Empresa.")

        return cleaned


class RegistoDiarioEmpregadoAdminForm(forms.ModelForm):
    fotos_amostra = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "accept": "image/*",
            "multiple": True,
        }),
        label="Fotos da amostra"
    )

    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            "empregado",
            "projeto",
            "furo",
            "data",
            "hora_inicio",
            "hora_inicio_pausa",
            "hora_fim_pausa",
            "hora_fim",
            "horas_paragem",
            "tipo_paragem",
            "metros_furados",
            "relatorio_foto",
            "observacoes",
        ]
        widgets = {
            "empregado": forms.Select(attrs={"class": "form-control"}),
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_inicio_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "horas_paragem": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tipo_paragem": forms.Select(attrs={"class": "form-control"}),
            "metros_furados": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "relatorio_foto": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean_metros_furados(self):
        valor = self.cleaned_data.get("metros_furados")
        if valor is not None and valor < 0:
            raise forms.ValidationError("Os metros furados não podem ser negativos.")
        return valor

    def clean_horas_paragem(self):
        valor = self.cleaned_data.get("horas_paragem")
        if valor is not None and valor < 0:
            raise forms.ValidationError("As horas de paragem não podem ser negativas.")
        return valor

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        furo = cleaned.get("furo")
        hora_inicio = cleaned.get("hora_inicio")
        hora_inicio_pausa = cleaned.get("hora_inicio_pausa")
        hora_fim_pausa = cleaned.get("hora_fim_pausa")
        hora_fim = cleaned.get("hora_fim")
        horas_paragem = cleaned.get("horas_paragem")
        tipo_paragem = cleaned.get("tipo_paragem")

        if furo and projeto and furo.projeto_id != projeto.id:
            self.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")

        horarios = [hora_inicio, hora_inicio_pausa, hora_fim_pausa, hora_fim]
        total_horarios = sum(1 for h in horarios if h is not None)

        if 0 < total_horarios < 4:
            raise forms.ValidationError(
                "Preencha todos os horários do turno ou deixe todos em branco."
            )

        if total_horarios == 4:
            inicio_dt = _juntar_data_hora(hora_inicio)
            inicio_pausa_dt = _hora_apos(hora_inicio, hora_inicio_pausa)
            fim_pausa_dt = _hora_apos(hora_inicio_pausa, hora_fim_pausa)
            fim_dt = _hora_apos(hora_fim_pausa, hora_fim)

            if inicio_pausa_dt < inicio_dt:
                self.add_error(
                    "hora_inicio_pausa",
                    "A pausa deve começar depois da hora de início."
                )

            if fim_pausa_dt < inicio_pausa_dt:
                self.add_error(
                    "hora_fim_pausa",
                    "A pausa deve terminar depois de começar."
                )

            if fim_dt < fim_pausa_dt:
                self.add_error(
                    "hora_fim",
                    "A hora de fim deve ser posterior ao fim da pausa."
                )

        if horas_paragem is not None and horas_paragem > 0 and not tipo_paragem:
            self.add_error("tipo_paragem", "Selecione se a paragem é Cliente ou Empresa.")

        return cleaned