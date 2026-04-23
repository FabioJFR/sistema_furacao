from django.core.exceptions import ValidationError
from django.db import models


class ConfiguracaoFeatureAcesso(models.Model):
    empresa = models.ForeignKey(
        "Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="configuracoes_features",
    )
    perfil_plataforma = models.ForeignKey(
        "PerfilPlataforma",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="configuracoes_features",
    )
    chave_feature = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["chave_feature"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "chave_feature"],
                condition=models.Q(empresa__isnull=False),
                name="unique_feature_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["perfil_plataforma", "chave_feature"],
                condition=models.Q(perfil_plataforma__isnull=False),
                name="unique_feature_por_perfil",
            ),
        ]

    def clean(self):
        super().clean()

        if bool(self.empresa_id) == bool(self.perfil_plataforma_id):
            raise ValidationError(
                "A configuração da feature deve estar associada a uma empresa ou a um perfil individual, mas não aos dois."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.empresa_id:
            return f"{self.empresa} · {self.chave_feature}"
        return f"{self.perfil_plataforma} · {self.chave_feature}"
