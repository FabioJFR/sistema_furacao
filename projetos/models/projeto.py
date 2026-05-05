import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

# ------------------------
# Projeto
# ------------------------
class Projeto(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=200)
    cliente = models.CharField(max_length=200, blank=True)
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="projetos"
    )
    # 🔥 localização (mantive ambos: cidade + coords)
    cidade = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    localizacao_lat = models.FloatField(null=True, blank=True)
    localizacao_lon = models.FloatField(null=True, blank=True)

    data_inicio_proj = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    atualizado_em = models.DateTimeField(auto_now=True)
    data_fim_proj = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    notas = models.TextField(blank=True)
    custo_por_metro_cliente_override = models.FloatField(
        null=True,
        blank=True,
        help_text="Se definido, este valor substitui o custo por metro global da empresa para este projeto.",
    )
    outros_valores_gastos_associados = models.FloatField(
        default=0.0,
        help_text="Outros custos associados especificamente a este projeto.",
    )

    def __str__(self):
        return self.nome or "Projeto sem nome"

    @property
    def slug_url(self):
        nome_slug = slugify(self.nome or "projeto") or "projeto"
        return f"{nome_slug}--{str(self.pk)[:8]}"

    def get_absolute_url(self):
        return reverse(
            "projetos:projeto_detail",
            kwargs={"pk": self.pk, "slug": self.slug_url},
        )

    def clean(self):
        super().clean()

        if self.nome:
            self.nome = self.nome.strip()

        if self.cidade:
            self.cidade = self.cidade.strip().title()

        if self.pais:
            self.pais = self.pais.strip().title()

        if not self.empresa_id:
            raise ValidationError({
                "empresa": "O projeto deve estar associado a uma empresa."
            })

        if self.nome and self.empresa_id:
            qs = Projeto.objects.filter(
                nome__iexact=self.nome,
                empresa_id=self.empresa_id,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError({
                    "nome": "Já existe um projeto com este nome nesta empresa."
                })

        if self.data_fim_proj and self.data_inicio_proj:
            if self.data_fim_proj.date() < self.data_inicio_proj:
                raise ValidationError({
                    "data_fim_proj": "A data de fim não pode ser anterior à data de início."
                })

        if self.localizacao_lat is not None and not (-90 <= self.localizacao_lat <= 90):
            raise ValidationError({
                "localizacao_lat": "Latitude inválida."
            })

        if self.localizacao_lon is not None and not (-180 <= self.localizacao_lon <= 180):
            raise ValidationError({
                "localizacao_lon": "Longitude inválida."
            })

        if self.custo_por_metro_cliente_override is not None and self.custo_por_metro_cliente_override < 0:
            raise ValidationError({
                "custo_por_metro_cliente_override": "O custo por metro do projeto não pode ser negativo."
            })
        if self.outros_valores_gastos_associados is not None and self.outros_valores_gastos_associados < 0:
            raise ValidationError({
                "outros_valores_gastos_associados": "Outros valores gastos associados do projeto não podem ser negativos."
            })

    def save(self, *args, **kwargs):
        # TODO futuro:
        # - gerar slug/identificador amigável do projeto
        # - auditoria de criação/alteração (created_by/updated_by)
        # - soft-delete em vez de delete físico

        self.full_clean()
        super().save(*args, **kwargs)
