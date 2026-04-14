from django.conf import settings
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

    @classmethod
    def registar_historico(cls, configuracao, acao, utilizador=None, observacoes=None):
        """
        Cria um registo de histórico com snapshot completo da configuração.
        """
        return cls.objects.create(
            configuracao=configuracao,
            empregado=configuracao.empregado,
            furo=configuracao.furo,
            acao=acao,
            comprimento_tubo=configuracao.comprimento_tubo,
            comprimento_karoutier=configuracao.comprimento_karoutier,
            comprimento_acrescento=configuracao.comprimento_acrescento,
            comprimento_calibrador=configuracao.comprimento_calibrador,
            comprimento_record=configuracao.comprimento_record,
            comprimento_bit=configuracao.comprimento_bit,
            comprimento_caixa_mola=configuracao.comprimento_caixa_mola,
            comprimento_tubo_interior=configuracao.comprimento_tubo_interior,
            comprimento_cabeca_interior=configuracao.comprimento_cabeca_interior,
            alterado_por=utilizador,
            observacoes=observacoes,
        )