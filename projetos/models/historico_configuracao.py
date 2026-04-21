from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .empregado import Empregados
from .furo import Furo
from .configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregado


class HistoricoConfiguracaoPerfuracao(models.Model):
    ACAO_CHOICES = [
        ("criado", "Criado"),
        ("editado", "Editado"),
        ("apagado", "Apagado"),
    ]

    configuracao = models.ForeignKey(
        ConfiguracaoPerfuracaoEmpregado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos",
    )

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="historicos_configuracao",
    )

    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_configuracao",
    )

    acao = models.CharField(
        max_length=20,
        choices=ACAO_CHOICES,
    )

    # TODO futuro:
    # - avaliar retenção/arquivamento do histórico conforme volume de dados
    # - guardar diff detalhado entre versões além do snapshot completo
    # - suportar categorização do motivo da alteração
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="historicos_configuracao"
    )

    # Snapshot dos valores da configuração no momento da alteração
    comprimento_tubo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comprimento_karoutier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_karoutier = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_acrescento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_acrescento = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_calibrador = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_calibrador = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_record = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_record = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_bit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comprimento_caixa_mola = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comprimento_tubo_interior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_tubo_interior = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_acrescento_tubo_interior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantidade_acrescento_tubo_interior = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=1,
    )
    comprimento_cabeca_interior = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    observacoes = models.TextField(
        blank=True,
        null=True,
        help_text="Observações sobre a alteração efetuada."
    )

    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_alterados_configuracao",
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de Configuração de Perfuração"
        verbose_name_plural = "Históricos de Configuração de Perfuração"
        ordering = ["-criado_em"]

    def __str__(self):
        nome_empregado = self.empregado.nome if self.empregado else "-"
        nome_furo = self.furo.nome if self.furo else "-"
        return f"{nome_empregado} - {nome_furo} - {self.get_acao_display()} - {self.criado_em:%d/%m/%Y %H:%M}"

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

    @staticmethod
    def _normalizar_decimal_historico(valor):
        if valor is None:
            return None
        return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def registar_historico(cls, configuracao, acao, utilizador=None, observacoes=None):
        if not configuracao:
            raise ValueError("A configuração é obrigatória para registar histórico.")

        return cls.objects.create(
            configuracao=configuracao,
            empregado=configuracao.empregado,
            furo=configuracao.furo,
            empresa_id=getattr(configuracao, "empresa_id", None),
            acao=acao,
            comprimento_tubo=cls._normalizar_decimal_historico(configuracao.comprimento_tubo),
            comprimento_karoutier=cls._normalizar_decimal_historico(configuracao.comprimento_karoutier),
            quantidade_karoutier=getattr(configuracao, "quantidade_karoutier", 1),
            comprimento_acrescento=cls._normalizar_decimal_historico(configuracao.comprimento_acrescento),
            quantidade_acrescento=getattr(configuracao, "quantidade_acrescento", 1),
            comprimento_calibrador=cls._normalizar_decimal_historico(configuracao.comprimento_calibrador),
            quantidade_calibrador=getattr(configuracao, "quantidade_calibrador", 1),
            comprimento_record=cls._normalizar_decimal_historico(configuracao.comprimento_record),
            quantidade_record=getattr(configuracao, "quantidade_record", 1),
            comprimento_bit=cls._normalizar_decimal_historico(configuracao.comprimento_bit),
            comprimento_caixa_mola=cls._normalizar_decimal_historico(configuracao.comprimento_caixa_mola),
            comprimento_tubo_interior=cls._normalizar_decimal_historico(configuracao.comprimento_tubo_interior),
            quantidade_tubo_interior=getattr(configuracao, "quantidade_tubo_interior", 1),
            comprimento_acrescento_tubo_interior=cls._normalizar_decimal_historico(configuracao.comprimento_acrescento_tubo_interior),
            quantidade_acrescento_tubo_interior=getattr(configuracao, "quantidade_acrescento_tubo_interior", 1),
            comprimento_cabeca_interior=cls._normalizar_decimal_historico(configuracao.comprimento_cabeca_interior),
            alterado_por=utilizador,
            observacoes=observacoes,
        )
    
    def clean(self):
        super().clean()

        if self.empregado and not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.configuracao and getattr(self.configuracao, "empresa_id", None):
            if self.empresa_id and self.empresa_id != self.configuracao.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do histórico deve ser a mesma da configuração."
                })

        if self.empregado and self.empresa_id and self.empregado.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa do histórico deve ser a mesma do empregado."
            })

        if self.furo and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "empresa": "A empresa do histórico deve ser a mesma do furo."
            })

        if self.configuracao and self.empregado_id and self.configuracao.empregado_id != self.empregado_id:
            raise ValidationError({
                "empregado": "O empregado do histórico deve ser o mesmo da configuração."
            })

        if self.configuracao and self.furo_id and self.configuracao.furo_id != self.furo_id:
            raise ValidationError({
                "furo": "O furo do histórico deve ser o mesmo da configuração."
            })
        

    def save(self, *args, **kwargs):
        if self.configuracao and getattr(self.configuracao, "empresa_id", None):
            self.empresa_id = self.configuracao.empresa_id
        elif self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
