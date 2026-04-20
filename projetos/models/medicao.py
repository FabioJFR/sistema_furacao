import uuid
from django.core.exceptions import ValidationError
from django.db import models
from .furo import Furo

# ------------------------
# Medição
# ------------------------
class Medicao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="medicoes"
    )
    furo = models.ForeignKey(
        Furo,
        on_delete=models.CASCADE,
        related_name="medicoes"
    )

    # ------------------------
    # REGISTO VISUAL / AMOSTRA
    # ------------------------
    # TODO futuro:
    # - validar formato e tamanho da imagem antes do save
    # - guardar metadados técnicos da imagem (resolução, tamanho, extensão)
    # - suportar múltiplas imagens ou anexos por medição, se necessário
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
        # TODO futuro:
        # - avaliar índice por furo/profundidade para otimizar consultas
        # - avaliar constraints adicionais para evitar medições duplicadas no mesmo contexto
        ordering = ["-criado_em", "-profundidade_medida"]
        verbose_name = "Medição"
        verbose_name_plural = "Medições"

    def __str__(self):
        profundidade = self.profundidade_medida if self.profundidade_medida is not None else "-"
        nome_furo = self.nome_furo_snapshot or (self.furo.nome if self.furo_id and self.furo else "-")
        return f"{nome_furo} - {profundidade} m"

    def clean(self):
        super().clean()

        if not self.furo_id:
            raise ValidationError({
                "furo": "A medição deve estar associada a um furo."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo deve estar associado a uma empresa."
            })

        if self.furo and self.furo.empresa_id:
            if self.empresa_id and self.empresa_id != self.furo.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da medição deve ser a mesma do furo."
                })

        if self.profundidade_medida is not None and self.profundidade_medida < 0:
            raise ValidationError({
                "profundidade_medida": "A profundidade medida não pode ser negativa."
            })

        if self.inclinacao_real_medida is not None and not (-90 <= self.inclinacao_real_medida <= 90):
            raise ValidationError({
                "inclinacao_real_medida": "A inclinação real medida deve estar entre -90° e 90°."
            })

        if self.azimute_real_medido is not None and not (0 <= self.azimute_real_medido <= 360):
            raise ValidationError({
                "azimute_real_medido": "O azimute real medido deve estar entre 0° e 360°."
            })

        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            raise ValidationError({
                "latitude": "Latitude inválida."
            })

        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            raise ValidationError({
                "longitude": "Longitude inválida."
            })

        if self.dureza is not None and self.dureza < 0:
            raise ValidationError({
                "dureza": "A dureza não pode ser negativa."
            })

    def save(self, *args, **kwargs):
        if self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

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

        # TODO futuro:
        # - guardar auditoria de quem criou/editou a medição
        # - gerar derivados automáticos para análise 3D/relatórios
        # - comprimir/otimizar imagem antes de persistir

        self.full_clean()
        super().save(*args, **kwargs)