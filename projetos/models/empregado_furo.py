from django.db import models
from .empregado import Empregados
from .furo import Furo


class EmpregadoFuro(models.Model):
    FUNCAO_CHOICES = [
        ("sondador", "Sondador"),
        ("sondador_1", "Sondador 1ª"),
        ("sondador_2", "Sondador 2ª"),
        ("sondador_3", "Sondador 3ª"),
        ("ajudante_sondador", "Ajudante de Sondador"),
        ("ajudante_sondador_1", "Ajudante Sondador 1ª"),
        ("ajudante_sondador_2", "Ajudante Sondador 2ª"),
        ("ajudante_sondador_3", "Ajudante Sondador 3ª"),
        ("mecanico", "Mecânico"),
        ("ajudante_mecanico", "Ajudante Mecânico"),
        ("administrador", "Administrador"),
        ("encarregado_obra", "Encarregado de Obra"),
        ("chefe_turno", "Chefe de Turno"),
        ("geologo", "Geólogo"),
        ("supervisor", "Supervisor"),
        ("fiscal_cliente", "Fiscal do Cliente"),
        ("tecnico_seguranca", "Técnico de Segurança"),
        ("almoxarife", "Almoxarife"),
        ("motorista", "Motorista"),
        ("outro", "Outro"),
    ]

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="ligacoes_furos"
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.CASCADE,
        related_name="ligacoes_empregados"
    )
    funcao = models.CharField(
        max_length=50,
        choices=FUNCAO_CHOICES,
        default="ajudante_sondador"
    )
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empregado no Furo"
        verbose_name_plural = "Empregados nos Furos"
        ordering = ["-ativo", "empregado__nome"]
        unique_together = ("empregado", "furo")

    def __str__(self):
        return f"{self.empregado.nome} - {self.furo.nome} ({self.get_funcao_display()})"