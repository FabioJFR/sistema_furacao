import uuid
from django.db import models
from .projeto import Projeto


# ------------------------
# Furo
# ------------------------
class Furo(models.Model):
    TIPO_CHOICES = [
        ("fundo", "Fundo"),
        ("superficie", "Superfície"),
    ]

    ESTADO_CHOICES = [
        ("ativo", "Ativo"),
        ("parado", "Parado"),
        ("concluido", "Concluído"),
        ("pausado", "Pausado"),
    ]

    SISTEMA_COORDENADAS_CHOICES = [
        ("local", "Local"),
        ("utm", "UTM"),
        ("wgs84", "WGS84"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="furos"
    )

    nome = models.CharField(max_length=200, default="Furo")

    # ------------------------
    # PROFUNDIDADES
    # ------------------------
    # Referência inicial do planeamento do furo
    profundidade_inicial = models.FloatField(default=0.0)

    # Alvo planeado inicial (não deve ser alterado automaticamente)
    profundidade_alvo_inicial = models.FloatField(default=0.0)

    # Alvo planeado atual (pode ser revisto manualmente no futuro)
    profundidade_alvo_atual = models.FloatField(default=0.0)

    # Profundidade real atual do furo
    profundidade_atual = models.FloatField(default=0.0)

    # Maior profundidade real já atingida
    profundidade_maxima_atingida = models.FloatField(default=0.0)

    # ------------------------
    # ORIENTAÇÃO PLANEADA
    # ------------------------
    # Valores definidos no início do furo e preservados como referência
    inclinacao_planeada_inicial = models.FloatField(default=0.0)
    azimute_planeado_inicial = models.FloatField(default=0.0)

    # Valores planeados atuais, caso o plano seja revisto
    inclinacao_planeada_atual = models.FloatField(null=True, blank=True)
    azimute_planeado_atual = models.FloatField(null=True, blank=True)

    # ------------------------
    # ORIENTAÇÃO REAL
    # ------------------------
    # Valores reais medidos mais recentes
    inclinacao_real_atual = models.FloatField(null=True, blank=True)
    azimute_real_atual = models.FloatField(null=True, blank=True)

    magnetismo = models.FloatField(default=0.0)

    # ------------------------
    # LOCALIZAÇÃO
    # ------------------------
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    altitude = models.FloatField(null=True, blank=True)

    localizacao = models.CharField(max_length=200, blank=True)
    local_sondagem = models.CharField(max_length=200, blank=True)

    sistema_coordenadas = models.CharField(
        max_length=50,
        choices=SISTEMA_COORDENADAS_CHOICES,
        default="local"
    )

    origem_este = models.FloatField(default=0.0)
    origem_norte = models.FloatField(default=0.0)
    origem_tvd = models.FloatField(default=0.0)

    # ------------------------
    # ESTADO E CLASSIFICAÇÃO
    # ------------------------
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="fundo")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="ativo")

    # ------------------------
    # PRODUÇÃO / RESUMO
    # ------------------------
    metros_furados = models.FloatField(default=0.0)
    total_horas = models.DurationField(null=True, blank=True)

    # ------------------------
    # INFORMAÇÃO EXTRA
    # ------------------------
    detalhes = models.TextField(blank=True)

    # JSONs temporários / auxiliares
    medicoes_json = models.JSONField(default=list, blank=True)
    relatorios = models.JSONField(default=list, blank=True)
    imagens = models.JSONField(default=list, blank=True)
    planeamento = models.JSONField(default=list, blank=True)
    ficheiros = models.JSONField(default=list, blank=True)
    trabalhadores = models.JSONField(default=list, blank=True)
    metros_furados_diario = models.JSONField(default=list, blank=True)

    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "nome"]
        verbose_name = "Furo"
        verbose_name_plural = "Furos"

    def __str__(self):
        return f"{self.nome} - {self.projeto.nome}"

    def save(self, *args, **kwargs):
        # Ao criar o furo, garantir que os valores "atuais planeados"
        # começam iguais aos valores "iniciais planeados", se ainda não tiverem sido definidos.
        if self.inclinacao_planeada_atual is None:
            self.inclinacao_planeada_atual = self.inclinacao_planeada_inicial

        if self.azimute_planeado_atual is None:
            self.azimute_planeado_atual = self.azimute_planeado_inicial

        if self.profundidade_alvo_atual is None:
            self.profundidade_alvo_atual = self.profundidade_alvo_inicial

        super().save(*args, **kwargs)