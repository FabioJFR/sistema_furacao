import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ClienteContrato(models.Model):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("ativo", "Ativo"),
        ("suspenso", "Suspenso"),
        ("terminado", "Terminado"),
    ]

    TIPO_COBRANCA_CHOICES = [
        ("mensal", "Mensal"),
        ("anual", "Anual"),
        ("projeto", "Por projeto"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="clientes_contratos",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_contratos",
    )

    nome_cliente = models.CharField(max_length=200)
    numero_contrato = models.CharField(max_length=120, blank=True)
    contacto_nome = models.CharField(max_length=200, blank=True)
    contacto_email = models.EmailField(blank=True)
    contacto_telefone = models.CharField(max_length=40, blank=True)

    tipo_cobranca = models.CharField(max_length=20, choices=TIPO_COBRANCA_CHOICES, default="mensal")
    valor_contratado = models.FloatField(default=0.0)
    moeda = models.CharField(max_length=8, default="EUR")
    sla_resposta_horas = models.PositiveIntegerField(default=24)

    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ativo")
    notas = models.TextField(blank=True)

    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome_cliente", "-atualizado_em"]
        verbose_name = "Cliente/Contrato"
        verbose_name_plural = "Clientes/Contratos"

    def __str__(self):
        ref = f" ({self.numero_contrato})" if self.numero_contrato else ""
        return f"{self.nome_cliente}{ref}"

    def clean(self):
        super().clean()

        self.nome_cliente = (self.nome_cliente or "").strip()
        self.numero_contrato = (self.numero_contrato or "").strip()
        self.contacto_nome = (self.contacto_nome or "").strip()
        self.moeda = (self.moeda or "EUR").strip().upper()

        if not self.empresa_id:
            raise ValidationError({"empresa": "O contrato deve estar associado a uma empresa."})

        if not self.nome_cliente:
            raise ValidationError({"nome_cliente": "O nome do cliente é obrigatório."})

        if self.valor_contratado is not None and self.valor_contratado < 0:
            raise ValidationError({"valor_contratado": "O valor contratado não pode ser negativo."})

        if self.sla_resposta_horas <= 0:
            raise ValidationError({"sla_resposta_horas": "O SLA deve ser maior que zero."})

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data de fim não pode ser anterior à data de início."})

        if self.projeto_id and self.projeto and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({"projeto": "O projeto selecionado não pertence à mesma empresa."})

        if self.numero_contrato:
            qs = ClienteContrato.objects.filter(
                empresa_id=self.empresa_id,
                numero_contrato__iexact=self.numero_contrato,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"numero_contrato": "Já existe este número de contrato na empresa."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
