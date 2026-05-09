import uuid
from datetime import time

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class PedidoCompra(models.Model):
    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]
    ESTADO_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="pedidos_compra")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_compra",
    )
    solicitado_por = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_compra_solicitados",
    )
    descricao = models.CharField(max_length=220)
    categoria = models.CharField(max_length=80, blank=True)
    fornecedor_sugerido = models.CharField(max_length=160, blank=True)
    valor_estimado = models.FloatField(default=0.0)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="media")
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default="pendente")
    data_necessidade = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    aprovado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Pedido de compra"
        verbose_name_plural = "Pedidos de compra"


class FornecedorCompra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="fornecedores_compra")
    nome = models.CharField(max_length=180)
    contacto_nome = models.CharField(max_length=160, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=60, blank=True)
    sla_dias_entrega = models.PositiveIntegerField(default=0)
    avaliacao = models.FloatField(default=0.0)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Fornecedor de compra"
        verbose_name_plural = "Fornecedores de compra"
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nome"], name="uniq_fornecedor_compra_empresa_nome"),
        ]

    def __str__(self):
        return self.nome


class PropostaFornecedorCompra(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(PedidoCompra, on_delete=models.CASCADE, related_name="propostas_fornecedor")
    fornecedor = models.ForeignKey(FornecedorCompra, on_delete=models.CASCADE, related_name="propostas_compra")
    valor_proposto = models.FloatField(default=0.0)
    prazo_entrega_dias = models.PositiveIntegerField(default=0)
    observacoes = models.TextField(blank=True)
    selecionada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["valor_proposto", "prazo_entrega_dias", "-criado_em"]
        verbose_name = "Proposta de fornecedor"
        verbose_name_plural = "Propostas de fornecedor"

    def clean(self):
        if self.fornecedor_id and self.pedido_id and self.fornecedor.empresa_id != self.pedido.empresa_id:
            raise ValidationError("O fornecedor tem de pertencer à mesma empresa do pedido.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class NotificacaoGestao(models.Model):
    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
    ]
    ESTADO_CHOICES = [
        ("aberta", "Aberta"),
        ("em_andamento", "Em andamento"),
        ("resolvida", "Resolvida"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="notificacoes_gestao")
    titulo = models.CharField(max_length=220)
    tipo = models.CharField(max_length=80, blank=True)
    prioridade = models.CharField(max_length=10, choices=PRIORIDADE_CHOICES, default="media")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="aberta")
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes_gestao",
    )
    prazo = models.DateTimeField(null=True, blank=True)
    origem_url = models.CharField(max_length=255, blank=True)
    detalhes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["estado", "-criado_em"]
        verbose_name = "Notificação de gestão"
        verbose_name_plural = "Notificações de gestão"


class ChecklistHSE(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("conforme", "Conforme"),
        ("nao_conforme", "Não conforme"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="checklists_hse")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checklists_hse",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checklists_hse",
    )
    titulo = models.CharField(max_length=220)
    area = models.CharField(max_length=120, blank=True)
    data_check = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_check", "-criado_em"]
        verbose_name = "Checklist HSE"
        verbose_name_plural = "Checklists HSE"


class IncidenteSeguranca(models.Model):
    GRAVIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    ]
    STATUS_CHOICES = [
        ("aberto", "Aberto"),
        ("investigacao", "Em investigação"),
        ("fechado", "Fechado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="incidentes_seguranca")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidentes_seguranca",
    )
    reportado_por = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidentes_reportados",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidentes_responsavel",
    )
    titulo = models.CharField(max_length=220)
    descricao = models.TextField(blank=True)
    gravidade = models.CharField(max_length=20, choices=GRAVIDADE_CHOICES, default="media")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberto")
    data_incidente = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-data_incidente", "-criado_em"]
        verbose_name = "Incidente de segurança"
        verbose_name_plural = "Incidentes de segurança"


class AuditoriaHSE(models.Model):
    STATUS_CHOICES = [
        ("planeada", "Planeada"),
        ("em_curso", "Em curso"),
        ("concluida", "Concluída"),
    ]
    RESULTADO_CHOICES = [
        ("conforme", "Conforme"),
        ("observacao", "Observação"),
        ("nao_conforme", "Não conforme"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="auditorias_hse")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_hse",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_hse",
    )
    titulo = models.CharField(max_length=220)
    area = models.CharField(max_length=120, blank=True)
    data_auditoria = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planeada")
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, default="observacao")
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-data_auditoria", "-criado_em"]
        verbose_name = "Auditoria HSE"
        verbose_name_plural = "Auditorias HSE"


class PlanoAuditoriaHSE(models.Model):
    FREQUENCIA_CHOICES = [
        ("mensal", "Mensal"),
        ("trimestral", "Trimestral"),
        ("semestral", "Semestral"),
        ("anual", "Anual"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="planos_auditoria_hse")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_auditoria_hse",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planos_auditoria_hse",
    )
    titulo = models.CharField(max_length=220)
    area = models.CharField(max_length=120, blank=True)
    frequencia = models.CharField(max_length=20, choices=FREQUENCIA_CHOICES, default="mensal")
    ativo = models.BooleanField(default=True)
    proxima_execucao = models.DateField(default=timezone.localdate)
    ultima_geracao_em = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["proxima_execucao", "titulo"]
        verbose_name = "Plano de auditoria HSE"
        verbose_name_plural = "Planos de auditoria HSE"


class AcaoCorretiva(models.Model):
    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    ]
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("em_andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("cancelada", "Cancelada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="acoes_corretivas")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_corretivas",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_corretivas",
    )
    checklist = models.ForeignKey(
        ChecklistHSE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_corretivas",
    )
    incidente = models.ForeignKey(
        IncidenteSeguranca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_corretivas",
    )
    auditoria = models.ForeignKey(
        AuditoriaHSE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_corretivas",
    )
    titulo = models.CharField(max_length=220)
    descricao = models.TextField(blank=True)
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default="media")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")
    prazo = models.DateField(null=True, blank=True)
    concluida_em = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "prazo", "-criado_em"]
        verbose_name = "Ação corretiva"
        verbose_name_plural = "Ações corretivas"


class AcaoPreventiva(models.Model):
    PRIORIDADE_CHOICES = [
        ("baixa", "Baixa"),
        ("media", "Média"),
        ("alta", "Alta"),
        ("critica", "Crítica"),
    ]
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("em_andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("cancelada", "Cancelada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="acoes_preventivas")
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_preventivas",
    )
    responsavel = models.ForeignKey(
        "projetos.Empregados",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_preventivas",
    )
    checklist = models.ForeignKey(
        ChecklistHSE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_preventivas",
    )
    incidente = models.ForeignKey(
        IncidenteSeguranca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_preventivas",
    )
    auditoria = models.ForeignKey(
        AuditoriaHSE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_preventivas",
    )
    titulo = models.CharField(max_length=220)
    descricao = models.TextField(blank=True)
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, default="media")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")
    prazo = models.DateField(null=True, blank=True)
    concluida_em = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "prazo", "-criado_em"]
        verbose_name = "Ação preventiva"
        verbose_name_plural = "Ações preventivas"


class EvidenciaCompliance(models.Model):
    TIPO_CHOICES = [
        ("foto", "Foto"),
        ("documento", "Documento"),
        ("relatorio", "Relatório"),
        ("outro", "Outro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="evidencias_compliance")
    checklist = models.ForeignKey(
        ChecklistHSE,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    incidente = models.ForeignKey(
        IncidenteSeguranca,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    auditoria = models.ForeignKey(
        AuditoriaHSE,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    acao_corretiva = models.ForeignKey(
        AcaoCorretiva,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    acao_preventiva = models.ForeignKey(
        AcaoPreventiva,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidencias",
    )
    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evidencias_compliance_criadas",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="documento")
    titulo = models.CharField(max_length=180, blank=True)
    ficheiro = models.FileField(upload_to="gestao/compliance/evidencias/")
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Evidência de compliance"
        verbose_name_plural = "Evidências de compliance"

    @property
    def origem_obj(self):
        return self.checklist or self.incidente or self.auditoria or self.acao_corretiva or self.acao_preventiva

    @property
    def origem_label(self):
        if self.checklist_id:
            return "Checklist HSE"
        if self.incidente_id:
            return "Incidente"
        if self.auditoria_id:
            return "Auditoria HSE"
        if self.acao_corretiva_id:
            return "Ação corretiva"
        if self.acao_preventiva_id:
            return "Ação preventiva"
        return "Compliance"

    def clean(self):
        super().clean()
        origens = [self.checklist, self.incidente, self.auditoria, self.acao_corretiva, self.acao_preventiva]
        preenchidas = [origem for origem in origens if origem]
        if len(preenchidas) != 1:
            raise ValidationError("A evidência deve estar associada a uma única origem de compliance.")

        origem = preenchidas[0]
        origem_empresa_id = getattr(origem, "empresa_id", None)
        if origem_empresa_id and self.empresa_id and origem_empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa da evidência tem de coincidir com a empresa da origem."})

    def save(self, *args, **kwargs):
        origem = self.origem_obj
        if origem and getattr(origem, "empresa_id", None):
            self.empresa_id = origem.empresa_id
        if not self.titulo and origem:
            self.titulo = f"{self.get_tipo_display()} - {self.origem_label}"
        self.full_clean()
        super().save(*args, **kwargs)


class FechoAcaoCorretiva(models.Model):
    acao = models.OneToOneField(
        AcaoCorretiva,
        on_delete=models.CASCADE,
        related_name="fecho_formal",
    )
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="fechos_acoes_corretivas")
    fechado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fechos_acoes_corretivas",
    )
    data_fecho = models.DateField(default=timezone.localdate)
    resumo_execucao = models.TextField()
    eficaz = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_fecho", "-criado_em"]
        verbose_name = "Fecho formal da ação corretiva"
        verbose_name_plural = "Fechos formais das ações corretivas"

    def clean(self):
        super().clean()
        if self.acao and self.empresa_id and self.acao.empresa_id != self.empresa_id:
            raise ValidationError({"empresa": "A empresa do fecho deve coincidir com a empresa da ação corretiva."})

    def save(self, *args, **kwargs):
        if self.acao and self.acao.empresa_id:
            self.empresa_id = self.acao.empresa_id
        self.full_clean()
        super().save(*args, **kwargs)


class AgendamentoRelatorioExecutivo(models.Model):
    FREQUENCIA_CHOICES = [
        ("diario", "Diário"),
        ("semanal", "Semanal"),
        ("mensal", "Mensal"),
    ]

    empresa = models.OneToOneField(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="agendamento_relatorio_executivo",
    )
    ativo = models.BooleanField(default=False)
    frequencia = models.CharField(max_length=20, choices=FREQUENCIA_CHOICES, default="semanal")
    hora_execucao = models.TimeField(default=time(8, 0))
    dia_semana = models.PositiveSmallIntegerField(default=0)  # 0=segunda
    dia_mes = models.PositiveSmallIntegerField(default=1)  # 1..28
    destinos = models.TextField(blank=True, help_text="Emails separados por vírgula/ponto e vírgula.")
    incluir_csv = models.BooleanField(default=True)
    incluir_xlsx = models.BooleanField(default=True)
    incluir_pdf = models.BooleanField(default=False)
    ultimo_envio_em = models.DateTimeField(null=True, blank=True)
    proximo_envio_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agendamento de relatório executivo"
        verbose_name_plural = "Agendamentos de relatório executivo"


class HistoricoEnvioRelatorioExecutivo(models.Model):
    ORIGEM_CHOICES = [
        ("manual", "Manual"),
        ("agendado", "Agendado"),
        ("executar_agora", "Executar agora"),
    ]
    STATUS_CHOICES = [
        ("sucesso", "Sucesso"),
        ("erro", "Erro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("plataforma.Empresa", on_delete=models.CASCADE, related_name="historico_relatorios_executivos")
    agendamento = models.ForeignKey(
        AgendamentoRelatorioExecutivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historico_envios",
    )
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sucesso")
    assunto = models.CharField(max_length=220, blank=True)
    destinos = models.TextField(blank=True)
    incluir_csv = models.BooleanField(default=True)
    incluir_xlsx = models.BooleanField(default=True)
    incluir_pdf = models.BooleanField(default=False)
    enviados = models.PositiveIntegerField(default=0)
    filtros_json = models.JSONField(default=dict, blank=True)
    resumo_json = models.JSONField(default=dict, blank=True)
    erro = models.TextField(blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Histórico de envio de relatório executivo"
        verbose_name_plural = "Histórico de envio de relatórios executivos"
