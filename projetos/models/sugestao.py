import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class SugestaoPlataforma(models.Model):
    AVALIACAO_CHOICES = [
        ("excelente", "Excelente"),
        ("boa", "Boa"),
        ("regular", "Regular"),
        ("fraca", "Fraca"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sugestoes_plataforma",
    )
    avaliacao = models.CharField(max_length=20, choices=AVALIACAO_CHOICES)
    opiniao = models.TextField(blank=True)
    sugestoes = models.TextField()
    email_destino = models.EmailField(blank=True)
    enviado_por_email = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Sugestão da Plataforma"
        verbose_name_plural = "Sugestões da Plataforma"

    def clean(self):
        super().clean()
        if not self.user_id:
            raise ValidationError({"user": "A sugestão deve estar associada a um utilizador."})
        if not (self.sugestoes or "").strip():
            raise ValidationError({"sugestoes": "Escreve pelo menos uma sugestão de melhoria."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

