from django.core.exceptions import ValidationError
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
    # TODO futuro:
    # - avaliar histórico detalhado de entradas/saídas do furo
    # - guardar motivo da saída/transferência do empregado
    # - auditar quem criou/alterou a ligação
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ligacoes_furos"
    )

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
        # TODO futuro:
        # - avaliar se unique_together deve passar a incluir data_inicio em cenários com histórico completo
        verbose_name = "Empregado no Furo"
        verbose_name_plural = "Empregados nos Furos"
        ordering = ["-ativo", "empregado__nome"]
        unique_together = ("empregado", "furo")

    def clean(self):
        super().clean()

        # TODO futuro:
        # - impedir sobreposição de períodos ativos do mesmo empregado em múltiplos furos, se essa regra passar a ser obrigatória
        # - validar limites adicionais de datas conforme regras operacionais do projeto

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
                        "furo": "O empregado e o furo têm de pertencer à mesma empresa."
                    })

        if self.empresa_id:
            if self.empregado and self.empregado.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da ligação deve ser a mesma do empregado."
                })

            if self.furo and self.furo.empresa_id and self.empresa_id != self.furo.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da ligação deve ser a mesma do furo."
                })

        if self.furo and self.empregado:
            qs = EmpregadoFuro.objects.filter(
                empregado=self.empregado,
                furo=self.furo,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    "empregado": "Este empregado já está associado a este furo."
                })

        # Regra operacional:
        # Furo concluído não aceita novas associações de trabalhadores.
        # Em edição, permite manter a ligação já existente ao mesmo furo.
        if self.furo and self.furo.estado == "concluido":
            if not self.pk:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos trabalhadores."
                })
            original = EmpregadoFuro.objects.filter(pk=self.pk).only("furo_id").first()
            if original and original.furo_id != self.furo_id:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos trabalhadores."
                })

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({
                "data_fim": "A data de fim não pode ser anterior à data de início."
            })

        if self.ativo and self.data_fim:
            raise ValidationError({
                "ativo": "Se a ligação está ativa, a data de fim deve ficar vazia."
            })

    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        nome_empregado = self.empregado.nome if self.empregado_id and self.empregado else "-"
        nome_furo = self.furo.nome if self.furo_id and self.furo else "-"
        return f"{nome_empregado} - {nome_furo} ({self.get_funcao_display()})"
