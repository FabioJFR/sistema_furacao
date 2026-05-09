from django import forms
from datetime import timedelta

from projetos.models import Empregados, Furo, Maquina, PlaneamentoTurno, Projeto
from projetos.selectors.forms import resolver_empresa_id
from projetos.services.maquinas import obter_turno_configurado_maquina


class PlaneamentoTurnoForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        empresa_id = resolver_empresa_id(empresa) if empresa is not None else None
        if empresa_id is None:
            self.fields["projeto"].queryset = Projeto.objects.none()
            self.fields["furo"].queryset = Furo.objects.none()
            self.fields["empregado"].queryset = Empregados.objects.none()
            self.fields["maquina"].queryset = Maquina.objects.none()
            return

        self.instance.empresa_id = empresa_id
        self.fields["projeto"].queryset = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["furo"].queryset = Furo.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["empregado"].queryset = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
        self.fields["maquina"].queryset = Maquina.objects.filter(empresa_id=empresa_id).order_by("nome")

    def clean(self):
        cleaned = super().clean()
        maquina = cleaned.get("maquina")
        turno = cleaned.get("turno")
        data_inicio = cleaned.get("data_inicio")
        turno_maquina = obter_turno_configurado_maquina(maquina=maquina, turno=turno)

        if not turno_maquina:
            return cleaned

        # Se a máquina tiver horário próprio para este turno, ele prevalece sempre.
        cleaned["hora_inicio"] = turno_maquina.hora_inicio
        cleaned["hora_fim"] = turno_maquina.hora_fim

        if data_inicio and turno_maquina.atravessa_meia_noite:
            data_fim = cleaned.get("data_fim")
            if not data_fim or data_fim <= data_inicio:
                cleaned["data_fim"] = data_inicio + timedelta(days=1)

        return cleaned

    class Meta:
        model = PlaneamentoTurno
        fields = [
            "nome",
            "projeto",
            "furo",
            "empregado",
            "maquina",
            "data_inicio",
            "data_fim",
            "hora_inicio",
            "hora_fim",
            "turno",
            "estado",
            "prioridade",
            "objetivo",
            "notas",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Turno Noite CS-14"}),
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }
