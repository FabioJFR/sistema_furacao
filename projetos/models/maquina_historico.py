import uuid

from django.core.exceptions import ValidationError
from django.db import models


class MaquinaEventoOperacional(models.Model):
    TIPO_EVENTO_CHOICES = [
        ("alocacao_projeto", "Alocação a projeto"),
        ("alocacao_furo", "Alocação a furo"),
        ("operacao_turno", "Operação em turno"),
        ("avaria_reportada", "Avaria reportada"),
        ("avaria_resolvida", "Avaria resolvida"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="maquina_eventos_operacionais",
    )
    maquina = models.ForeignKey(
        "projetos.Maquina",
        on_delete=models.CASCADE,
        related_name="eventos_operacionais",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_eventos_operacionais",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_eventos_operacionais",
    )
    empregado = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_eventos_operacionais",
    )
    registo = models.ForeignKey(
        "projetos.RegistoDiarioEmpregado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_eventos_operacionais",
    )
    tipo_evento = models.CharField(max_length=30, choices=TIPO_EVENTO_CHOICES)
    data_evento = models.DateField(null=True, blank=True)
    data_inicio = models.DateTimeField(null=True, blank=True)
    data_fim = models.DateTimeField(null=True, blank=True)
    metros_furados = models.FloatField(default=0.0)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_evento", "-criado_em"]
        verbose_name = "Evento operacional da máquina"
        verbose_name_plural = "Eventos operacionais da máquina"

    def clean(self):
        super().clean()

        if self.maquina_id and self.empresa_id and self.maquina.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do evento deve ser a mesma da máquina."})

        if self.projeto_id and self.empresa_id and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({"projeto": "O projeto deve pertencer à mesma empresa do evento."})

        if self.furo_id and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({"furo": "O furo deve pertencer à mesma empresa do evento."})

        if self.empregado_id and self.empresa_id and self.empregado.empresa_id != self.empresa_id:
            raise ValidationError({"empregado": "O empregado deve pertencer à mesma empresa do evento."})

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data fim não pode ser anterior à data início."})

    def save(self, *args, **kwargs):
        if self.maquina_id and not self.empresa_id:
            self.empresa_id = self.maquina.empresa_id
        self.full_clean()
        return super().save(*args, **kwargs)


class MaquinaAvaria(models.Model):
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("em_reparacao", "Em reparação"),
        ("resolvida", "Resolvida"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="maquina_avarias",
    )
    maquina = models.ForeignKey(
        "projetos.Maquina",
        on_delete=models.CASCADE,
        related_name="avarias",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_avarias",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maquina_avarias",
    )
    reportado_por = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avarias_reportadas_maquina",
    )
    responsavel_empregado = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avarias_responsavel_maquina",
    )
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")
    descricao = models.TextField()
    solucao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_inicio", "-criado_em"]
        verbose_name = "Avaria da máquina"
        verbose_name_plural = "Avarias da máquina"

    def clean(self):
        super().clean()
        if self.maquina_id and self.empresa_id and self.maquina.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da avaria deve ser a mesma da máquina."})
        if (
            self.responsavel_empregado_id
            and self.empresa_id
            and self.responsavel_empregado.empresa_id != self.empresa_id
        ):
            raise ValidationError({"responsavel_empregado": "O responsável deve pertencer à mesma empresa da avaria."})
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data fim não pode ser anterior à data início."})

    def save(self, *args, **kwargs):
        if self.maquina_id and not self.empresa_id:
            self.empresa_id = self.maquina.empresa_id
        self.full_clean()
        return super().save(*args, **kwargs)
