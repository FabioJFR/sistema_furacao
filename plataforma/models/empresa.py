import uuid
from django.core.exceptions import ValidationError

from django.db import models


class Empresa(models.Model):
    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("teste", "Teste"),
        ("suspensa", "Suspensa"),
        ("cancelada", "Cancelada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nome = models.CharField(max_length=200)
    nome_comercial = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)

    nif = models.CharField(max_length=30, blank=True)
    pais = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    morada = models.CharField(max_length=255, blank=True)

    responsavel_nome = models.CharField(max_length=200, blank=True)
    responsavel_email = models.EmailField(blank=True)
    responsavel_telefone = models.CharField(max_length=30, blank=True)

    plano = models.ForeignKey(
        "Plano",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empresas",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="teste")

    data_inicio = models.DateField(blank=True, null=True)
    data_fim = models.DateField(blank=True, null=True)

    limite_utilizadores = models.PositiveIntegerField(default=5)
    observacoes = models.TextField(blank=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def clean(self):
        super().clean()

        if self.status in ["suspensa", "cancelada"]:
            self.ativo = False

        if self.status == "ativa":
            self.ativo = True

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({
                "data_fim": "A data de fim não pode ser anterior à data de início.",
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def tem_plano_ativo(self):
        return bool(self.plano_id and self.ativo and self.status in ["ativa", "teste"])

    def pode_aceder_dashboard_empresa(self):
        if not self.tem_plano_ativo() or not self.plano:
            return False
        return bool(getattr(self.plano, "acesso_dashboard_empresa", False))

    def pode_aceder_painel_empregado(self):
        if not self.tem_plano_ativo() or not self.plano:
            return False
        return bool(getattr(self.plano, "acesso_painel_empregado", False))

    def permite_multiplos_utilizadores(self):
        if not self.tem_plano_ativo() or not self.plano:
            return False
        return bool(getattr(self.plano, "permite_multiplos_utilizadores", False))

    def limite_empregados_plano(self):
        if not self.plano:
            return 0
        return int(getattr(self.plano, "limite_empregados", 0) or 0)

    def limite_projetos_plano(self):
        if not self.plano:
            return 0
        return int(getattr(self.plano, "limite_projetos", 0) or 0)

    def limite_furos_plano(self):
        if not self.plano:
            return 0
        return int(getattr(self.plano, "limite_furos", 0) or 0)

    def __str__(self):
        return self.nome_comercial or self.nome