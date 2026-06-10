import uuid
from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PlaneamentoTurno(models.Model):
    TURNO_CHOICES = [
        ("manha", "Manhã"),
        ("tarde", "Tarde"),
        ("noite", "Noite"),
        ("extra", "Extra"),
        ("extra_manha", "Extra Manhã"),
        ("extra_tarde", "Extra Tarde"),
        ("extra_noite", "Extra Noite"),
    ]

    ESTADO_CHOICES = [
        ("planeado", "Planeado"),
        ("confirmado", "Confirmado"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="planeamentos_turnos",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.CASCADE,
        related_name="planeamentos_turnos",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planeamentos_turnos",
    )
    empregado = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planeamentos_turnos",
    )
    maquina = models.ForeignKey(
        "projetos.Maquina",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planeamentos_turnos",
    )

    nome = models.CharField(max_length=180, blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, default="manha")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="planeado")
    prioridade = models.PositiveSmallIntegerField(default=2)
    objetivo = models.CharField(max_length=220, blank=True)
    notas = models.TextField(blank=True)

    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_inicio", "turno", "-atualizado_em"]
        verbose_name = "Planeamento de Turno"
        verbose_name_plural = "Planeamento de Turnos"

    def __str__(self):
        if self.nome:
            return self.nome
        projeto_nome = self.projeto.nome if self.projeto_id and self.projeto else "-"
        horario = self.intervalo_horario_display
        return f"{self.data_inicio} · {self.get_turno_display()}{f' · {horario}' if horario else ''} · {projeto_nome}"

    @property
    def nome_efetivo(self):
        if self.nome:
            return self.nome
        partes = [self.get_turno_display(), self.data_inicio.strftime("%d/%m/%Y")]
        if self.maquina_id and self.maquina:
            partes.append(self.maquina.nome)
        elif self.projeto_id and self.projeto:
            partes.append(self.projeto.nome)
        return " · ".join(partes)

    @property
    def hora_inicio_efetiva(self):
        return self.hora_inicio or time(0, 0)

    @property
    def hora_fim_efetiva(self):
        return self.hora_fim or time(23, 59, 59)

    @property
    def inicio_datetime(self):
        return datetime.combine(self.data_inicio, self.hora_inicio_efetiva)

    @property
    def fim_datetime(self):
        data_fim = self.data_fim or self.data_inicio
        return datetime.combine(data_fim, self.hora_fim_efetiva)

    @property
    def intervalo_horario_display(self):
        if self.hora_inicio and self.hora_fim:
            return f"{self.hora_inicio.strftime('%H:%M')} - {self.hora_fim.strftime('%H:%M')}"
        if self.hora_inicio:
            return f"{self.hora_inicio.strftime('%H:%M')} - ?"
        if self.hora_fim:
            return f"? - {self.hora_fim.strftime('%H:%M')}"
        return ""

    def clean(self):
        super().clean()
        if not self.empresa_id:
            raise ValidationError({"empresa": "O planeamento deve estar associado a uma empresa."})

        projeto = self.projeto if self.projeto_id else None
        furo = self.furo if self.furo_id else None
        empregado = self.empregado if self.empregado_id else None
        maquina = self.maquina if self.maquina_id else None

        if projeto and projeto.empresa_id != self.empresa_id:
            raise ValidationError({"projeto": "O projeto deve pertencer à mesma empresa."})

        if furo and furo.empresa_id != self.empresa_id:
            raise ValidationError({"furo": "O furo deve pertencer à mesma empresa."})
        if furo and furo.projeto_id != self.projeto_id:
            raise ValidationError({"furo": "O furo deve pertencer ao projeto selecionado."})

        if empregado and empregado.empresa_id != self.empresa_id:
            raise ValidationError({"empregado": "O empregado deve pertencer à mesma empresa."})

        if maquina and maquina.empresa_id != self.empresa_id:
            raise ValidationError({"maquina": "A máquina deve pertencer à mesma empresa."})

        turno_maquina = None
        if maquina and self.turno:
            turno_maquina = (
                maquina.turnos_maquina.filter(turno=self.turno, ativo=True)
                .order_by("-atualizado_em")
                .first()
            )

        # Se a hora fim for inferior/igual à hora início, tratamos como turno que
        # atravessa a meia-noite e avançamos automaticamente a data fim.
        if self.hora_inicio and self.hora_fim and self.hora_fim <= self.hora_inicio:
            if not self.data_fim or self.data_fim <= self.data_inicio:
                self.data_fim = self.data_inicio + timedelta(days=1)

        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data fim não pode ser anterior à data início."})

        if turno_maquina:
            if self.hora_inicio != turno_maquina.hora_inicio:
                raise ValidationError(
                    {
                        "hora_inicio": (
                            f"Para a máquina '{maquina.nome}', o turno "
                            f"'{turno_maquina.get_turno_display()}' tem de começar às "
                            f"{turno_maquina.hora_inicio.strftime('%H:%M')}."
                        )
                    }
                )
            if self.hora_fim != turno_maquina.hora_fim:
                raise ValidationError(
                    {
                        "hora_fim": (
                            f"Para a máquina '{maquina.nome}', o turno "
                            f"'{turno_maquina.get_turno_display()}' tem de terminar às "
                            f"{turno_maquina.hora_fim.strftime('%H:%M')}."
                        )
                    }
                )
            if turno_maquina.atravessa_meia_noite and (self.data_fim or self.data_inicio) <= self.data_inicio:
                raise ValidationError(
                    {
                        "data_fim": (
                            f"Para a máquina '{maquina.nome}', o turno "
                            f"'{turno_maquina.get_turno_display()}' termina no dia seguinte."
                        )
                    }
                )

        if (
            self.hora_inicio
            and self.hora_fim
            and (self.data_fim or self.data_inicio) == self.data_inicio
            and self.hora_fim <= self.hora_inicio
        ):
            raise ValidationError(
                {
                    "hora_fim": "A hora fim tem de ser posterior à hora início quando o turno termina no mesmo dia."
                }
            )

        if not (1 <= int(self.prioridade or 0) <= 5):
            raise ValidationError({"prioridade": "A prioridade deve estar entre 1 e 5."})

    def save(self, *args, **kwargs):
        if not self.nome:
            self.nome = self.nome_efetivo
        self.full_clean()
        super().save(*args, **kwargs)
