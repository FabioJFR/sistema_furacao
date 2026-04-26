import uuid

from django.db import models


class ConfiguracaoPagamentoPlataforma(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50, unique=True, default="principal")
    paypal_email = models.EmailField(blank=True)
    paypal_password = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Pagamento da Plataforma"
        verbose_name_plural = "Configurações de Pagamento da Plataforma"

    def __str__(self):
        return f"{self.nome} ({'ativo' if self.ativo else 'inativo'})"
