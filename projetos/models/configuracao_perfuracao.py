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

    # String de perfuração
    comprimento_tubo = models.FloatField(default=3.0)
    comprimento_karoutier = models.FloatField(default=0.0)
    comprimento_acrescento = models.FloatField(default=0.0)
    comprimento_calibrador = models.FloatField(default=0.0)
    comprimento_record = models.FloatField(default=0.0)
    comprimento_bit = models.FloatField(default=0.0)

    # Conjunto interior
    comprimento_caixa_mola = models.FloatField(default=0.0)
    comprimento_tubo_interior = models.FloatField(default=0.0)
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
        # TODO futuro:
        # - avaliar se unique_together deve permitir histórico por data
        # - criar índice por furo para otimização
        unique_together = ("empregado", "furo")
        ordering = ["furo__nome"]
        verbose_name = "Configuração de Perfuração do Empregado"
        verbose_name_plural = "Configurações de Perfuração dos Empregados"

    def __str__(self):
        nome_empregado = self.empregado.nome if self.empregado_id and self.empregado else "-"
        nome_furo = self.furo.nome if self.furo_id and self.furo else "-"
        return f"{nome_empregado} - {nome_furo}"

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
                        "furo": "O empregado e o furo devem pertencer à mesma empresa."
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
            "comprimento_tubo",
            "comprimento_karoutier",
            "comprimento_acrescento",
            "comprimento_calibrador",
            "comprimento_record",
            "comprimento_bit",
            "comprimento_caixa_mola",
            "comprimento_tubo_interior",
            "comprimento_cabeca_interior",
        ]:
            valor = getattr(self, field_name, None)
            if valor is not None and valor < 0:
                raise ValidationError({
                    field_name: "O comprimento não pode ser negativo."
                })

    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)