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
    comprimento_acrescento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comprimento_calibrador = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comprimento_record = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
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
            comprimento_acrescento=cls._normalizar_decimal_historico(configuracao.comprimento_acrescento),
            comprimento_calibrador=cls._normalizar_decimal_historico(configuracao.comprimento_calibrador),
            comprimento_record=cls._normalizar_decimal_historico(configuracao.comprimento_record),
            comprimento_bit=cls._normalizar_decimal_historico(configuracao.comprimento_bit),
            comprimento_caixa_mola=cls._normalizar_decimal_historico(configuracao.comprimento_caixa_mola),
            comprimento_tubo_interior=cls._normalizar_decimal_historico(configuracao.comprimento_tubo_interior),
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