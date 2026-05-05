from django.core.exceptions import ValidationError
from django.db import models


class SalarioBaseFuncao(models.Model):
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="salarios_base_funcoes",
    )
    funcao = models.CharField(max_length=100)
    salario_base = models.FloatField(default=0.0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("empresa", "funcao")
        ordering = ["funcao"]
        verbose_name = "Salário base por função"
        verbose_name_plural = "Salários base por função"

    def clean(self):
        super().clean()
        if self.salario_base is not None and self.salario_base < 0:
            raise ValidationError({"salario_base": "O salário base não pode ser negativo."})

    def __str__(self):
        return f"{self.empresa_id} · {self.funcao}: {self.salario_base}"

