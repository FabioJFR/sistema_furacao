import uuid
from django.core.exceptions import ValidationError
from django.db import models
from .projeto import Projeto
from .furo import Furo


# ------------------------
# Maquina
# ------------------------
class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operacional', 'Operacional'),
        ('avariada', 'Avariada'),
        ('reparacao', 'Reparação'),
        ('sucata', 'Sucata'),
        ('parada', 'Parada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # TODO multiempresa:
    # - avaliar se estas relações devem evoluir para modelos intermédios com histórico
    # - validar atribuições por projeto/furo via form/service para evitar ligações indevidas
    # - guardar histórico de alocação da máquina
    projetos = models.ManyToManyField(
        Projeto,
        blank=True,
        related_name='maquinas'
    )
    projeto_atual = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maquinas_atuais'
    )

    furos = models.ManyToManyField(
        Furo,
        blank=True,
        related_name='maquinas'
    )

    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, blank=True)

    data_compra = models.DateField(null=True, blank=True)
    data_registo = models.DateField(null=True, blank=True)
    data_revisao = models.DateField(null=True, blank=True)
    # TODO futuro:
    # - tornar empresa obrigatória após migração total dos dados
    # - suportar auditoria de alterações operacionais e manutenção
    # - separar documentação/seguros/licenças em módulo próprio se crescer muito
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="maquinas"
    )
    matricula = models.CharField(max_length=20, null=True, blank=True)
    seguro = models.CharField(max_length=200, blank=True)
    data_seguro = models.DateField(null=True, blank=True)
    data_iuc = models.DateField(null=True, blank=True)

    km = models.BigIntegerField(default=0, blank=True)
    horimetro = models.FloatField(default=0.0, blank=True)
    ano_registo = models.IntegerField(null=True, blank=True)
    valor = models.FloatField(default=0.0, blank=True)

    localizacao_atual = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='operacional'
    )

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()

        if not self.empresa_id:
            raise ValidationError({
                "empresa": "A máquina deve estar associada a uma empresa."
            })

        if self.projeto_atual and not self.projeto_atual.empresa_id:
            raise ValidationError({
                "projeto_atual": "O projeto atual deve estar associado a uma empresa."
            })

        if self.projeto_atual and self.projeto_atual.empresa_id != self.empresa_id:
            raise ValidationError({
                "projeto_atual": "O projeto atual deve pertencer à mesma empresa da máquina."
            })

        if self.pk and self.empresa_id:
            projetos_outra_empresa = self.projetos.exclude(empresa_id=self.empresa_id)
            if projetos_outra_empresa.exists():
                raise ValidationError({
                    "projetos": "Existem projetos associados que não pertencem à mesma empresa da máquina."
                })

            furos_outra_empresa = self.furos.exclude(empresa_id=self.empresa_id)
            if furos_outra_empresa.exists():
                raise ValidationError({
                    "furos": "Existem furos associados que não pertencem à mesma empresa da máquina."
                })

            projetos_ids = set(self.projetos.values_list("id", flat=True))
            for furo in self.furos.all():
                if furo.projeto_id and projetos_ids and furo.projeto_id not in projetos_ids:
                    raise ValidationError({
                        "furos": "Todos os furos associados devem pertencer aos projetos da máquina."
                    })

        if self.km is not None and self.km < 0:
            raise ValidationError({
                "km": "Os quilómetros não podem ser negativos."
            })

        if self.horimetro is not None and self.horimetro < 0:
            raise ValidationError({
                "horimetro": "O horímetro não pode ser negativo."
            })

        if self.valor is not None and self.valor < 0:
            raise ValidationError({
                "valor": "O valor não pode ser negativo."
            })

        if self.ano_registo is not None and self.ano_registo < 1900:
            raise ValidationError({
                "ano_registo": "Ano inválido."
            })

        if self.data_compra and self.data_registo and self.data_registo < self.data_compra:
            raise ValidationError({
                "data_registo": "A data de registo não pode ser anterior à data de compra."
            })

        if self.data_compra and self.data_revisao and self.data_revisao < self.data_compra:
            raise ValidationError({
                "data_revisao": "A data de revisão não pode ser anterior à data de compra."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
