import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PlaneamentoTurno(models.Model):
    TURNO_CHOICES = [
        ("manha", "Manhã"),
        ("tarde", "Tarde"),
        ("noite", "Noite"),
        ("extra", "Extra"),
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

    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
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
        projeto_nome = self.projeto.nome if self.projeto_id and self.projeto else "-"
        return f"{self.data_inicio} · {self.get_turno_display()} · {projeto_nome}"

    def clean(self):
        super().clean()
        if not self.empresa_id:
            raise ValidationError({"empresa": "O planeamento deve estar associado a uma empresa."})

        if self.projeto and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({"projeto": "O projeto deve pertencer à mesma empresa."})

        if self.furo and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({"furo": "O furo deve pertencer à mesma empresa."})
        if self.furo and self.furo.projeto_id != self.projeto_id:
            raise ValidationError({"furo": "O furo deve pertencer ao projeto selecionado."})

        if self.empregado and self.empregado.empresa_id != self.empresa_id:
            raise ValidationError({"empregado": "O empregado deve pertencer à mesma empresa."})

        if self.maquina and self.maquina.empresa_id != self.empresa_id:
            raise ValidationError({"maquina": "A máquina deve pertencer à mesma empresa."})

        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data fim não pode ser anterior à data início."})

        if not (1 <= int(self.prioridade or 0) <= 5):
            raise ValidationError({"prioridade": "A prioridade deve estar entre 1 e 5."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
