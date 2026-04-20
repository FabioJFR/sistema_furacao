from django.core.exceptions import ValidationError
from django.db import models
from .registo import RegistoDiarioEmpregado


class RegistoDiarioFotoAmostra(models.Model):
    registo = models.ForeignKey(
        RegistoDiarioEmpregado,
        on_delete=models.CASCADE,
        related_name="fotos_amostra"
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fotos_amostra"
    )
    # TODO futuro:
    # - validar tipo/tamanho do ficheiro antes do save
    # - guardar metadados da imagem (ex: resolução, extensão, tamanho)
    # - permitir mais do que uma categoria de imagem/amostra
    imagem = models.ImageField(upload_to="registos/amostras/")
    descricao = models.CharField(max_length=200, blank=True, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        # TODO futuro:
        # - avaliar índice por registo/data_upload para melhorar listagens
        # - avaliar constraints adicionais se surgir regra de unicidade por imagem/registo
        verbose_name = "Foto de Amostra do Registo"
        verbose_name_plural = "Fotos de Amostra do Registo"
        ordering = ["-data_upload"]

    def clean(self):
        super().clean()

        # TODO futuro:
        # - validar formatos permitidos (jpg, png, webp, etc.)
        # - validar tamanho máximo do ficheiro
        # - validar se a imagem pertence ao contexto operacional esperado

        # Registo deve ter empresa
        if self.registo and not self.registo.empresa_id:
            raise ValidationError({
                "registo": "O registo associado deve ter empresa definida."
            })

        # Coerência de empresa com o registo
        if self.registo and self.registo.empresa_id:
            if self.empresa_id and self.empresa_id != self.registo.empresa_id:
                raise ValidationError(
                    "A empresa da foto deve ser a mesma do registo."
                )

    def save(self, *args, **kwargs):
        # Herdar empresa do registo
        if self.registo and self.registo.empresa_id:
            self.empresa_id = self.registo.empresa_id

        # TODO futuro:
        # - gerar miniaturas/previews automáticas
        # - integrar compressão/otimização antes de guardar
        # - guardar auditoria de quem fez upload/alteração

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Foto amostra - Registo {self.registo.id}"