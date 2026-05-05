import uuid
from datetime import time

from django.db import models
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
    ultimo_envio_em = models.DateTimeField(null=True, blank=True)
    proximo_envio_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agendamento de relatório executivo"
        verbose_name_plural = "Agendamentos de relatório executivo"
