import uuid

from django.core.exceptions import ValidationError
from django.db import models


class SessaoDispositivo(models.Model):
    STATUS_CHOICES = [
        ("criada", "Criada"),
        ("ligando", "Ligando"),
        ("ligado", "Ligado"),
        ("erro", "Erro"),
        ("encerrada", "Encerrada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    dispositivo = models.ForeignKey(
        "dispositivos.Dispositivo",
        on_delete=models.CASCADE,
        related_name="sessoes",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="sessoes_dispositivos",
    )
    empregado = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_dispositivos",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_dispositivo",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="criada")
    mensagem_erro = models.TextField(blank=True)

    iniciado_em = models.DateTimeField(auto_now_add=True)
    terminado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sessão de Dispositivo"
        verbose_name_plural = "Sessões de Dispositivos"
        ordering = ["-iniciado_em"]

    def __str__(self):
        nome_dispositivo = self.dispositivo.nome if self.dispositivo else "-"
        return f"{nome_dispositivo} - {self.get_status_display()}"

    def clean(self):
        super().clean()

        if self.dispositivo and self.empresa_id and self.dispositivo.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa da sessão deve ser a mesma do dispositivo."
            })

        if self.empregado and not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.empregado and self.empresa_id and self.empregado.empresa_id != self.empresa_id:
            raise ValidationError({
                "empregado": "O empregado não pertence à empresa da sessão."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.furo and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "furo": "O furo não pertence à empresa da sessão."
            })

        if self.terminado_em and self.terminado_em < self.iniciado_em:
            raise ValidationError({
                "terminado_em": "A data de término não pode ser inferior à data de início."
            })

    def save(self, *args, **kwargs):
        if self.dispositivo and self.dispositivo.empresa_id:
            self.empresa_id = self.dispositivo.empresa_id
        elif self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
