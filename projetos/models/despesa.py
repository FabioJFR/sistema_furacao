import uuid
from django.core.exceptions import ValidationError
from django.db import models


###############################
##### DESPESAS ###########
###############################
class Despesa(models.Model):
    TIPO_CHOICES = [
        ("maquina", "Máquina"),
        ("projeto", "Projeto"),
        ("furo", "Furo"),
        ("geral", "Geral"),
        ("combustivel", "Combustível"),
        ("manutencao", "Manutenção"),
        ("pecas", "Peças"),
        ("alimentacao", "Alimentação"),
        ("alojamento", "Alojamento"),
        ("transporte", "Transporte"),
        ("ferramentas", "Ferramentas"),
        ("servicos", "Serviços"),
        ("salarios", "Salários"),
        ("outro", "Outro"),
        ("bit BQ", "bit BQ"),
        ("bit NQ", "bit NQ"),
        ("bit HQ", "bit HQ"),
        ("bit PQ", "bit PQ"),
        ("bit", "bit"),
        ("tubos BQ", "tubos BQ"),
        ("tubos NQ", "tubos NQ"),
        ("tubos HQ", "tubos HQ"),
        ("tubos PQ", "tubos PQ"),
        ("tubos", "tubos"),
        ("anel centralizador BQ", "anel centralizador BQ"),
        ("anel centralizador NQ", "anel centralizador NQ"),
        ("anel centralizador HQ", "anel centralizador HQ"),
        ("anel centralizador PQ", "anel centralizador PQ"),
        ("anel centralizador", "anel centralizador"),
        ("anel batente BQ", "anel batente BQ"),
        ("anel batente NQ", "anel batente NQ"),
        ("anel batente HQ", "anel batente HQ"),
        ("anel batente PQ", "anel batente PQ"),
        ("anel batente", "anel batente"),
        ("calibradores BQ", "calibradores BQ"),
        ("calibradores NQ", "calibradores NQ"),
        ("calibradores HQ", "calibradores HQ"),
        ("calibradores PQ", "calibradores PQ"),
        ("calibradores", "calibradores"),
        ("karoutier", "karoutier"),
        ("karoutier BQ", "karoutier BQ"),
        ("karoutier NQ", "karoutier NQ"),
        ("karoutier HQ", "karoutier HQ"),
        ("karoutier PQ", "karoutier PQ"),
        ("caixa molas", "caixa molas"),
        ("caixa molas BQ", "caixa molas BQ"),
        ("caixa molas NQ", "caixa molas NQ"),
        ("caixa molas HQ", "caixa molas HQ"),
        ("caixa molas PQ", "caixa molas PQ"),
        ("molas BQ", "molas BQ"),
        ("molas NQ", "molas NQ"),
        ("molas HQ", "molas HQ"),
        ("molas PQ", "molas PQ"),
        ("molas", "molas"),
        ("freio BQ", "freio BQ"),
        ("freio NQ", "freio NQ"),
        ("freio HQ", "freio HQ"),
        ("freio PQ", "freio PQ"),
        ("freio", "freio"),
        ("tubo interior", "tubo interior"),
        ("tubo interior BQ", "tubo interior BQ"),
        ("tubo interior NQ", "tubo interior NQ"),
        ("tubo interior HQ", "tubo interior HQ"),
        ("tubo interior PQ", "tubo interior PQ"),
        ("Polimeros", "Polimeros"),
        ("Massa Lubrificante", "massa lubrificante"),
        ("rolamentos", "rolamentos"),
        ("borrachas expansivas", "borrachas expansivas"),
        ("cabeca de interior", "cabeca de interior"),
        ("cabeca de injecao", "cabeca de injecao"),
        ("Bombas de agua", "bombas de agua"),
        ("bicos de massa", "bicos de massa"),
        ("luvas", "luvas"),
        ("capacete", "capacete"),
        ("oculos protecao", "oculos protecao"),
        ("calcas trabalho", "calcas trabalho"),
        ("blusas trabalho", "blusas trabalho"),
        ("botas protecao", "botas protecao"),
        ("botas protecao galochas", "botas protecao galochas"),
        ("casacos", "casacos"),
        ("agua", "agua"),
        ("energia", "energia"),
    ]

    CATEGORIA_CHOICES = [
        ("combustivel", "Combustível"),
        ("manutencao", "Manutenção"),
        ("pecas", "Peças"),
        ("salarios", "Salários"),
        ("outros", "Outros"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="outros")
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)

    maquina = models.ForeignKey(
        "Maquina",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="despesas",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="despesas",
    )
    projeto = models.ForeignKey(
        "Projeto",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="despesas",
    )
    furo = models.ForeignKey(
        "Furo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="despesas",
    )

    descricao = models.CharField(max_length=255)
    valor = models.FloatField(default=0.0)

    data = models.DateField()
    observacoes = models.TextField(blank=True)

    # TODO futuro:
    # - guardar centro de custo / conta analítica
    # - suportar aprovação da despesa
    # - guardar auditoria de criação/edição
    comprovativo = models.FileField(
        upload_to="despesas/comprovativos/",
        null=True,
        blank=True,
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        # TODO futuro:
        # - índices por empresa/data/tipo
        # - soft delete / fecho contabilístico
        ordering = ["-data", "-criado_em"]
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"

    def __str__(self):
        descricao = self.descricao or "Despesa"
        return f"{descricao} - {self.valor}€"

    def clean(self):
        super().clean()

        # TODO futuro:
        # - validar regras contabilísticas por tipo
        # - validar documentos obrigatórios por categoria

        ligados = [self.maquina, self.projeto, self.furo]
        preenchidos = [x for x in ligados if x]

        if len(preenchidos) > 1:
            raise ValidationError({
                "tipo": "A despesa deve estar associada a apenas um: máquina, projeto ou furo."
            })

        if self.tipo == "maquina" and not self.maquina:
            raise ValidationError({
                "maquina": "Seleciona a máquina a que esta despesa está associada."
            })

        if self.tipo == "projeto" and not self.projeto:
            raise ValidationError({
                "projeto": "Seleciona o projeto a que esta despesa está associada."
            })

        if self.tipo == "furo" and not self.furo:
            raise ValidationError({
                "furo": "Seleciona o furo a que esta despesa está associada."
            })

        if self.tipo == "maquina" and (self.projeto or self.furo):
            raise ValidationError({
                "tipo": "Uma despesa do tipo máquina só deve estar ligada à máquina selecionada."
            })

        if self.tipo == "projeto" and (self.maquina or self.furo):
            raise ValidationError({
                "tipo": "Uma despesa do tipo projeto só deve estar ligada ao projeto selecionado."
            })

        if self.tipo == "furo" and (self.maquina or self.projeto):
            raise ValidationError({
                "tipo": "Uma despesa do tipo furo só deve estar ligada ao furo selecionado."
            })

        if self.valor is not None and self.valor < 0:
            raise ValidationError({
                "valor": "O valor da despesa não pode ser negativo."
            })

        if self.maquina and not self.maquina.empresa_id:
            raise ValidationError({
                "maquina": "A máquina deve estar associada a uma empresa."
            })

        if self.projeto and not self.projeto.empresa_id:
            raise ValidationError({
                "projeto": "O projeto deve estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.maquina and self.projeto and self.maquina.projeto_atual_id:
            if self.maquina.projeto_atual_id != self.projeto.id:
                raise ValidationError({
                    "projeto": "O projeto da despesa deve ser o mesmo do projeto atual da máquina."
                })

        if self.empresa_id:
            if self.maquina and self.maquina.empresa_id != self.empresa_id:
                raise ValidationError({
                    "empresa": "A máquina deve pertencer à mesma empresa da despesa."
                })

            if self.projeto and self.projeto.empresa_id != self.empresa_id:
                raise ValidationError({
                    "empresa": "O projeto deve pertencer à mesma empresa da despesa."
                })

            if self.furo and self.furo.empresa_id != self.empresa_id:
                raise ValidationError({
                    "empresa": "O furo deve pertencer à mesma empresa da despesa."
                })

        if self.maquina and self.furo:
            furos_maquina = self.maquina.furos.filter(pk=self.furo.pk)
            if self.maquina.pk and self.maquina.furos.exists() and not furos_maquina.exists():
                raise ValidationError({
                    "furo": "O furo da despesa deve estar associado à máquina selecionada."
                })

        if self.furo and self.projeto and self.furo.projeto_id != self.projeto.id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence ao projeto escolhido."
            })

    def save(self, *args, **kwargs):
        if self.projeto and self.projeto.empresa_id:
            self.empresa_id = self.projeto.empresa_id
        elif self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id
        elif self.maquina and self.maquina.empresa_id:
            self.empresa_id = self.maquina.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
