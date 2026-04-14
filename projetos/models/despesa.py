import uuid
from django.db import models


###############################
##### DESPESAS ###########
####################
class Despesa(models.Model):
    TIPO_CHOICES = [
        ('maquina', 'Máquina'),
        ('projeto', 'Projeto'),
        ('furo', 'Furo'),
        ('geral', 'Geral'),
    ]
    CATEGORIA_CHOICES = [
        ('combustivel', 'Combustível'),
        ('manutencao', 'Manutenção'),
        ('pecas', 'Peças'),
        ('salarios', 'Salários'),
        ('outros', 'Outros'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    maquina = models.ForeignKey(
        'Maquina',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    projeto = models.ForeignKey(
        'Projeto',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    furo = models.ForeignKey(
        'Furo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='despesas'
    )

    descricao = models.CharField(max_length=255)
    valor = models.FloatField(default=0.0)

    data = models.DateField()
    observacoes = models.TextField(blank=True)

    comprovativo = models.FileField(
        upload_to='despesas/comprovativos/',
        null=True,
        blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descricao} - {self.valor}€"
    
    def clean(self):
        ligados = [self.maquina, self.projeto, self.furo]
        preenchidos = [x for x in ligados if x]

        if len(preenchidos) > 1:
            raise ValidationError("A despesa deve estar associada a apenas um: máquina, projeto ou furo.")

        if len(preenchidos) == 0:
            raise ValidationError("A despesa deve estar associada a pelo menos um elemento.")