import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Individual(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_individual",
    )
    nome = models.CharField(max_length=200)
    especialidade = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    data_nascimento = models.DateField(null=True, blank=True)
    data_inicio_atividade = models.DateField(null=True, blank=True)
    idade = models.IntegerField(blank=True, null=True)
    doc_id = models.BigIntegerField(blank=True, null=True)
    morada = models.CharField(max_length=200, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    nif = models.BigIntegerField(blank=True, null=True)
    curriculo = models.FileField(upload_to="individuais/curriculos/", blank=True, null=True)
    contrato = models.FileField(upload_to="individuais/documentos/", blank=True, null=True)
    biografia = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    total_horas = models.FloatField(default=0.0)
    total_metros = models.FloatField(default=0.0)
    total_registos = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    data_registo = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Individual"
        verbose_name_plural = "Individuais"

    def __str__(self):
        return self.nome or "Conta individual"

    def clean(self):
        super().clean()
        if not self.user_id:
            raise ValidationError({"user": "A conta individual deve estar ligada a um utilizador."})
        if self.idade is not None and self.idade < 0:
            raise ValidationError({"idade": "A idade não pode ser negativa."})
        if self.data_nascimento and self.data_inicio_atividade and self.data_inicio_atividade < self.data_nascimento:
            raise ValidationError({
                "data_inicio_atividade": "A data de início de atividade não pode ser anterior à data de nascimento."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
