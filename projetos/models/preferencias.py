from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User


class PreferenciasUser(models.Model):
    TEMA_CHOICES = [
        ("claro", "Claro"),
        ("escuro", "Escuro"),
    ]

    IDIOMA_CHOICES = [
        ("pt-pt", "Português"),
        ("en", "English"),
        ("es", "Español"),
        ("fr", "Français"),
        ("de", "Deutsch"),
        ("zh-hans", "简体中文"),
    ]

    PALETA_CHOICES = [
        ("industrial-blue", "Aço Profissional"),
        ("earth-drill", "Terra Técnica"),
        ("graphite-tech", "Grafite Elegante"),
        ("sandstone", "Areia Industrial"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferencias",
    )

    tema = models.CharField(max_length=10, choices=TEMA_CHOICES, default="claro")
    paleta = models.CharField(max_length=30, choices=PALETA_CHOICES, default="industrial-blue")
    idioma = models.CharField(max_length=10, choices=IDIOMA_CHOICES, default="pt-pt")
    # TODO futuro:
    # - avaliar preferências por empresa vs preferências globais do utilizador
    # - adicionar mais opções (layout, notificações, dashboard inicial)
    # - suportar preferências por papel/perfil se necessário
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="preferencias"
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferências de {self.user.username}"

    def clean(self):
        super().clean()

        # TODO futuro:
        # - validar coerência com perfis multiempresa mais avançados
        # - separar preferências pessoais de contexto operacional

        if self.user and hasattr(self.user, "empregado"):
            empregado = self.user.empregado
            if empregado and empregado.empresa_id:
                if self.empresa_id and self.empresa_id != empregado.empresa_id:
                    raise ValidationError(
                        "A empresa das preferências deve ser a mesma do empregado associado ao utilizador."
                    )

        if not self.empresa_id and self.user and hasattr(self.user, "empregado"):
            empregado = self.user.empregado
            if empregado and empregado.empresa_id:
                self.empresa_id = empregado.empresa_id

    def save(self, *args, **kwargs):
        if self.user and hasattr(self.user, "empregado"):
            empregado = self.user.empregado
            if empregado and empregado.empresa_id:
                self.empresa_id = empregado.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
