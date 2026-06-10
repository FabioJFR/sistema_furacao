from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .empregado import Empregados
from .furo import Furo


class ConfiguracaoPerfuracaoEmpregado(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="configuracoes_perfuracao",
    )
    # TODO futuro:
    # - histórico de alterações da configuração (versionamento)
    # - guardar parâmetros por tipo de equipamento
    # - auditoria detalhada de alterações (quem, quando, o quê)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="configuracoes_perfuracao",
    )

    furo = models.ForeignKey(
        Furo,
        on_delete=models.CASCADE,
        related_name="configuracoes_perfuracao",
    )

    medida_morta = models.FloatField(default=0.0)

    # String de perfuração
    comprimento_tubo = models.FloatField(default=3.0)
    comprimento_karoutier = models.FloatField(default=0.0)
    quantidade_karoutier = models.PositiveIntegerField(default=1)
    comprimento_acrescento = models.FloatField(default=0.0)
    quantidade_acrescento = models.PositiveIntegerField(default=1)
    comprimento_calibrador = models.FloatField(default=0.0)
    quantidade_calibrador = models.PositiveIntegerField(default=1)
    comprimento_record = models.FloatField(default=0.0)
    quantidade_record = models.PositiveIntegerField(default=1)
    comprimento_bit = models.FloatField(default=0.0)

    # Conjunto interior
    comprimento_caixa_mola = models.FloatField(default=0.0)
    comprimento_tubo_interior = models.FloatField(default=0.0)
    quantidade_tubo_interior = models.PositiveIntegerField(default=1)
    comprimento_acrescento_tubo_interior = models.FloatField(default=0.0)
    quantidade_acrescento_tubo_interior = models.PositiveIntegerField(default=1)
    comprimento_cabeca_interior = models.FloatField(default=0.0)

    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configuracoes_perfuracao_atualizadas",
    )

    class Meta:
        unique_together = ("furo",)
        ordering = ["furo__nome"]
        verbose_name = "Configuração de Perfuração do Furo"
        verbose_name_plural = "Configurações de Perfuração dos Furos"

    def __str__(self):
        nome_empregado = self.empregado.nome if self.empregado_id and self.empregado else "-"
        nome_furo = self.furo.nome if self.furo_id and self.furo else "-"
        return f"{nome_empregado} - {nome_furo}"

    @property
    def comprimento_total_conjunto_fundo(self):
        return (
            (float(self.comprimento_karoutier or 0) * int(self.quantidade_karoutier or 0))
            + (float(self.comprimento_acrescento or 0) * int(self.quantidade_acrescento or 0))
            + (float(self.comprimento_calibrador or 0) * int(self.quantidade_calibrador or 0))
            + (float(self.comprimento_record or 0) * int(self.quantidade_record or 0))
            + float(self.comprimento_bit or 0)
        )

    @property
    def comprimento_total_tubo_interior(self):
        return (
            + float(self.comprimento_caixa_mola or 0)
            + (float(self.comprimento_tubo_interior or 0) * int(self.quantidade_tubo_interior or 0))
            + (float(self.comprimento_acrescento_tubo_interior or 0) * int(self.quantidade_acrescento_tubo_interior or 0))
            + float(self.comprimento_cabeca_interior or 0)
        )

    def clean(self):
        super().clean()

        # TODO futuro:
        # - validar limites técnicos dos comprimentos
        # - validar consistência entre componentes (string de perfuração)

        if self.empregado and not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.empregado and self.furo:
            if self.empregado.empresa_id and self.furo.empresa_id:
                if self.empregado.empresa_id != self.furo.empresa_id:
                    raise ValidationError({
                        "furo": "O empregado que altera a configuração deve pertencer à mesma empresa do furo."
                    })

        if self.empresa_id:
            if self.empregado and self.empregado.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do empregado."
                })

            if self.furo and self.furo.empresa_id and self.empresa_id != self.furo.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa deve ser a mesma do furo."
                })

        for field_name in [
            "medida_morta",
            "comprimento_tubo",
            "comprimento_karoutier",
            "comprimento_acrescento",
            "comprimento_calibrador",
            "comprimento_record",
            "comprimento_bit",
            "comprimento_caixa_mola",
            "comprimento_tubo_interior",
            "comprimento_acrescento_tubo_interior",
            "comprimento_cabeca_interior",
        ]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({
                    field_name: "O comprimento não pode ser negativo."
                })

        for field_name in [
            "quantidade_karoutier",
            "quantidade_acrescento",
            "quantidade_calibrador",
            "quantidade_record",
            "quantidade_tubo_interior",
            "quantidade_acrescento_tubo_interior",
        ]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({
                    field_name: "A quantidade não pode ser negativa."
                })

    def save(self, *args, **kwargs):
        if self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id
        elif self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
