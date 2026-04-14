import uuid
from django.db import models
from .furo import Furo
#  Utilizador: empregadoteste2 | Palavra-passe temporária: suNKEyftyN
# Utilizador: empregadoteste21 | Palavra-passe temporária: YZv3bAnth6

# ------------------------
# Medição
# ------------------------
class Medicao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    furo = models.ForeignKey(
        Furo,
        on_delete=models.CASCADE,
        related_name="medicoes"
    )

    # ------------------------
    # REGISTO VISUAL / AMOSTRA
    # ------------------------
    imagem = models.ImageField(upload_to="rochas/", blank=True, null=True)

    # ------------------------
    # POSIÇÃO DA MEDIÇÃO
    # ------------------------
    profundidade_medida = models.FloatField(blank=True, null=True)

    # ------------------------
    # VALORES REAIS MEDIDOS
    # ------------------------
    inclinacao_real_medida = models.FloatField(blank=True, null=True)
    azimute_real_medido = models.FloatField(blank=True, null=True)

    # ------------------------
    # SNAPSHOT DO PLANEAMENTO NO MOMENTO DA MEDIÇÃO
    # ------------------------
    profundidade_alvo_inicial_furo = models.FloatField(blank=True, null=True)
    profundidade_alvo_atual_furo = models.FloatField(blank=True, null=True)

    inclinacao_planeada_inicial_furo = models.FloatField(blank=True, null=True)
    inclinacao_planeada_atual_furo = models.FloatField(blank=True, null=True)

    azimute_planeado_inicial_furo = models.FloatField(blank=True, null=True)
    azimute_planeado_atual_furo = models.FloatField(blank=True, null=True)

    # ------------------------
    # GEOLOGIA / OBSERVAÇÃO
    # ------------------------
    tipo_rocha = models.CharField(max_length=100, blank=True)
    cor = models.CharField(max_length=20, default="gray")
    dureza = models.FloatField(default=0)
    observacoes = models.TextField(blank=True)

    # ------------------------
    # OUTROS DADOS TÉCNICOS
    # ------------------------
    magnetismo = models.FloatField(blank=True, null=True)
    altitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # ------------------------
    # APOIO / HISTÓRICO
    # ------------------------
    nome_furo_snapshot = models.CharField(max_length=100, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em", "-profundidade_medida"]
        verbose_name = "Medição"
        verbose_name_plural = "Medições"

    def __str__(self):
        profundidade = self.profundidade_medida if self.profundidade_medida is not None else "-"
        return f"{self.furo.nome} - {profundidade} m"

    def save(self, *args, **kwargs):
        # Snapshot automático do nome do furo
        if self.furo and not self.nome_furo_snapshot:
            self.nome_furo_snapshot = self.furo.nome

        # Snapshot automático do planeamento do furo no momento da medição
        if self.furo:
            self.profundidade_alvo_inicial_furo = self.furo.profundidade_alvo_inicial
            self.profundidade_alvo_atual_furo = self.furo.profundidade_alvo_atual

            self.inclinacao_planeada_inicial_furo = self.furo.inclinacao_planeada_inicial
            self.inclinacao_planeada_atual_furo = self.furo.inclinacao_planeada_atual

            self.azimute_planeado_inicial_furo = self.furo.azimute_planeado_inicial
            self.azimute_planeado_atual_furo = self.furo.azimute_planeado_atual

        super().save(*args, **kwargs)