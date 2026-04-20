from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class PerfilPlataforma(models.Model):
    TIPO_CHOICES = [
        ("platform_owner", "Platform Owner"),
        ("platform_admin", "Platform Admin"),
        ("empresa_admin", "Empresa Admin"),
        ("empresa_gestor", "Empresa Gestor"),
        ("empregado", "Empregado"),
        ("individual", "Individual"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_plataforma",
    )

    tipo_acesso = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default="individual",
    )
    empresa = models.ForeignKey(
        "Empresa",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis_acesso",
    )

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()

        tipos_plataforma = ["platform_owner", "platform_admin"]
        tipos_empresa = ["empresa_admin", "empresa_gestor", "empregado"]
        tipos_sem_empresa = ["individual"]

        if self.tipo_acesso in tipos_plataforma and self.empresa is not None:
            raise ValidationError({
                "empresa": "Utilizadores da plataforma não devem estar associados a uma empresa.",
            })

        if self.tipo_acesso in tipos_empresa and self.empresa is None:
            raise ValidationError({
                "empresa": "Este tipo de utilizador deve estar associado a uma empresa.",
            })

        if self.tipo_acesso in tipos_sem_empresa and self.empresa is not None:
            raise ValidationError({
                "empresa": "Contas individuais não devem estar associadas a uma empresa.",
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.tipo_acesso}"