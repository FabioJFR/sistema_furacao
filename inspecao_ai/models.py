import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AnaliseImagemAI(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ("caixa_cilindrica", "Caixa cilíndrica com testemunho"),
        ("relatorio_trabalhador", "Relatório manuscrito de trabalhador"),
    ]

    ESTADO_CHOICES = [
        ("pendente", "Pendente"),
        ("concluida", "Concluída"),
        ("revisao_manual", "Revisão manual"),
        ("erro", "Erro"),
    ]

    COR_MARCADOR_CHOICES = [
        ("azul", "Azul"),
        ("preto", "Preto"),
        ("misto", "Misto"),
        ("indefinido", "Indefinido"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="analises_imagem_ai",
    )
    projeto = models.ForeignKey(
        "projetos.Projeto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analises_imagem_ai",
    )
    furo = models.ForeignKey(
        "projetos.Furo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analises_imagem_ai",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analises_imagem_ai_criadas",
    )
    nome = models.CharField(max_length=180)
    tipo_documento = models.CharField(
        max_length=40,
        choices=TIPO_DOCUMENTO_CHOICES,
        default="caixa_cilindrica",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="pendente",
    )
    guardada = models.BooleanField(default=False)
    imagem_original = models.ImageField(upload_to="inspecao_ai/originais/")
    imagem_processada = models.ImageField(
        upload_to="inspecao_ai/processadas/",
        null=True,
        blank=True,
    )
    marcador_predominante = models.CharField(
        max_length=20,
        choices=COR_MARCADOR_CHOICES,
        default="indefinido",
    )
    texto_detectado = models.BooleanField(default=False)
    texto_extraido_bruto = models.TextField(blank=True)
    texto_normalizado = models.TextField(blank=True)
    campos_extraidos = models.JSONField(default=dict, blank=True)
    confianca_media = models.FloatField(null=True, blank=True)
    motor_analise = models.CharField(max_length=80, default="local_vision_v1")
    metadados = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField(blank=True)
    erro_analise = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Análise de imagem AI"
        verbose_name_plural = "Análises de imagem AI"

    def __str__(self):
        return self.nome or f"Análise {self.pk}"

    def clean(self):
        super().clean()

        if self.projeto and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError(
                {"projeto": "O projeto selecionado não pertence à empresa atual."}
            )

        if self.furo:
            if self.furo.empresa_id != self.empresa_id:
                raise ValidationError(
                    {"furo": "O furo selecionado não pertence à empresa atual."}
                )
            if self.projeto_id and self.furo.projeto_id != self.projeto_id:
                raise ValidationError(
                    {"furo": "O furo selecionado não pertence ao projeto indicado."}
                )

    def save(self, *args, **kwargs):
        if self.furo and not self.projeto_id:
            self.projeto = self.furo.projeto
        self.full_clean()
        super().save(*args, **kwargs)


class DeteccaoImagemAI(models.Model):
    TIPO_DETECCAO_CHOICES = [
        ("texto_marcador", "Texto a marcador"),
        ("zona_interesse", "Zona de interesse"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analise = models.ForeignKey(
        AnaliseImagemAI,
        on_delete=models.CASCADE,
        related_name="deteccoes",
    )
    ordem = models.PositiveIntegerField(default=1)
    tipo_deteccao = models.CharField(
        max_length=30,
        choices=TIPO_DETECCAO_CHOICES,
        default="texto_marcador",
    )
    marcador_cor = models.CharField(
        max_length=20,
        choices=AnaliseImagemAI.COR_MARCADOR_CHOICES,
        default="indefinido",
    )
    confianca = models.FloatField(null=True, blank=True)
    texto_sugerido = models.TextField(blank=True)
    caixa_delimitadora = models.JSONField(default=dict, blank=True)
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordem", "criado_em"]
        verbose_name = "Deteção de imagem AI"
        verbose_name_plural = "Deteções de imagem AI"

    def __str__(self):
        return f"{self.analise.nome} - deteção {self.ordem}"


class AnaliseZonaPresetAI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="analise_zona_presets_ai",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analise_zona_presets_ai_criados",
    )
    nome = models.CharField(max_length=120)
    tipo_documento = models.CharField(
        max_length=40,
        choices=AnaliseImagemAI.TIPO_DOCUMENTO_CHOICES,
        default="relatorio_trabalhador",
    )
    zona_relatorio = models.JSONField(default=dict, blank=True)
    zonas_texto = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "-atualizado_em"]
        verbose_name = "Preset de zonas AI"
        verbose_name_plural = "Presets de zonas AI"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento", "nome"],
                name="unique_preset_zonas_ai_empresa_tipo_nome",
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_documento_display()})"


class MemoriaTrabalhoAI(models.Model):
    ESTADO_CHOICES = [
        ("ativo", "Ativo"),
        ("standby", "Standby"),
        ("concluido", "Concluído"),
    ]

    AREA_CHOICES = [
        ("ocr_relatorios", "OCR relatórios"),
        ("ocr_caixas", "OCR caixas"),
        ("chatbox", "Chatbox"),
        ("memoria_operacional", "Memória operacional"),
        ("plataforma", "Plataforma"),
        ("geral", "Geral"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="memorias_trabalho_ai",
        null=True,
        blank=True,
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memorias_trabalho_ai_criadas",
    )
    titulo = models.CharField(max_length=180)
    area = models.CharField(max_length=40, choices=AREA_CHOICES, default="geral")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="ativo")
    resumo = models.TextField()
    detalhes = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em", "-criado_em"]
        verbose_name = "Memória de trabalho AI"
        verbose_name_plural = "Memórias de trabalho AI"

    def __str__(self):
        return self.titulo


class ChatSessaoAI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        related_name="chat_sessoes_ai",
    )
    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessoes_ai",
    )
    titulo = models.CharField(max_length=180, default="Nova conversa AI")
    ativa = models.BooleanField(default=True)
    ultimo_resumo_contexto = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em", "-criado_em"]
        verbose_name = "Sessão Chat AI"
        verbose_name_plural = "Sessões Chat AI"

    def __str__(self):
        return self.titulo or f"Chat {self.pk}"


class ChatMensagemAI(models.Model):
    PAPEL_CHOICES = [
        ("user", "Utilizador"),
        ("assistant", "Assistente"),
        ("system", "Sistema"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sessao = models.ForeignKey(
        ChatSessaoAI,
        on_delete=models.CASCADE,
        related_name="mensagens",
    )
    papel = models.CharField(max_length=20, choices=PAPEL_CHOICES)
    conteudo = models.TextField()
    metadados = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "Mensagem Chat AI"
        verbose_name_plural = "Mensagens Chat AI"

    def __str__(self):
        return f"{self.sessao} - {self.papel}"
