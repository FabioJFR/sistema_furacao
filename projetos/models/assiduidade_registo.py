import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AssiduidadeRegisto(models.Model):
    TIPO_CHOICES = [
        ("presenca", "Presença"),
        ("falta", "Falta"),
        ("ferias", "Férias"),
        ("baixa", "Baixa"),
        ("hora_extra", "Hora Extra"),
    ]

    ESTADO_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="assiduidades",
    )
    empregado = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.CASCADE,
        related_name="assiduidades",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assiduidades",
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="presenca")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendente")
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    horas = models.FloatField(default=0.0)
    motivo = models.CharField(max_length=220, blank=True)
    notas = models.TextField(blank=True)

    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_inicio", "-atualizado_em"]
        verbose_name = "Registo de Assiduidade"
        verbose_name_plural = "Registos de Assiduidade"

    def __str__(self):
        return f"{self.empregado.nome} · {self.get_tipo_display()} · {self.data_inicio}"

    def clean(self):
        super().clean()
        if not self.empresa_id:
            raise ValidationError({"empresa": "O registo deve estar associado a uma empresa."})
        if self.empregado and self.empregado.empresa_id != self.empresa_id:
            raise ValidationError({"empregado": "O empregado deve pertencer à mesma empresa."})
        if self.projeto and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({"projeto": "O projeto deve pertencer à mesma empresa."})
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data fim não pode ser anterior à data início."})
        if self.horas < 0:
            raise ValidationError({"horas": "As horas não podem ser negativas."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
