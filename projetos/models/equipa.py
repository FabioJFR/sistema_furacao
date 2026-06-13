import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Equipa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="equipas",
    )
    nome = models.CharField(max_length=160)
    membros = models.ManyToManyField(
        "projetos.Empregados",
        blank=True,
        related_name="equipas",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nome"],
                name="projetos_equipa_nome_unico_por_empresa",
            )
        ]
        verbose_name = "Equipa"
        verbose_name_plural = "Equipas"

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if not self.empresa_id:
            raise ValidationError({"empresa": "A equipa deve estar associada a uma empresa."})
