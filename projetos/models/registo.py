import uuid
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models

from .empregado import Empregados
from .projeto import Projeto
from .furo import Furo


def _juntar_data_hora(data, hora):
    return datetime.combine(data, hora)


def _hora_apos(data, base_hora, hora_para_validar):
    base_dt = _juntar_data_hora(data, base_hora)
    hora_dt = _juntar_data_hora(data, hora_para_validar)

    if hora_dt < base_dt:
        hora_dt += timedelta(days=1)

    return hora_dt


class RegistoDiarioEmpregado(models.Model):
    TIPO_PARAGEM_CHOICES = [
        ("", "---------"),
        ("cliente", "Cliente"),
        ("empresa", "Empresa"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="registos_diarios"
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="registos_diarios"
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_projeto"
    )

    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_furo"
    )

    data = models.DateField(null=True, blank=True)

    hora_inicio = models.TimeField(null=True, blank=True)
    hora_inicio_pausa = models.TimeField(null=True, blank=True)
    hora_fim_pausa = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    horas_trabalhadas = models.FloatField(default=0.0)
    horas_trabalhadas_furo = models.DurationField(null=True, blank=True)

    horas_paragem = models.FloatField(default=0.0)
    tipo_paragem = models.CharField(
        max_length=20,
        choices=TIPO_PARAGEM_CHOICES,
        blank=True,
        default=""
    )

    metros_furados = models.FloatField(default=0.0)
    observacoes = models.TextField(blank=True)

    relatorio_foto = models.ImageField(
        upload_to="registos_diarios/relatorios/",
        blank=True,
        null=True
    )

    # ------------------------
    # SNAPSHOT DA PROFUNDIDADE
    # ------------------------
    profundidade_furo_antes = models.FloatField(default=0.0)
    profundidade_furo_depois = models.FloatField(default=0.0)

    # ------------------------
    # SNAPSHOT DO PLANEAMENTO INICIAL
    # ------------------------
    profundidade_alvo_inicial_furo = models.FloatField(default=0.0)
    inclinacao_planeada_inicial_furo = models.FloatField(null=True, blank=True)
    azimute_planeado_inicial_furo = models.FloatField(null=True, blank=True)

    # ------------------------
    # SNAPSHOT DO PLANEAMENTO ATUAL
    # ------------------------
    profundidade_alvo_atual_furo = models.FloatField(default=0.0)
    inclinacao_planeada_atual_furo = models.FloatField(null=True, blank=True)
    azimute_planeado_atual_furo = models.FloatField(null=True, blank=True)

    # ------------------------
    # SNAPSHOT DO ESTADO REAL
    # ------------------------
    inclinacao_real_atual_furo = models.FloatField(null=True, blank=True)
    azimute_real_atual_furo = models.FloatField(null=True, blank=True)

    editado_por_empregado = models.BooleanField(default=False)
    editado_em = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data", "-criado_em"]
        verbose_name = "Registo Diário do Empregado"
        verbose_name_plural = "Registos Diários dos Empregados"

    def __str__(self):
        return f"{self.empregado.nome} - {self.data}"

    def clean(self):
        super().clean()

        if getattr(self, "empregado_id", None):
            empregado = getattr(self, "empregado", None)
            if not empregado or not getattr(empregado, "empresa_id", None):
                raise ValidationError("O empregado não está associado a uma empresa.")

        if self.projeto and not self.projeto.empresa_id:
            raise ValidationError({
                "projeto": "O projeto tem de estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo tem de estar associado a uma empresa."
            })

        if self.empregado and self.empregado.empresa_id:
            if self.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do registo deve ser a mesma do empregado."
                })
        if self.projeto and self.empregado and self.empregado.empresa_id:
            if self.projeto.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "projeto": "O projeto selecionado não pertence à empresa do empregado."
                })

        if self.furo and self.empregado and self.empregado.empresa_id:
            if self.furo.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "furo": "O furo selecionado não pertence à empresa do empregado."
                })

        if self.projeto and self.furo:
            if self.projeto.empresa_id and self.furo.empresa_id:
                if self.projeto.empresa_id != self.furo.empresa_id:
                    raise ValidationError({
                        "furo": "O furo e o projeto têm de pertencer à mesma empresa."
                    })

        if self.projeto and self.empresa_id and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({
                "projeto": "O projeto selecionado não pertence à empresa definida no registo."
            })

        if self.furo and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence à empresa definida no registo."
            })

        if self.furo and self.projeto and self.furo.projeto_id != self.projeto.id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence ao projeto escolhido."
            })

        # Regra operacional:
        # Furo concluído não aceita novos registos.
        # Em edição, permite guardar se o registo já estava ligado ao mesmo furo.
        if self.furo and self.furo.estado == "concluido":
            if not self.pk:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos relatórios."
                })
            original = RegistoDiarioEmpregado.objects.filter(pk=self.pk).only("furo_id").first()
            if original and original.furo_id != self.furo_id:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos relatórios."
                })

        if self.metros_furados is not None and self.metros_furados < 0:
            raise ValidationError({
                "metros_furados": "Os metros furados não podem ser negativos."
            })

        if self.horas_paragem is not None and self.horas_paragem < 0:
            raise ValidationError({
                "horas_paragem": "As horas de paragem não podem ser negativas."
            })

        horarios = [
            self.hora_inicio,
            self.hora_inicio_pausa,
            self.hora_fim_pausa,
            self.hora_fim,
        ]
        total_horarios = sum(1 for h in horarios if h is not None)

        if 0 < total_horarios < 4:
            raise ValidationError(
                "Preencha todos os horários do turno ou deixe todos em branco."
            )

        if total_horarios == 4:
            if not self.data:
                raise ValidationError({
                    "data": "A data é obrigatória quando preenche os horários."
                })

            inicio_dt = _juntar_data_hora(self.data, self.hora_inicio)
            inicio_pausa_dt = _hora_apos(self.data, self.hora_inicio, self.hora_inicio_pausa)
            fim_pausa_dt = _hora_apos(self.data, self.hora_inicio_pausa, self.hora_fim_pausa)
            fim_dt = _hora_apos(self.data, self.hora_fim_pausa, self.hora_fim)

            if inicio_pausa_dt < inicio_dt:
                raise ValidationError({
                    "hora_inicio_pausa": "A hora de início da pausa deve ser posterior à hora de início."
                })

            if fim_pausa_dt < inicio_pausa_dt:
                raise ValidationError({
                    "hora_fim_pausa": "A hora de fim da pausa deve ser posterior à hora de início da pausa."
                })

            if fim_dt < fim_pausa_dt:
                raise ValidationError({
                    "hora_fim": "A hora de fim deve ser posterior à hora de fim da pausa."
                })

        if self.horas_paragem is not None and self.horas_paragem > 0 and not self.tipo_paragem:
            raise ValidationError({
                "tipo_paragem": "Selecione se a paragem é Cliente ou Empresa."
            })

    def calcular_horas_trabalhadas(self):
        if not all([
            self.data,
            self.hora_inicio is not None,
            self.hora_inicio_pausa is not None,
            self.hora_fim_pausa is not None,
            self.hora_fim is not None,
        ]):
            return 0.0

        dt_inicio = _juntar_data_hora(self.data, self.hora_inicio)
        dt_inicio_pausa = _hora_apos(self.data, self.hora_inicio, self.hora_inicio_pausa)
        dt_fim_pausa = _hora_apos(self.data, self.hora_inicio_pausa, self.hora_fim_pausa)
        dt_fim = _hora_apos(self.data, self.hora_fim_pausa, self.hora_fim)

        periodo_total = (dt_fim - dt_inicio).total_seconds()
        pausa = (dt_fim_pausa - dt_inicio_pausa).total_seconds()

        horas = (periodo_total - pausa) / 3600
        return max(round(horas, 2), 0.0)

    def save(self, *args, **kwargs):
        if self.empregado_id and self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.projeto_id and self.projeto and self.projeto.empresa_id:
            self.empresa_id = self.projeto.empresa_id
        elif self.furo_id and self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.horas_trabalhadas = self.calcular_horas_trabalhadas()
        self.horas_trabalhadas_furo = timedelta(hours=self.horas_trabalhadas or 0.0)

        self.full_clean()
        super().save(*args, **kwargs)
