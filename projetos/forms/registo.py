from datetime import datetime, timedelta
import json
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.utils import timezone

from projetos.models import RegistoDiarioEmpregado
from projetos.selectors.forms import (
    listar_empregados_empresa_qs,
    listar_planeamentos_empresa_qs,
    listar_planeamentos_empregado_qs,
    listar_furos_empresa_qs,
    listar_furos_empregado_qs,
    listar_projetos_empresa_qs,
    listar_projetos_empregado_qs,
    resolver_empresa_id,
)


# Helper to resolve empresa id from either an object or pk directly

def _resolver_empresa_id(empresa):
    return resolver_empresa_id(empresa)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)



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



def _validar_empresa_objeto(form, campo, objeto, empresa_id):
    if objeto and objeto.empresa_id != empresa_id:
        form.add_error(campo, f"O {campo} selecionado não pertence à empresa atual.")



def _validar_relacao_furo_projeto(form, projeto, furo):
    if furo and projeto and furo.projeto_id != projeto.id:
        form.add_error("furo", "O furo selecionado não pertence ao projeto escolhido.")



def _validar_horarios_turno(form, cleaned_data):
    hora_inicio = cleaned_data.get("hora_inicio")
    hora_inicio_pausa = cleaned_data.get("hora_inicio_pausa")
    hora_fim_pausa = cleaned_data.get("hora_fim_pausa")
    hora_fim = cleaned_data.get("hora_fim")

    tem_inicio = hora_inicio is not None
    tem_fim = hora_fim is not None
    tem_pausa_inicio = hora_inicio_pausa is not None
    tem_pausa_fim = hora_fim_pausa is not None

    if tem_inicio != tem_fim:
        raise forms.ValidationError(
            "Preencha 'Hora de início' e 'Hora de fim' ou deixe ambos em branco."
        )

    if tem_pausa_inicio != tem_pausa_fim:
        raise forms.ValidationError(
            "Preencha 'Hora de início da pausa' e 'Hora de fim da pausa' ou deixe ambas em branco."
        )

    if (tem_pausa_inicio or tem_pausa_fim) and not (tem_inicio and tem_fim):
        raise forms.ValidationError(
            "Para registar uma pausa, preencha também a hora de início e a hora de fim do turno."
        )

    if tem_inicio and tem_fim:
        fim_dt = _hora_apos(hora_inicio, hora_fim)
        inicio_dt = _juntar_data_hora(hora_inicio)
        if fim_dt < inicio_dt:
            form.add_error(
                "hora_fim",
                "A hora de fim deve ser posterior à hora de início.",
            )

    if tem_inicio and tem_fim and tem_pausa_inicio and tem_pausa_fim:
        inicio_dt = _juntar_data_hora(hora_inicio)
        inicio_pausa_dt = _hora_apos(hora_inicio, hora_inicio_pausa)
        fim_pausa_dt = _hora_apos(hora_inicio_pausa, hora_fim_pausa)
        fim_dt = _hora_apos(hora_fim_pausa, hora_fim)

        if inicio_pausa_dt < inicio_dt:
            form.add_error(
                "hora_inicio_pausa",
                "A pausa deve começar depois da hora de início.",
            )

        if fim_pausa_dt < inicio_pausa_dt:
            form.add_error(
                "hora_fim_pausa",
                "A pausa deve terminar depois de começar.",
            )

        if fim_dt < fim_pausa_dt:
            form.add_error(
                "hora_fim",
                "A hora de fim deve ser posterior ao fim da pausa.",
            )



def _validar_tipo_paragem(form, cleaned_data):
    horas_paragem = cleaned_data.get("horas_paragem")
    tipo_paragem = cleaned_data.get("tipo_paragem")

    if horas_paragem is not None and horas_paragem > 0 and not tipo_paragem:
        form.add_error("tipo_paragem", "Selecione se a paragem é Cliente ou Empresa.")



class RegistoDiarioValidacoesMixin:
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

    def _validar_empresa_clean(self, cleaned_data):
        projeto = cleaned_data.get("projeto")
        furo = cleaned_data.get("furo")

        if self.empresa is None:
            return

        empresa_id = _resolver_empresa_id(self.empresa)

        if hasattr(self, "empregado") and self.empregado:
            if self.empregado.empresa_id != empresa_id:
                raise forms.ValidationError("O empregado não pertence à empresa atual.")
        else:
            empregado = cleaned_data.get("empregado")
            _validar_empresa_objeto(self, "empregado", empregado, empresa_id)

        _validar_empresa_objeto(self, "projeto", projeto, empresa_id)
        _validar_empresa_objeto(self, "furo", furo, empresa_id)

    def _executar_validacoes_comuns(self, cleaned_data):
        projeto = cleaned_data.get("projeto")
        furo = cleaned_data.get("furo")

        self._validar_empresa_clean(cleaned_data)
        _validar_relacao_furo_projeto(self, projeto, furo)
        _validar_tipo_paragem(self, cleaned_data)


class RegistoDiarioForm(RegistoDiarioValidacoesMixin, forms.Form):
    empregado = forms.ModelChoiceField(
        queryset=listar_empregados_empresa_qs(None),
        label="Empregado",
    )
    projeto = forms.ModelChoiceField(
        queryset=listar_projetos_empresa_qs(None),
        label="Projeto",
    )
    furo = forms.ModelChoiceField(
        queryset=listar_furos_empresa_qs(None),
        label="Furo",
    )
    data = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Data",
    )

    hora_inicio = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de início",
    )
    hora_inicio_pausa = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de início da pausa",
    )
    hora_fim_pausa = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de fim da pausa",
    )
    hora_fim = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
        label="Hora de fim",
    )

    horas_paragem = forms.FloatField(
        required=False,
        min_value=0,
        initial=0,
        label="Horas de paragem",
    )
    tipo_paragem = forms.ChoiceField(
        required=False,
        choices=RegistoDiarioEmpregado.TIPO_PARAGEM_CHOICES,
        label="Tipo de paragem",
    )

    metros_furados = forms.FloatField(
        min_value=0,
        initial=0,
        label="Metros furados",
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Observações",
    )
    relatorio_foto = forms.ImageField(
        required=False,
        label="Foto do relatório",
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if not self.is_bound:
            self.fields["data"].initial = self.fields["data"].initial or timezone.localdate()

        if empresa is not None:
            empresa_id = _resolver_empresa_id(empresa)
            self.fields["empregado"].queryset = listar_empregados_empresa_qs(empresa_id)
            self.fields["projeto"].queryset = listar_projetos_empresa_qs(empresa_id)
            self.fields["furo"].queryset = listar_furos_empresa_qs(empresa_id)
        self.fields["data"].help_text = "Por defeito fica hoje; altera apenas se estiveres a lançar um turno anterior."
        self.fields["horas_paragem"].help_text = "Deixa 0 se não houve paragem."
        self.fields["metros_furados"].help_text = "Pode ficar 0 se o turno foi preparação, manutenção ou ocorrência."

    def clean(self):
        cleaned_data = super().clean()
        self._executar_validacoes_comuns(cleaned_data)
        return cleaned_data


class BaseRegistoDiarioModelForm(RegistoDiarioValidacoesMixin, forms.ModelForm):
    fotos_amostra = MultipleFileField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            }
        ),
        label="Fotos da amostra",
    )

    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            "planeamento_turno",
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
            "planeamento_turno": forms.Select(attrs={"class": "form-control"}),
            "projeto": forms.Select(attrs={"class": "form-control"}),
            "furo": forms.Select(attrs={"class": "form-control"}),
            "data": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_inicio_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim_pausa": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "horas_paragem": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Horas de paragem",
                }
            ),
            "tipo_paragem": forms.Select(attrs={"class": "form-control"}),
            "metros_furados": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "relatorio_foto": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance._state.adding:
            self.fields["data"].initial = self.fields["data"].initial or timezone.localdate()
            self.fields["horas_paragem"].initial = 0
            self.fields["metros_furados"].initial = 0

        self.fields["planeamento_turno"].help_text = "Opcional: se existir planeamento, projeto/furo/horário são preenchidos a partir dele."
        self.fields["projeto"].help_text = "Escolhe o projeto do turno; pode ser herdado do planeamento."
        self.fields["furo"].help_text = "Escolhe o furo trabalhado; furos concluídos ficam ocultos em novos registos."
        self.fields["data"].help_text = "Por defeito fica hoje; altera apenas se estiveres a lançar um turno anterior."
        self.fields["horas_paragem"].help_text = "Deixa 0 se não houve paragem."
        self.fields["metros_furados"].help_text = "Pode ficar 0 se o turno foi preparação, manutenção ou ocorrência."
        self.fields["observacoes"].help_text = "Regista aqui contexto que ajude a explicar o turno no relatório técnico."

    def clean(self):
        cleaned = super().clean()
        planeamento = cleaned.get("planeamento_turno")
        if planeamento:
            cleaned["projeto"] = planeamento.projeto
            if planeamento.furo_id:
                cleaned["furo"] = planeamento.furo
            if not cleaned.get("data"):
                cleaned["data"] = planeamento.data_inicio
            if not cleaned.get("hora_inicio"):
                cleaned["hora_inicio"] = planeamento.hora_inicio
            if not cleaned.get("hora_fim"):
                cleaned["hora_fim"] = planeamento.hora_fim

            self.instance.projeto = cleaned.get("projeto")
            self.instance.furo = cleaned.get("furo")
            self.instance.data = cleaned.get("data")
            self.instance.hora_inicio = cleaned.get("hora_inicio")
            self.instance.hora_fim = cleaned.get("hora_fim")

        self._executar_validacoes_comuns(cleaned)
        return cleaned


class RegistoDiarioEmpregadoForm(BaseRegistoDiarioModelForm):
    def __init__(self, *args, empregado=None, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empregado = empregado
        self.empresa = empresa or getattr(empregado, "empresa", None)
        self.planeamentos_disponiveis = []
        self.planeamentos_mapa = []
        self.planeamento_turno_selecionado_id = ""
        self.data_planeamento_referencia = None

        empresa_id = _resolver_empresa_id(self.empresa) if self.empresa is not None else None

        if self.empresa is not None:
            self.fields["planeamento_turno"].queryset = listar_planeamentos_empresa_qs(empresa_id)
            self.fields["projeto"].queryset = listar_projetos_empresa_qs(empresa_id)
            self.fields["furo"].queryset = listar_furos_empresa_qs(empresa_id)

        if empregado:
            data_referencia = (
                self.data.get("data")
                or self.initial.get("data")
                or getattr(self.instance, "data", None)
                or timezone.localdate()
            )
            self.data_planeamento_referencia = data_referencia
            projetos_atuais = listar_projetos_empregado_qs(empregado, empresa=empresa_id if self.empresa is not None else None)
            self.fields["projeto"].queryset = projetos_atuais
            self.fields["furo"].queryset = listar_furos_empregado_qs(
                empregado,
                empresa=empresa_id if self.empresa is not None else None,
            )
            self.fields["planeamento_turno"].queryset = listar_planeamentos_empregado_qs(
                empregado,
                empresa=empresa_id if self.empresa is not None else None,
                data=data_referencia,
            )
            self.fields["planeamento_turno"].label_from_instance = (
                lambda item: (
                    f"{'[Atribuído] ' if item.empregado_id == empregado.id else '[Disponível] '}"
                    f"{item.nome_efetivo} · {item.data_inicio.strftime('%d/%m/%Y')}"
                )
            )
            self.planeamentos_disponiveis = list(self.fields["planeamento_turno"].queryset[:12])
            self.planeamentos_mapa = [
                {
                    "id": str(item.id),
                    "data": item.data_inicio.isoformat() if item.data_inicio else "",
                    "hora_inicio": item.hora_inicio.strftime("%H:%M") if item.hora_inicio else "",
                    "hora_fim": item.hora_fim.strftime("%H:%M") if item.hora_fim else "",
                    "projeto_id": str(item.projeto_id) if item.projeto_id else "",
                    "furo_id": str(item.furo_id) if item.furo_id else "",
                }
                for item in self.fields["planeamento_turno"].queryset
            ]

        if not self.instance.pk:
            self.fields["furo"].queryset = self.fields["furo"].queryset.exclude(estado="concluido")
        self.fields["planeamento_turno"].required = False
        self.fields["planeamento_turno"].help_text = "Selecione o turno planeado que cumpriu. São mostrados os turnos atribuídos a si e também os turnos ainda sem empregado definido. Projeto, furo e horário base são herdados automaticamente."
        self.planeamento_turno_selecionado_id = str(
            self["planeamento_turno"].value() or getattr(self.instance, "planeamento_turno_id", "") or ""
        )


class RegistoDiarioEmpregadoAdminForm(BaseRegistoDiarioModelForm):
    class Meta(BaseRegistoDiarioModelForm.Meta):
        fields = [
            "empregado",
            "planeamento_turno",
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
            **BaseRegistoDiarioModelForm.Meta.widgets,
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.empregado = None

        if empresa is not None:
            empresa_id = _resolver_empresa_id(empresa)
            self.fields["empregado"].queryset = listar_empregados_empresa_qs(empresa_id)
            self.fields["planeamento_turno"].queryset = listar_planeamentos_empresa_qs(empresa_id)
            self.fields["projeto"].queryset = listar_projetos_empresa_qs(empresa_id)
            self.fields["furo"].queryset = listar_furos_empresa_qs(empresa_id)
            self.fields["planeamento_turno"].label_from_instance = (
                lambda item: f"{item.nome_efetivo} · {item.empregado.nome if item.empregado_id else '-'} · {item.data_inicio.strftime('%d/%m/%Y')}"
            )

        if not self.instance.pk:
            self.fields["furo"].queryset = self.fields["furo"].queryset.exclude(estado="concluido")


class RelatorioTurnoForm(forms.ModelForm):
    class Meta:
        model = RegistoDiarioEmpregado
        fields = [
            "cliente",
            "sonda",
            "torre",
            "bomba_injecao",
            "bomba_captacao",
            "estaleiro",
            "numero_sondagem",
            "inclinacao",
            "diametro_furo",
            "numero_relatorio",
            "no_inicio",
            "no_final",
            "avanco_turno",
            "testemunho_recuperado",
            "percentagem_recuperacao",
            "furacoes",
            "operacoes_ocorrencias",
            "polimeros",
            "bit_novo",
            "polimeros_de",
            "polimeros_ate",
            "notas",
            "equipa_turno",
            "turno",
        ]
        widgets = {
            "cliente": forms.TextInput(attrs={"class": "form-control"}),
            "sonda": forms.TextInput(attrs={"class": "form-control"}),
            "torre": forms.TextInput(attrs={"class": "form-control"}),
            "bomba_injecao": forms.TextInput(attrs={"class": "form-control"}),
            "bomba_captacao": forms.TextInput(attrs={"class": "form-control"}),
            "estaleiro": forms.TextInput(attrs={"class": "form-control"}),
            "numero_sondagem": forms.TextInput(attrs={"class": "form-control"}),
            "inclinacao": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "diametro_furo": forms.TextInput(attrs={"class": "form-control"}),
            "numero_relatorio": forms.TextInput(attrs={"class": "form-control"}),
            "no_inicio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "no_final": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "avanco_turno": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "testemunho_recuperado": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "percentagem_recuperacao": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "furacoes": forms.HiddenInput(),
            "operacoes_ocorrencias": forms.HiddenInput(),
            "polimeros": forms.HiddenInput(),
            "bit_novo": forms.TextInput(attrs={"class": "form-control"}),
            "polimeros_de": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "polimeros_ate": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "equipa_turno": forms.HiddenInput(),
            "turno": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "numero_sondagem": "Número sondagem",
            "diametro_furo": "Diâmetro do furo",
            "numero_relatorio": "Número relatório",
            "no_inicio": "No início",
            "no_final": "No final",
            "avanco_turno": "Avanço do turno",
            "testemunho_recuperado": "Testemunho recuperado",
            "percentagem_recuperacao": "Percentagem de recuperação",
            "furacoes": "Furadas do turno",
            "operacoes_ocorrencias": "Operações e ocorrências",
            "bomba_injecao": "Bomba injeção",
            "bomba_captacao": "Bomba captação",
            "polimeros": "Polímeros",
            "bit_novo": "Bit novo",
            "polimeros_de": "De",
            "polimeros_ate": "Até",
            "equipa_turno": "Equipa do turno",
        }

    def __init__(self, *args, registo=None, **kwargs):
        self.registo = registo
        super().__init__(*args, **kwargs)

        self.operacoes_ocorrencias_tipos = [
            {"value": chave, "label": label}
            for chave, label in RegistoDiarioEmpregado.RELATORIO_OCORRENCIA_CHOICES
        ]

        polimeros_iniciais = []
        if self.is_bound:
            valor_bound = self.data.get(self.add_prefix("polimeros"), "")
            if valor_bound:
                try:
                    polimeros_iniciais = json.loads(valor_bound)
                except json.JSONDecodeError:
                    polimeros_iniciais = []
        if not polimeros_iniciais:
            polimeros_iniciais = self.initial.get("polimeros")
        if polimeros_iniciais in (None, ""):
            polimeros_iniciais = getattr(self.instance, "polimeros", []) or []
        self.polimeros_lista_inicial = [
            item.strip()
            for item in polimeros_iniciais
            if isinstance(item, str) and item.strip()
        ]
        self.initial["polimeros"] = self.polimeros_lista_inicial
        self.fields["polimeros"].initial = self.polimeros_lista_inicial
        self.fields["polimeros"].help_text = "Adicione os polímeros um a um com o botão +."

        furacoes_iniciais = []
        if self.is_bound:
            valor_bound = self.data.get(self.add_prefix("furacoes"), "")
            if valor_bound:
                try:
                    furacoes_iniciais = json.loads(valor_bound)
                except json.JSONDecodeError:
                    furacoes_iniciais = []
        if not furacoes_iniciais:
            furacoes_iniciais = self.initial.get("furacoes")
        if furacoes_iniciais in (None, ""):
            furacoes_iniciais = getattr(self.instance, "furacoes", []) or []
        if not furacoes_iniciais:
            valores_legado = [
                self.initial.get("furacao_inicio", getattr(self.instance, "furacao_inicio", None)),
                self.initial.get("furacao_fim", getattr(self.instance, "furacao_fim", None)),
                self.initial.get("furacao_avanco", getattr(self.instance, "furacao_avanco", None)),
                self.initial.get("furacao_recuperacao", getattr(self.instance, "furacao_recuperacao", None)),
                self.initial.get("furacao_rocha", getattr(self.instance, "furacao_rocha", "")),
                self.initial.get("furacao_descricao", getattr(self.instance, "furacao_descricao", "")),
            ]
            if any(valor not in (None, "", []) for valor in valores_legado):
                furacoes_iniciais = [{
                    "inicio": self.initial.get("furacao_inicio", getattr(self.instance, "furacao_inicio", None)),
                    "fim": self.initial.get("furacao_fim", getattr(self.instance, "furacao_fim", None)),
                    "avanco": self.initial.get("furacao_avanco", getattr(self.instance, "furacao_avanco", None)),
                    "recuperacao": self.initial.get("furacao_recuperacao", getattr(self.instance, "furacao_recuperacao", None)),
                    "rocha": self.initial.get("furacao_rocha", getattr(self.instance, "furacao_rocha", "")),
                    "descricao": self.initial.get("furacao_descricao", getattr(self.instance, "furacao_descricao", "")),
                }]
        self.furacoes_lista_inicial = []
        for item in furacoes_iniciais:
            if not isinstance(item, dict):
                continue
            self.furacoes_lista_inicial.append(
                {
                    "inicio": float(item["inicio"]) if item.get("inicio") not in (None, "") else None,
                    "fim": float(item["fim"]) if item.get("fim") not in (None, "") else None,
                    "avanco": float(item["avanco"]) if item.get("avanco") not in (None, "") else None,
                    "recuperacao": float(item["recuperacao"]) if item.get("recuperacao") not in (None, "") else None,
                    "rocha": (item.get("rocha") or "").strip(),
                    "descricao": (item.get("descricao") or "").strip(),
                }
            )
        self.initial["furacoes"] = self.furacoes_lista_inicial
        self.fields["furacoes"].initial = self.furacoes_lista_inicial
        self.fields["furacoes"].help_text = "Adicione cada furada do turno como uma linha da lista."

        operacoes_iniciais = []
        if self.is_bound:
            valor_bound = self.data.get(self.add_prefix("operacoes_ocorrencias"), "")
            if valor_bound:
                try:
                    operacoes_iniciais = json.loads(valor_bound)
                except json.JSONDecodeError:
                    operacoes_iniciais = []
        if not operacoes_iniciais:
            operacoes_iniciais = self.initial.get("operacoes_ocorrencias")
        if operacoes_iniciais in (None, ""):
            operacoes_iniciais = getattr(self.instance, "operacoes_ocorrencias", []) or []
        if not operacoes_iniciais:
            campos_legado = [
                ("manobra", "manobra", "manobra_de", "manobra_ate"),
                ("reaming", "reaming", "reaming_de", "reaming_ate"),
                ("avaria", "avaria", "avaria_de", "avaria_ate"),
                ("horas_paragem", "relatorio_horas_paragem", "horas_paragem_de", "horas_paragem_ate"),
                ("medicao_desvio", "medicao_desvio", "medicao_desvio_de", "medicao_desvio_ate"),
                ("cimentacao", "cimentacao", "cimentacao_de", "cimentacao_ate"),
                ("lavar_furo", "lavar_furo", "lavar_furo_de", "lavar_furo_ate"),
                ("varas_presas", "varas_presas", "varas_presas_de", "varas_presas_ate"),
                ("entubamento", "entubamento", "entubamento_de", "entubamento_ate"),
                ("outros", "outros", "outros_de", "outros_ate"),
            ]
            for tipo, campo_flag, campo_de, campo_ate in campos_legado:
                valor_flag = self.initial.get(campo_flag, getattr(self.instance, campo_flag, None))
                hora_de = self.initial.get(campo_de, getattr(self.instance, campo_de, None))
                hora_ate = self.initial.get(campo_ate, getattr(self.instance, campo_ate, None))
                ativo = valor_flag == "sim" if campo_flag != "outros" else valor_flag not in (None, "")
                if not ativo and not hora_de and not hora_ate:
                    continue
                operacoes_iniciais.append(
                    {
                        "tipo": tipo,
                        "de": hora_de.strftime("%H:%M") if hasattr(hora_de, "strftime") else (hora_de or ""),
                        "ate": hora_ate.strftime("%H:%M") if hasattr(hora_ate, "strftime") else (hora_ate or ""),
                    }
                )
            valor_bit_novo = self.initial.get("bit_novo", getattr(self.instance, "bit_novo", None))
            hora_bit_novo_de = self.initial.get("bit_novo_de", getattr(self.instance, "bit_novo_de", None))
            hora_bit_novo_ate = self.initial.get("bit_novo_ate", getattr(self.instance, "bit_novo_ate", None))
            bit_novo_ativo = valor_bit_novo not in (None, "", "nao")
            if bit_novo_ativo or hora_bit_novo_de or hora_bit_novo_ate:
                operacoes_iniciais.append(
                    {
                        "tipo": "bit_novo",
                        "de": hora_bit_novo_de.strftime("%H:%M") if hasattr(hora_bit_novo_de, "strftime") else (hora_bit_novo_de or ""),
                        "ate": hora_bit_novo_ate.strftime("%H:%M") if hasattr(hora_bit_novo_ate, "strftime") else (hora_bit_novo_ate or ""),
                    }
                )
        self.operacoes_ocorrencias_lista_inicial = []
        tipos_validos = {item["value"] for item in self.operacoes_ocorrencias_tipos}
        for item in operacoes_iniciais:
            if not isinstance(item, dict):
                continue
            tipo = (item.get("tipo") or "").strip()
            if tipo not in tipos_validos:
                continue
            hora_de = item.get("de") or ""
            hora_ate = item.get("ate") or ""
            self.operacoes_ocorrencias_lista_inicial.append(
                {
                    "tipo": tipo,
                    "de": hora_de.strftime("%H:%M") if hasattr(hora_de, "strftime") else str(hora_de),
                    "ate": hora_ate.strftime("%H:%M") if hasattr(hora_ate, "strftime") else str(hora_ate),
                }
            )
        self.initial["operacoes_ocorrencias"] = self.operacoes_ocorrencias_lista_inicial
        self.fields["operacoes_ocorrencias"].initial = self.operacoes_ocorrencias_lista_inicial
        self.fields["operacoes_ocorrencias"].help_text = "Adicione cada ocorrência numa linha com tipo, hora de início e hora de fim."

        equipa_inicial = []
        if self.is_bound:
            valor_bound = self.data.get(self.add_prefix("equipa_turno"), "")
            if valor_bound:
                try:
                    equipa_inicial = json.loads(valor_bound)
                except json.JSONDecodeError:
                    equipa_inicial = []
        if not equipa_inicial:
            equipa_inicial = self.initial.get("equipa_turno")
        if equipa_inicial in (None, ""):
            equipa_inicial = getattr(self.instance, "equipa_turno", []) or []
        if not equipa_inicial:
            for prefixo, rotulo in (("especialista", "Especialista"), ("servente", "Servente")):
                for index in range(1, 5):
                    nome = self.initial.get(f"{prefixo}_{index}", getattr(self.instance, f"{prefixo}_{index}", "")) or ""
                    horas = self.initial.get(f"horas_{prefixo}_{index}", getattr(self.instance, f"horas_{prefixo}_{index}", None))
                    if nome or horas not in (None, ""):
                        equipa_inicial.append(
                            {
                                "funcao": rotulo,
                                "nome": str(nome).strip(),
                                "horas": float(horas) if horas not in (None, "") else None,
                            }
                        )
        self.equipa_turno_lista_inicial = []
        for item in equipa_inicial:
            if not isinstance(item, dict):
                continue
            self.equipa_turno_lista_inicial.append(
                {
                    "funcao": str(item.get("funcao") or "").strip(),
                    "nome": str(item.get("nome") or "").strip(),
                    "horas": float(item["horas"]) if item.get("horas") not in (None, "") else None,
                }
            )
        self.initial["equipa_turno"] = self.equipa_turno_lista_inicial
        self.fields["equipa_turno"].initial = self.equipa_turno_lista_inicial
        self.fields["equipa_turno"].help_text = "Adicione cada elemento da equipa com função, nome e horas."

        if registo:
            if not self.initial.get("cliente") and registo.projeto_id:
                self.initial["cliente"] = registo.projeto.cliente
                self.fields["cliente"].initial = registo.projeto.cliente
            if not self.initial.get("numero_sondagem") and registo.furo_id:
                self.initial["numero_sondagem"] = registo.furo.nome
                self.fields["numero_sondagem"].initial = registo.furo.nome
            if not self.initial.get("estaleiro") and registo.furo_id:
                self.initial["estaleiro"] = registo.furo.local_sondagem
                self.fields["estaleiro"].initial = registo.furo.local_sondagem
            if not self.initial.get("turno") and registo.planeamento_turno_id:
                self.initial["turno"] = registo.planeamento_turno.get_turno_display()
                self.fields["turno"].initial = registo.planeamento_turno.get_turno_display()
            if not self.initial.get("inclinacao") and registo.furo_id:
                inclinacao = registo.furo.inclinacao_real_atual
                if inclinacao is None:
                    inclinacao = registo.furo.inclinacao_planeada_atual
                if inclinacao is None:
                    inclinacao = registo.furo.inclinacao_planeada_inicial
                self.initial["inclinacao"] = inclinacao
                self.fields["inclinacao"].initial = inclinacao
            if not self.initial.get("no_inicio"):
                self.initial["no_inicio"] = registo.profundidade_furo_antes
                self.fields["no_inicio"].initial = registo.profundidade_furo_antes
            if not self.initial.get("no_final"):
                self.initial["no_final"] = registo.profundidade_furo_depois
                self.fields["no_final"].initial = registo.profundidade_furo_depois
            if not self.initial.get("avanco_turno") and registo.metros_furados is not None:
                self.initial["avanco_turno"] = registo.metros_furados
                self.fields["avanco_turno"].initial = registo.metros_furados
        self.secoes = [
            {
                "titulo": "Informação",
                "descricao": "Dados base do cliente, equipamento, identificação do relatório e resumo principal do turno.",
                "colunas": [
                    [
                        self["cliente"],
                        self["sonda"],
                        self["torre"],
                        self["bomba_injecao"],
                        self["bomba_captacao"],
                    ],
                    [
                        self["estaleiro"],
                        self["numero_sondagem"],
                        self["inclinacao"],
                        self["diametro_furo"],
                    ],
                    [
                        self["numero_relatorio"],
                        self["turno"],
                        self["no_inicio"],
                        self["no_final"],
                        self["avanco_turno"],
                        self["testemunho_recuperado"],
                        self["percentagem_recuperacao"],
                    ],
                ],
                "grid_classes": "grid grid-cols-1 lg:grid-cols-3 gap-4",
            },
            {
                "titulo": "Avanço e recuperação",
                "descricao": "Registe cada furada do turno numa linha própria com início, fim, avanço, recuperação, rocha e descrição.",
                "campos": [self["furacoes"]],
            },
            {
                "titulo": "Operações e ocorrências",
                "descricao": "Registe cada ocorrência como uma linha própria com tipo, hora de início e hora de fim.",
                "campos": [
                    self["operacoes_ocorrencias"],
                    self["polimeros"],
                    self["bit_novo"],
                    self["notas"],
                ],
                "grid_classes": "grid grid-cols-1 md:grid-cols-3 gap-4",
            },
            {
                "titulo": "Equipa",
                "descricao": "Adicione cada elemento da equipa numa linha com função, nome e horas.",
                "campos": [
                    self["equipa_turno"],
                ],
            },
        ]

    def clean(self):
        cleaned_data = super().clean()
        avanco_turno = cleaned_data.get("avanco_turno")
        testemunho_recuperado = cleaned_data.get("testemunho_recuperado")

        if avanco_turno not in (None, "") and testemunho_recuperado not in (None, ""):
            try:
                avanco_decimal = Decimal(str(avanco_turno))
                testemunho_decimal = Decimal(str(testemunho_recuperado))
            except Exception:
                return cleaned_data

            if avanco_decimal > 0:
                percentagem = (testemunho_decimal / avanco_decimal) * Decimal("100")
                cleaned_data["percentagem_recuperacao"] = percentagem.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )

        return cleaned_data

    def clean_polimeros(self):
        valor = self.cleaned_data.get("polimeros")
        if valor in (None, ""):
            return []
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError("Lista de polímeros inválida.") from exc
        if not isinstance(valor, list):
            raise forms.ValidationError("Lista de polímeros inválida.")
        polimeros = []
        for item in valor:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if item:
                polimeros.append(item[:120])
        return polimeros

    def clean_furacoes(self):
        valor = self.cleaned_data.get("furacoes")
        if valor in (None, ""):
            return []
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError("Lista de furadas inválida.") from exc
        if not isinstance(valor, list):
            raise forms.ValidationError("Lista de furadas inválida.")

        furacoes = []
        for index, item in enumerate(valor, start=1):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"A linha {index} da lista de furadas é inválida.")

            inicio = item.get("inicio")
            fim = item.get("fim")
            avanco = item.get("avanco")
            recuperacao = item.get("recuperacao")
            rocha = (item.get("rocha") or "").strip()
            descricao = (item.get("descricao") or "").strip()

            if all(campo in (None, "", []) for campo in [inicio, fim, avanco, recuperacao]) and not rocha and not descricao:
                continue

            try:
                inicio = float(inicio) if inicio not in (None, "") else None
                fim = float(fim) if fim not in (None, "") else None
                avanco = float(avanco) if avanco not in (None, "") else None
                recuperacao = float(recuperacao) if recuperacao not in (None, "") else None
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"A linha {index} da lista de furadas contém valores numéricos inválidos.") from exc

            for label, numero in (
                ("Furação início", inicio),
                ("Furação fim", fim),
                ("Furação avanço", avanco),
                ("Furação recuperação", recuperacao),
            ):
                if numero is not None and numero < 0:
                    raise forms.ValidationError(f"A linha {index} tem valor negativo em '{label}'.")

            if inicio is not None and fim is not None:
                if fim < inicio:
                    raise forms.ValidationError(f"A linha {index} tem 'Furação fim' inferior a 'Furação início'.")
                if avanco is None:
                    avanco = round(fim - inicio, 2)

            furacoes.append(
                {
                    "inicio": round(inicio, 2) if inicio is not None else None,
                    "fim": round(fim, 2) if fim is not None else None,
                    "avanco": round(avanco, 2) if avanco is not None else None,
                    "recuperacao": round(recuperacao, 2) if recuperacao is not None else None,
                    "rocha": rocha[:200],
                    "descricao": descricao[:500],
                }
            )

        return furacoes

    def clean_operacoes_ocorrencias(self):
        valor = self.cleaned_data.get("operacoes_ocorrencias")
        if valor in (None, ""):
            return []
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError("Lista de operações e ocorrências inválida.") from exc
        if not isinstance(valor, list):
            raise forms.ValidationError("Lista de operações e ocorrências inválida.")

        tipos_validos = {chave for chave, _ in RegistoDiarioEmpregado.RELATORIO_OCORRENCIA_CHOICES}
        operacoes = []
        for index, item in enumerate(valor, start=1):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"A linha {index} da lista de operações e ocorrências é inválida.")

            tipo = (item.get("tipo") or "").strip()
            hora_de = (item.get("de") or "").strip()
            hora_ate = (item.get("ate") or "").strip()

            if not tipo and not hora_de and not hora_ate:
                continue

            if tipo not in tipos_validos:
                raise forms.ValidationError(f"A linha {index} tem um tipo de ocorrência inválido.")

            if not hora_de or not hora_ate:
                raise forms.ValidationError(f"A linha {index} tem de preencher 'De' e 'Até'.")

            for label, hora in (("De", hora_de), ("Até", hora_ate)):
                try:
                    datetime.strptime(hora, "%H:%M")
                except ValueError as exc:
                    raise forms.ValidationError(f"A linha {index} contém uma hora inválida em '{label}'.") from exc

            operacoes.append(
                {
                    "tipo": tipo,
                    "de": hora_de,
                    "ate": hora_ate,
                }
            )
        return operacoes

    def clean_equipa_turno(self):
        valor = self.cleaned_data.get("equipa_turno")
        if valor in (None, ""):
            return []
        if isinstance(valor, str):
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError("Lista da equipa do turno inválida.") from exc
        if not isinstance(valor, list):
            raise forms.ValidationError("Lista da equipa do turno inválida.")

        equipa = []
        for index, item in enumerate(valor, start=1):
            if not isinstance(item, dict):
                raise forms.ValidationError(f"A linha {index} da equipa do turno é inválida.")

            funcao = (item.get("funcao") or "").strip()
            nome = (item.get("nome") or "").strip()
            horas = item.get("horas")

            if not funcao and not nome and horas in (None, "", []):
                continue
            if not funcao or not nome:
                raise forms.ValidationError(f"A linha {index} da equipa do turno tem de preencher 'Função' e 'Nome'.")
            try:
                horas = float(horas) if horas not in (None, "") else None
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"A linha {index} da equipa do turno contém horas inválidas.") from exc
            if horas is not None and horas < 0:
                raise forms.ValidationError(f"A linha {index} da equipa do turno não pode ter horas negativas.")

            equipa.append(
                {
                    "funcao": funcao[:80],
                    "nome": nome[:120],
                    "horas": round(horas, 2) if horas is not None else None,
                }
            )
        return equipa
