import uuid
from collections import defaultdict

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Sum

from django.db import models

from plataforma.feature_flags import feature_ativa_para_contexto


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
    logo = models.ImageField(upload_to="plataforma/empresas/logos/", blank=True, null=True)
    geologia_score_config = models.JSONField(default=dict, blank=True)

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

    custo_por_metro_cliente = models.FloatField(default=0.0)
    custo_por_metro_empresa = models.FloatField(default=0.0)
    valor_total_cobrado_cliente = models.FloatField(default=0.0)
    valor_total_gasto_projeto = models.FloatField(default=0.0)
    valor_total_gasto_furo = models.FloatField(default=0.0)
    valor_total_ganho_furo = models.FloatField(default=0.0)
    valor_total_gasto_materias = models.FloatField(default=0.0)
    valor_total_gasto_maquinas = models.FloatField(default=0.0)
    outros_valores_gastos_associados = models.FloatField(default=0.0)

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
        return feature_ativa_para_contexto(
            chave_feature="dashboard_empresa",
            empresa=self,
        )

    def pode_aceder_painel_empregado(self):
        return feature_ativa_para_contexto(
            chave_feature="painel_empregado",
            empresa=self,
        )

    def permite_multiplos_utilizadores(self):
        return feature_ativa_para_contexto(
            chave_feature="multiplos_utilizadores",
            empresa=self,
        )

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

    def recalcular_indicadores_financeiros(self, guardar=True):
        Despesa = apps.get_model("projetos", "Despesa")
        Furo = apps.get_model("projetos", "Furo")
        Projeto = apps.get_model("projetos", "Projeto")
        Material = apps.get_model("projetos", "Material")
        LevantamentoMaterial = apps.get_model("projetos", "LevantamentoMaterial")
        DevolucaoMaterial = apps.get_model("projetos", "DevolucaoMaterial")

        total_metros = float(
            Furo.objects.filter(empresa_id=self.pk).aggregate(total=Sum("metros_furados"))["total"] or 0
        )

        despesas = Despesa.objects.filter(empresa_id=self.pk)
        total_despesas = float(despesas.aggregate(total=Sum("valor"))["total"] or 0)
        self.valor_total_gasto_projeto = float(
            despesas.filter(projeto__isnull=False).aggregate(total=Sum("valor"))["total"] or 0
        )
        self.valor_total_gasto_furo = float(
            despesas.filter(furo__isnull=False).aggregate(total=Sum("valor"))["total"] or 0
        )
        self.valor_total_gasto_maquinas = float(
            despesas.filter(maquina__isnull=False).aggregate(total=Sum("valor"))["total"] or 0
        )

        custo_materiais = defaultdict(float)
        materiais_valor = {
            str(material_id): float(valor or 0)
            for material_id, valor in Material.objects.filter(empresa_id=self.pk).values_list("id", "valor")
        }

        for material_id, quantidade in LevantamentoMaterial.objects.filter(empresa_id=self.pk).values_list(
            "material_id", "quantidade"
        ):
            custo_materiais[str(material_id)] += float(quantidade or 0)

        for material_id, quantidade in DevolucaoMaterial.objects.filter(empresa_id=self.pk).values_list(
            "material_id", "quantidade"
        ):
            custo_materiais[str(material_id)] -= float(quantidade or 0)

        self.valor_total_gasto_materias = round(
            sum(max(quantidade, 0) * materiais_valor.get(material_id, 0.0) for material_id, quantidade in custo_materiais.items()),
            2,
        )

        total_gastos_empresa = total_despesas + self.valor_total_gasto_materias + float(
            self.outros_valores_gastos_associados or 0
        )
        self.custo_por_metro_empresa = round(total_gastos_empresa / total_metros, 2) if total_metros else 0.0

        projeto_rates = {
            str(pid): (float(rate) if rate is not None else None)
            for pid, rate in Projeto.objects.filter(empresa_id=self.pk).values_list("id", "custo_por_metro_cliente_override")
        }
        rate_global = float(self.custo_por_metro_cliente or 0)
        total_cobrado = 0.0
        metros_por_projeto = (
            Furo.objects.filter(empresa_id=self.pk)
            .values("projeto_id")
            .annotate(total=Sum("metros_furados"))
        )
        for item in metros_por_projeto:
            metros = float(item.get("total") or 0)
            projeto_id = str(item.get("projeto_id")) if item.get("projeto_id") else ""
            rate_projeto = projeto_rates.get(projeto_id)
            rate_efetiva = rate_global if rate_projeto is None else float(rate_projeto)
            total_cobrado += metros * rate_efetiva

        self.valor_total_cobrado_cliente = round(total_cobrado, 2)
        self.valor_total_ganho_furo = self.valor_total_cobrado_cliente

        if guardar:
            self.save(
                update_fields=[
                    "custo_por_metro_empresa",
                    "valor_total_cobrado_cliente",
                    "valor_total_gasto_projeto",
                    "valor_total_gasto_furo",
                    "valor_total_ganho_furo",
                    "valor_total_gasto_materias",
                    "valor_total_gasto_maquinas",
                    "atualizado_em",
                ]
            )
        return {
            "total_metros": total_metros,
            "total_despesas": round(total_despesas, 2),
            "valor_total_gasto_materias": self.valor_total_gasto_materias,
            "custo_por_metro_empresa": self.custo_por_metro_empresa,
            "valor_total_cobrado_cliente": self.valor_total_cobrado_cliente,
            "valor_total_ganho_furo": self.valor_total_ganho_furo,
        }

    def __str__(self):
        return self.nome_comercial or self.nome
