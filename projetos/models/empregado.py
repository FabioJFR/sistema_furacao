import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .projeto import Projeto
from .furo import Furo


# ------------------------
# Empregado
# ------------------------
class Empregados(models.Model):
    FUNCAO_GERAL_CHOICES = [
        ("Perfurador1a", "Perfurador 1ª"),
        ("Perfurador2a", "Perfurador 2ª"),
        ("Perfurador3a", "Perfurador 3ª"),
        ("ajudante_perfurador1", "Ajudante de Perfurador 1"),
        ("ajudante_perfurador2", "Ajudante de Perfurador 2"),
        ("ajudante_perfurador", "Ajudante de Perfurador"),
        ("mecanico", "Mecânico"),
        ("ajudante_mecanico", "Ajudante Mecânico"),
        ("administrador", "Administrador"),
        ("encarregado_obra", "Encarregado de Obra"),
        ("chefe_turno", "Chefe de Turno"),
        ("geologo", "Geólogo"),
        ("supervisor", "Supervisor"),
        ("tecnico_seguranca", "Técnico de Segurança"),
        ("almoxarife", "Almoxarife"),
        ("motorista", "Motorista"),
        ("outro", "Outro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empregado",
    )

    # TODO multiempresa:
    # - idealmente migrar esta relação para usar apenas o model intermédio EmpregadoFuro
    # - validar associações ManyToMany por empresa via signal/form/service
    # - evitar que um empregado fique ligado diretamente a furos de outra empresa
    furos = models.ManyToManyField(
        Furo,
        blank=True,
        related_name="empregados",
    )

    nome = models.CharField(max_length=200, blank=True, default="Empregado")
    funcao = models.CharField(
        max_length=100,
        choices=FUNCAO_GERAL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Função",
    )
    email = models.EmailField(blank=True, null=True)
    data_admissao = models.DateField(null=True, blank=True)
    numero = models.IntegerField(blank=True, null=True)
    data_inicio_contrato = models.DateField(blank=True, null=True)
    data_fim_contrato = models.DateField(blank=True, null=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    idade = models.IntegerField(blank=True, null=True)
    doc_id = models.BigIntegerField(blank=True, null=True)
    nib = models.CharField(max_length=50, blank=True, null=True)
    morada = models.CharField(max_length=200, blank=True, null=True)
    nacionalidade = models.CharField(max_length=100, blank=True, null=True)
    nif = models.BigIntegerField(blank=True, null=True)

    curriculo = models.FileField(
        upload_to="empregados/curriculos/",
        blank=True,
        null=True,
    )
    contrato = models.FileField(
        upload_to="empregados/contratos/",
        blank=True,
        null=True,
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="empregados"
    )
    

    salario = models.FloatField(default=0.0)
    horas_diarias = models.IntegerField(default=0, blank=True)
    horas_mensais = models.IntegerField(default=0, blank=True)
    horas_extra = models.IntegerField(default=0, blank=True)
    horas_trabalhadas_mes = models.IntegerField(default=0, blank=True)
    horas_total = models.IntegerField(default=0, blank=True)

    alertas = models.JSONField(default=list, blank=True)

    total_metros_furados = models.FloatField(default=0.0)
    metros_furados_mes = models.FloatField(default=0.0)
    metros_furados_hoje = models.FloatField(default=0.0)
    total_furos_trabalhados = models.IntegerField(default=0)
    media_metros_por_hora = models.FloatField(default=0.0)
    media_metros_por_dia = models.FloatField(default=0.0)

    total_levantamentos = models.IntegerField(default=0)
    total_devolucoes = models.IntegerField(default=0)

    aprovado = models.BooleanField(default=False)
    data_registo = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Empregado"
        verbose_name_plural = "Empregados"
        ordering = ["nome"]

    def __str__(self):
        return self.nome if self.nome else "Empregado sem nome"

    @property
    def projetos_atuais(self):
        return Projeto.objects.filter(
            empregado_projetos__empregado=self,
            empregado_projetos__ativo=True,
        ).distinct()

    @property
    def projetos_historico(self):
        return Projeto.objects.filter(
            empregado_projetos__empregado=self,
        ).distinct()
    
    def clean(self):
        super().clean()

        # TODO futuro:
        # - tornar empresa obrigatória (remover null/blank após migração de dados antigos)
        # - validar unicidade adicional por email/NIF se a regra de negócio exigir
        # - avaliar auditoria de aprovação/alteração de conta

        if not self.empresa_id:
            raise ValidationError({
                "empresa": "O empregado deve estar associado a uma empresa."
            })

        if self.user and hasattr(self.user, "empregado") and self.user.empregado.pk != self.pk:
            raise ValidationError({
                "user": "Este utilizador já está associado a outro empregado."
            })

        if self.pk and self.empresa_id:
            furos_outra_empresa = self.furos.exclude(empresa_id=self.empresa_id)
            if furos_outra_empresa.exists():
                raise ValidationError({
                    "furos": "Existem furos associados que não pertencem à mesma empresa do empregado."
                })

    def save(self, *args, **kwargs):
        if not self.data_admissao:
            self.data_admissao = timezone.now().date()

        self.full_clean()
        super().save(*args, **kwargs)


class EmpregadoProjeto(models.Model):
    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="ligacoes_projetos",
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name="empregado_projetos",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="empregado_projetos"
    )

    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("empregado", "projeto", "data_inicio")
        ordering = ["-ativo", "-data_inicio"]
        verbose_name = "Ligação Empregado-Projeto"
        verbose_name_plural = "Ligações Empregado-Projeto"

    def __str__(self):
        return f"{self.empregado.nome} - {self.projeto.nome}"
    
    def clean(self):
        super().clean()

        if self.empregado and not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.projeto and not self.projeto.empresa_id:
            raise ValidationError({
                "projeto": "O projeto deve estar associado a uma empresa."
            })

        if self.empregado and self.projeto:
            if self.empregado.empresa_id and self.projeto.empresa_id:
                if self.empregado.empresa_id != self.projeto.empresa_id:
                    raise ValidationError({
                        "projeto": "O empregado e o projeto têm de pertencer à mesma empresa."
                    })

        if self.empresa_id:
            if self.empregado and self.empregado.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da ligação deve ser a mesma do empregado."
                })

            if self.projeto and self.projeto.empresa_id and self.empresa_id != self.projeto.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa da ligação deve ser a mesma do empregado."
                })

        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError({
                "data_fim": "A data de fim não pode ser anterior à data de início."
            })

    # TODO futuro:
    # - guardar motivo de entrada/saída do projeto
    # - suportar histórico mais detalhado de estados da ligação
    # - auditar quem criou/encerrou a ligação
    def save(self, *args, **kwargs):
        if not self.data_inicio:
            self.data_inicio = timezone.now().date()

        if not self.ativo and not self.data_fim:
            self.data_fim = timezone.now().date()

        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.projeto and self.projeto.empresa_id:
            self.empresa_id = self.projeto.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)


class EmpregadoFicheiro(models.Model):
    TIPO_CHOICES = [
        ("foto", "Foto"),
        ("bi", "BI / Cartão de Cidadão"),
        ("nib", "NIB / IBAN"),
        ("contrato", "Contrato"),
        ("curriculo", "Currículo"),
        ("outro", "Outro"),
    ]

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="ficheiros",
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ficheiros"
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="outro")
    titulo = models.CharField(max_length=200, blank=True, default="")
    ficheiro = models.FileField(upload_to="empregados/ficheiros/")
    data_upload = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Ficheiro do Empregado"
        verbose_name_plural = "Ficheiros do Empregado"
        ordering = ["-data_upload"]

    def __str__(self):
        return f"{self.empregado.nome} - {self.get_tipo_display()}"
    
    def clean(self):
        super().clean()

        # TODO futuro:
        # - validar formato/tamanho do ficheiro
        # - categorizar documentos obrigatórios por função/tipo de empregado
        # - guardar auditoria de upload/alteração

        if not self.empregado.empresa_id:
            raise ValidationError({
                "empregado": "O empregado deve estar associado a uma empresa."
            })

        if self.empregado and self.empregado.empresa_id:
            if self.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do ficheiro deve ser a mesma do empregado."
                })

    # TODO futuro:
    # - gerar preview quando aplicável
    # - impedir duplicados exatos por hash/nome se necessário
    # - mover gestão documental para módulo próprio se crescer muito
    def save(self, *args, **kwargs):
        if self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id

        self.full_clean()
        super().save(*args, **kwargs)
