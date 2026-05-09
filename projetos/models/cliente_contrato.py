import uuid
from calendar import monthrange

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ClienteComercial(models.Model):
    CLASSIFICACAO_CHOICES = [
        ("estrategico", "Estratégico"),
        ("crescimento", "Crescimento"),
        ("estavel", "Estável"),
        ("em_risco", "Em risco"),
        ("inativo", "Inativo"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="clientes_comerciais",
    )
    nome_cliente = models.CharField(max_length=200)
    contacto_principal_nome = models.CharField(max_length=200, blank=True)
    contacto_principal_email = models.EmailField(blank=True)
    contacto_principal_telefone = models.CharField(max_length=40, blank=True)
    contacto_secundario_nome = models.CharField(max_length=200, blank=True)
    contacto_secundario_email = models.EmailField(blank=True)
    contacto_secundario_telefone = models.CharField(max_length=40, blank=True)
    classificacao_comercial = models.CharField(
        max_length=30,
        choices=CLASSIFICACAO_CHOICES,
        default="estavel",
    )
    notas_comerciais = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome_cliente", "-atualizado_em"]
        verbose_name = "Ficha comercial de cliente"
        verbose_name_plural = "Fichas comerciais de clientes"

    def __str__(self):
        return self.nome_cliente

    def clean(self):
        super().clean()
        self.nome_cliente = (self.nome_cliente or "").strip()
        self.contacto_principal_nome = (self.contacto_principal_nome or "").strip()
        self.contacto_principal_telefone = (self.contacto_principal_telefone or "").strip()
        self.contacto_secundario_nome = (self.contacto_secundario_nome or "").strip()
        self.contacto_secundario_telefone = (self.contacto_secundario_telefone or "").strip()
        self.notas_comerciais = (self.notas_comerciais or "").strip()

        if not self.empresa_id:
            raise ValidationError({"empresa": "A ficha comercial deve estar associada a uma empresa."})
        if not self.nome_cliente:
            raise ValidationError({"nome_cliente": "O nome do cliente é obrigatório."})

        qs = ClienteComercial.objects.filter(
            empresa_id=self.empresa_id,
            nome_cliente__iexact=self.nome_cliente,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"nome_cliente": "Já existe uma ficha comercial para este cliente na empresa."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
    WORKFLOW_COMERCIAL_CHOICES = [
        ("estavel", "Estável"),
        ("em_negociacao", "Em negociação"),
        ("renovacao_pendente", "Renovação pendente"),
        ("renovado", "Renovado"),
        ("perdido", "Perdido"),
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
    ultimo_contacto_em = models.DateField(null=True, blank=True)
    proximo_followup_em = models.DateField(null=True, blank=True)
    dias_alerta_sem_contacto = models.PositiveIntegerField(default=30)

    tipo_cobranca = models.CharField(max_length=20, choices=TIPO_COBRANCA_CHOICES, default="mensal")
    valor_contratado = models.FloatField(default=0.0)
    moeda = models.CharField(max_length=8, default="EUR")
    sla_resposta_horas = models.PositiveIntegerField(default=24)

    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    renovacao_automatica = models.BooleanField(default=False)
    periodo_renovacao_meses = models.PositiveIntegerField(default=12)
    dias_alerta_vencimento = models.PositiveIntegerField(default=30)
    workflow_comercial = models.CharField(max_length=30, choices=WORKFLOW_COMERCIAL_CHOICES, default="estavel")
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

        if self.periodo_renovacao_meses <= 0:
            raise ValidationError({"periodo_renovacao_meses": "O período de renovação deve ser maior que zero."})

        if self.dias_alerta_vencimento <= 0:
            raise ValidationError({"dias_alerta_vencimento": "O alerta de vencimento deve ser maior que zero."})

        if self.dias_alerta_sem_contacto <= 0:
            raise ValidationError({"dias_alerta_sem_contacto": "O alerta sem contacto deve ser maior que zero."})

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({"data_fim": "A data de fim não pode ser anterior à data de início."})

        if self.ultimo_contacto_em and self.data_inicio and self.ultimo_contacto_em < self.data_inicio:
            raise ValidationError({"ultimo_contacto_em": "O último contacto não pode ser anterior ao início do contrato."})

        if self.proximo_followup_em and self.ultimo_contacto_em and self.proximo_followup_em < self.ultimo_contacto_em:
            raise ValidationError({"proximo_followup_em": "O próximo follow-up não pode ser anterior ao último contacto."})

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


class ClienteContratoWorkflowHistorico(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="clientes_contratos_workflow_historico",
    )
    contrato = models.ForeignKey(
        ClienteContrato,
        on_delete=models.CASCADE,
        related_name="historico_workflow",
    )
    workflow_anterior = models.CharField(max_length=30, blank=True, default="")
    workflow_novo = models.CharField(max_length=30, choices=ClienteContrato.WORKFLOW_COMERCIAL_CHOICES)
    observacao = models.TextField(blank=True)
    alterado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_contratos_workflow_alterados",
    )
    criado_em = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Histórico de workflow do contrato"
        verbose_name_plural = "Histórico de workflow dos contratos"

    def __str__(self):
        return f"{self.contrato} | {self.get_workflow_novo_label()}"

    @staticmethod
    def _resolver_label_workflow(valor):
        mapa = dict(ClienteContrato.WORKFLOW_COMERCIAL_CHOICES)
        if not valor:
            return "Estado inicial"
        return mapa.get(valor, valor)

    def get_workflow_anterior_label(self):
        return self._resolver_label_workflow(self.workflow_anterior)

    def get_workflow_novo_label(self):
        return self._resolver_label_workflow(self.workflow_novo)

    def clean(self):
        super().clean()
        self.observacao = (self.observacao or "").strip()
        if not self.contrato_id:
            raise ValidationError({"contrato": "O histórico deve estar associado a um contrato."})
        if self.empresa_id and self.contrato_id and self.empresa_id != self.contrato.empresa_id:
            raise ValidationError({"empresa": "A empresa do histórico tem de coincidir com a empresa do contrato."})

    def save(self, *args, **kwargs):
        if self.contrato_id:
            self.empresa = self.contrato.empresa
        self.full_clean()
        super().save(*args, **kwargs)


class ClienteContratoAnexo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="clientes_contratos_anexos",
    )
    contrato = models.ForeignKey(
        ClienteContrato,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    titulo = models.CharField(max_length=220)
    ficheiro = models.FileField(upload_to="gestao/clientes_contratos/anexos/")
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Anexo de contrato"
        verbose_name_plural = "Anexos de contrato"

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        self.titulo = (self.titulo or "").strip()
        if not self.contrato_id:
            raise ValidationError({"contrato": "O anexo deve estar associado a um contrato."})
        if not self.titulo:
            raise ValidationError({"titulo": "O título do anexo é obrigatório."})
        if self.empresa_id and self.contrato_id and self.empresa_id != self.contrato.empresa_id:
            raise ValidationError({"empresa": "A empresa do anexo tem de coincidir com a empresa do contrato."})

    def save(self, *args, **kwargs):
        if self.contrato_id:
            self.empresa = self.contrato.empresa
        self.full_clean()
        super().save(*args, **kwargs)


class ClienteContratoAdenda(models.Model):
    ORIGEM_CHOICES = [
        ("manual", "Manual"),
        ("renovacao_automatica", "Renovação automática"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="clientes_contratos_adendas",
    )
    contrato = models.ForeignKey(
        ClienteContrato,
        on_delete=models.CASCADE,
        related_name="adendas",
    )
    titulo = models.CharField(max_length=220)
    descricao = models.TextField(blank=True)
    data_adenda = models.DateField(default=timezone.localdate)
    data_fim_anterior = models.DateField(null=True, blank=True)
    valor_adicional = models.FloatField(default=0.0)
    nova_data_fim = models.DateField(null=True, blank=True)
    origem = models.CharField(max_length=30, choices=ORIGEM_CHOICES, default="manual")
    ficheiro = models.FileField(upload_to="gestao/clientes_contratos/adendas/", blank=True, null=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_adenda", "-criado_em"]
        verbose_name = "Adenda contratual"
        verbose_name_plural = "Adendas contratuais"

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        self.titulo = (self.titulo or "").strip()
        if not self.contrato_id:
            raise ValidationError({"contrato": "A adenda deve estar associada a um contrato."})
        if not self.titulo:
            raise ValidationError({"titulo": "O título da adenda é obrigatório."})
        if self.empresa_id and self.contrato_id and self.empresa_id != self.contrato.empresa_id:
            raise ValidationError({"empresa": "A empresa da adenda tem de coincidir com a empresa do contrato."})
        if self.nova_data_fim and self.contrato.data_inicio and self.nova_data_fim < self.contrato.data_inicio:
            raise ValidationError({"nova_data_fim": "A nova data fim não pode ser anterior ao início do contrato."})
        if self.data_fim_anterior and self.nova_data_fim and self.nova_data_fim < self.data_fim_anterior:
            raise ValidationError({"nova_data_fim": "A nova data fim não pode ser anterior à data fim anterior."})

    def save(self, *args, **kwargs):
        if self.contrato_id:
            self.empresa = self.contrato.empresa
        self.full_clean()
        super().save(*args, **kwargs)


def adicionar_meses_data(data_base, meses):
    ano = data_base.year + ((data_base.month - 1 + meses) // 12)
    mes = ((data_base.month - 1 + meses) % 12) + 1
    dia = min(data_base.day, monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)
