import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models

from .empregado import Empregados
from .projeto import Projeto
from .furo import Furo


def _juntar_data_hora(data, hora):
    return datetime.combine(data, hora)


def _hora_apos(data, base_hora, hora_para_validar):
    base_dt = _juntar_data_hora(data, base_hora)
    hora_dt = _juntar_data_hora(data, hora_para_validar)

    if hora_dt < base_dt:
        hora_dt += timedelta(days=1)

    return hora_dt


class RegistoDiarioEmpregado(models.Model):
    TIPO_PARAGEM_CHOICES = [
        ("", "---------"),
        ("cliente", "Cliente"),
        ("empresa", "Empresa"),
    ]
    RELATORIO_SIM_NAO_CHOICES = [
        ("sim", "Sim"),
        ("nao", "Não"),
    ]
    RELATORIO_OCORRENCIA_CHOICES = [
        ("manobra", "Manobra"),
        ("reaming", "Reaming"),
        ("avaria", "Avaria"),
        ("horas_paragem", "Horas paragem"),
        ("medicao_desvio", "Medição de desvio"),
        ("cimentacao", "Cimentação"),
        ("lavar_furo", "Lavar furo"),
        ("varas_presas", "Varas presas"),
        ("entubamento", "Entubamento"),
        ("bit_novo", "Bit novo"),
        ("outros", "Outros"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    empregado = models.ForeignKey(
        Empregados,
        on_delete=models.CASCADE,
        related_name="registos_diarios"
    )
    empresa = models.ForeignKey(
        "plataforma.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="registos_diarios"
    )
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_projeto"
    )

    furo = models.ForeignKey(
        Furo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_furo"
    )
    planeamento_turno = models.ForeignKey(
        "projetos.PlaneamentoTurno",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registos_diarios",
    )

    data = models.DateField(null=True, blank=True)

    hora_inicio = models.TimeField(null=True, blank=True)
    hora_inicio_pausa = models.TimeField(null=True, blank=True)
    hora_fim_pausa = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)

    horas_trabalhadas = models.FloatField(default=0.0)
    horas_trabalhadas_furo = models.DurationField(null=True, blank=True)

    horas_paragem = models.FloatField(default=0.0)
    tipo_paragem = models.CharField(
        max_length=20,
        choices=TIPO_PARAGEM_CHOICES,
        blank=True,
        default=""
    )

    metros_furados = models.FloatField(default=0.0)
    observacoes = models.TextField(blank=True)

    relatorio_foto = models.ImageField(
        upload_to="registos_diarios/relatorios/",
        blank=True,
        null=True
    )
    cliente = models.CharField(max_length=200, blank=True)
    sonda = models.CharField(max_length=120, blank=True)
    torre = models.CharField(max_length=120, blank=True)
    bomba_injecao = models.CharField(max_length=120, blank=True)
    bomba_captacao = models.CharField(max_length=120, blank=True)
    estaleiro = models.CharField(max_length=200, blank=True)
    numero_sondagem = models.CharField(max_length=120, blank=True)
    inclinacao = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    diametro_furo = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    numero_relatorio = models.CharField(max_length=120, blank=True)
    no_inicio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    no_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avanco_turno = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    testemunho_recuperado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentagem_recuperacao = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    furacoes = models.JSONField(default=list, blank=True)
    furacao_inicio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    furacao_fim = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    furacao_avanco = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    furacao_recuperacao = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    furacao_rocha = models.CharField(max_length=200, blank=True)
    furacao_descricao = models.TextField(blank=True)
    operacoes_ocorrencias = models.JSONField(default=list, blank=True)
    manobra = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    manobra_de = models.TimeField(null=True, blank=True)
    manobra_ate = models.TimeField(null=True, blank=True)
    reaming = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    reaming_de = models.TimeField(null=True, blank=True)
    reaming_ate = models.TimeField(null=True, blank=True)
    avaria = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    avaria_de = models.TimeField(null=True, blank=True)
    avaria_ate = models.TimeField(null=True, blank=True)
    relatorio_horas_paragem = models.CharField(
        max_length=3,
        choices=RELATORIO_SIM_NAO_CHOICES,
        blank=True,
        default="nao",
    )
    horas_paragem_de = models.TimeField(null=True, blank=True)
    horas_paragem_ate = models.TimeField(null=True, blank=True)
    medicao_desvio = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    medicao_desvio_de = models.TimeField(null=True, blank=True)
    medicao_desvio_ate = models.TimeField(null=True, blank=True)
    cimentacao = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    cimentacao_de = models.TimeField(null=True, blank=True)
    cimentacao_ate = models.TimeField(null=True, blank=True)
    lavar_furo = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    lavar_furo_de = models.TimeField(null=True, blank=True)
    lavar_furo_ate = models.TimeField(null=True, blank=True)
    polimeros = models.JSONField(default=list, blank=True)
    polimeros_de = models.TimeField(null=True, blank=True)
    polimeros_ate = models.TimeField(null=True, blank=True)
    varas_presas = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    varas_presas_de = models.TimeField(null=True, blank=True)
    varas_presas_ate = models.TimeField(null=True, blank=True)
    outros = models.CharField(max_length=160, blank=True)
    outros_de = models.TimeField(null=True, blank=True)
    outros_ate = models.TimeField(null=True, blank=True)
    notas = models.TextField(blank=True)
    entubamento = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    entubamento_de = models.TimeField(null=True, blank=True)
    entubamento_ate = models.TimeField(null=True, blank=True)
    equipa_turno = models.JSONField(default=list, blank=True)
    especialista_1 = models.CharField(max_length=120, blank=True)
    horas_especialista_1 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    especialista_2 = models.CharField(max_length=120, blank=True)
    horas_especialista_2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    especialista_3 = models.CharField(max_length=120, blank=True)
    horas_especialista_3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    especialista_4 = models.CharField(max_length=120, blank=True)
    horas_especialista_4 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    servente_1 = models.CharField(max_length=120, blank=True)
    horas_servente_1 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    servente_2 = models.CharField(max_length=120, blank=True)
    horas_servente_2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    servente_3 = models.CharField(max_length=120, blank=True)
    horas_servente_3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    servente_4 = models.CharField(max_length=120, blank=True)
    horas_servente_4 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bit_novo = models.CharField(max_length=3, choices=RELATORIO_SIM_NAO_CHOICES, blank=True, default="nao")
    bit_novo_de = models.TimeField(null=True, blank=True)
    bit_novo_ate = models.TimeField(null=True, blank=True)
    turno = models.CharField(max_length=120, blank=True)

    # ------------------------
    # SNAPSHOT DA PROFUNDIDADE
    # ------------------------
    profundidade_furo_antes = models.FloatField(default=0.0)
    profundidade_furo_depois = models.FloatField(default=0.0)

    # ------------------------
    # SNAPSHOT DO PLANEAMENTO INICIAL
    # ------------------------
    profundidade_alvo_inicial_furo = models.FloatField(default=0.0)
    inclinacao_planeada_inicial_furo = models.FloatField(null=True, blank=True)
    azimute_planeado_inicial_furo = models.FloatField(null=True, blank=True)

    # ------------------------
    # SNAPSHOT DO PLANEAMENTO ATUAL
    # ------------------------
    profundidade_alvo_atual_furo = models.FloatField(default=0.0)
    inclinacao_planeada_atual_furo = models.FloatField(null=True, blank=True)
    azimute_planeado_atual_furo = models.FloatField(null=True, blank=True)

    # ------------------------
    # SNAPSHOT DO ESTADO REAL
    # ------------------------
    inclinacao_real_atual_furo = models.FloatField(null=True, blank=True)
    azimute_real_atual_furo = models.FloatField(null=True, blank=True)

    editado_por_empregado = models.BooleanField(default=False)
    editado_em = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data", "-criado_em"]
        verbose_name = "Registo Diário do Empregado"
        verbose_name_plural = "Registos Diários dos Empregados"

    def __str__(self):
        return f"{self.empregado.nome} - {self.data}"

    @property
    def tem_relatorio_tecnico(self):
        campos_relatorio = [
            "cliente", "sonda", "torre", "bomba_injecao", "bomba_captacao", "estaleiro",
            "numero_sondagem", "inclinacao", "diametro_furo", "numero_relatorio", "no_inicio",
            "no_final", "avanco_turno", "testemunho_recuperado", "percentagem_recuperacao",
            "furacoes", "furacao_inicio", "furacao_fim", "furacao_avanco", "furacao_recuperacao",
            "furacao_rocha", "furacao_descricao", "operacoes_ocorrencias", "manobra", "manobra_de", "manobra_ate",
            "reaming", "reaming_de", "reaming_ate", "avaria", "avaria_de", "avaria_ate",
            "relatorio_horas_paragem", "horas_paragem_de", "horas_paragem_ate", "medicao_desvio",
            "medicao_desvio_de", "medicao_desvio_ate", "cimentacao", "cimentacao_de",
            "cimentacao_ate", "lavar_furo", "lavar_furo_de", "lavar_furo_ate", "polimeros",
            "polimeros_de", "polimeros_ate", "varas_presas", "varas_presas_de",
            "varas_presas_ate", "outros", "outros_de", "outros_ate", "notas", "entubamento",
            "entubamento_de", "entubamento_ate", "equipa_turno", "especialista_1", "horas_especialista_1",
            "especialista_2", "horas_especialista_2", "especialista_3", "horas_especialista_3",
            "especialista_4", "horas_especialista_4", "servente_1", "horas_servente_1",
            "servente_2", "horas_servente_2", "servente_3", "horas_servente_3",
            "servente_4", "horas_servente_4", "bit_novo", "bit_novo_de", "bit_novo_ate",
            "turno",
        ]
        campos_sim_nao = {
            "manobra", "reaming", "avaria", "relatorio_horas_paragem", "medicao_desvio",
            "cimentacao", "lavar_furo", "varas_presas", "entubamento", "bit_novo",
        }
        for campo in campos_relatorio:
            valor = getattr(self, campo)
            if campo in campos_sim_nao and valor == "nao":
                continue
            if valor in (None, "", [], (), {}):
                continue
            return True
        return False

    def clean(self):
        super().clean()

        if getattr(self, "empregado_id", None):
            empregado = getattr(self, "empregado", None)
            if not empregado or not getattr(empregado, "empresa_id", None):
                raise ValidationError("O empregado não está associado a uma empresa.")

        if self.projeto and not self.projeto.empresa_id:
            raise ValidationError({
                "projeto": "O projeto tem de estar associado a uma empresa."
            })

        if self.furo and not self.furo.empresa_id:
            raise ValidationError({
                "furo": "O furo tem de estar associado a uma empresa."
            })

        if self.empregado and self.empregado.empresa_id:
            if self.empresa_id and self.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "empresa": "A empresa do registo deve ser a mesma do empregado."
                })
        if self.projeto and self.empregado and self.empregado.empresa_id:
            if self.projeto.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "projeto": "O projeto selecionado não pertence à empresa do empregado."
                })

        if self.furo and self.empregado and self.empregado.empresa_id:
            if self.furo.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "furo": "O furo selecionado não pertence à empresa do empregado."
                })

        if self.projeto and self.furo:
            if self.projeto.empresa_id and self.furo.empresa_id:
                if self.projeto.empresa_id != self.furo.empresa_id:
                    raise ValidationError({
                        "furo": "O furo e o projeto têm de pertencer à mesma empresa."
                    })

        if self.projeto and self.empresa_id and self.projeto.empresa_id != self.empresa_id:
            raise ValidationError({
                "projeto": "O projeto selecionado não pertence à empresa definida no registo."
            })

        if self.furo and self.empresa_id and self.furo.empresa_id != self.empresa_id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence à empresa definida no registo."
            })

        if self.furo and self.projeto and self.furo.projeto_id != self.projeto.id:
            raise ValidationError({
                "furo": "O furo selecionado não pertence ao projeto escolhido."
            })

        if self.planeamento_turno:
            if self.planeamento_turno.empresa_id != self.empregado.empresa_id:
                raise ValidationError({
                    "planeamento_turno": "O planeamento selecionado não pertence à empresa do empregado."
                })
            if self.planeamento_turno.empregado_id and self.planeamento_turno.empregado_id != self.empregado_id:
                raise ValidationError({
                    "planeamento_turno": "O planeamento selecionado não pertence a este empregado."
                })
            if self.projeto_id and self.planeamento_turno.projeto_id != self.projeto_id:
                raise ValidationError({
                    "planeamento_turno": "O planeamento selecionado pertence a outro projeto."
                })
            if self.furo_id and self.planeamento_turno.furo_id and self.planeamento_turno.furo_id != self.furo_id:
                raise ValidationError({
                    "planeamento_turno": "O planeamento selecionado pertence a outro furo."
                })

        # Regra operacional:
        # Furo concluído não aceita novos registos.
        # Em edição, permite guardar se o registo já estava ligado ao mesmo furo.
        if self.furo and self.furo.estado == "concluido":
            if not self.pk:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos relatórios."
                })
            original = RegistoDiarioEmpregado.objects.filter(pk=self.pk).only("furo_id").first()
            if original and original.furo_id != self.furo_id:
                raise ValidationError({
                    "furo": "Este furo está terminado e já não aceita novos relatórios."
                })

        if self.metros_furados is not None and self.metros_furados < 0:
            raise ValidationError({
                "metros_furados": "Os metros furados não podem ser negativos."
            })

        if self.horas_paragem is not None and self.horas_paragem < 0:
            raise ValidationError({
                "horas_paragem": "As horas de paragem não podem ser negativas."
            })

        for campo in [
            "no_inicio",
            "no_final",
            "avanco_turno",
            "testemunho_recuperado",
            "percentagem_recuperacao",
            "furacao_inicio",
            "furacao_fim",
            "furacao_avanco",
            "furacao_recuperacao",
            "horas_especialista_1",
            "horas_especialista_2",
            "horas_especialista_3",
            "horas_especialista_4",
            "horas_servente_1",
            "horas_servente_2",
            "horas_servente_3",
            "horas_servente_4",
        ]:
            valor = getattr(self, campo)
            if valor is not None and valor < 0:
                raise ValidationError({campo: "Este valor não pode ser negativo."})

        if self.no_inicio is not None and self.no_final is not None and self.no_final < self.no_inicio:
            raise ValidationError({"no_final": "O valor 'No final' não pode ser inferior ao 'No início'."})

        if self.furacao_inicio is not None and self.furacao_fim is not None and self.furacao_fim < self.furacao_inicio:
            raise ValidationError({"furacao_fim": "O valor 'Furação fim' não pode ser inferior ao 'Furação início'."})

        if self.furacoes not in (None, ""):
            if not isinstance(self.furacoes, list):
                raise ValidationError({"furacoes": "A lista de furadas é inválida."})
            for index, item in enumerate(self.furacoes, start=1):
                if not isinstance(item, dict):
                    raise ValidationError({"furacoes": f"A linha {index} da lista de furadas é inválida."})
                try:
                    inicio = Decimal(str(item.get("inicio"))) if item.get("inicio") not in (None, "") else None
                    fim = Decimal(str(item.get("fim"))) if item.get("fim") not in (None, "") else None
                    avanco = Decimal(str(item.get("avanco"))) if item.get("avanco") not in (None, "") else None
                    recuperacao = Decimal(str(item.get("recuperacao"))) if item.get("recuperacao") not in (None, "") else None
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ValidationError({"furacoes": f"A linha {index} da lista de furadas contém valores inválidos."}) from exc

                for label, valor in (
                    ("início", inicio),
                    ("fim", fim),
                    ("avanço", avanco),
                    ("recuperação", recuperacao),
                ):
                    if valor is not None and valor < 0:
                        raise ValidationError({"furacoes": f"A linha {index} tem valor negativo em '{label}'."})

                if inicio is not None and fim is not None and fim < inicio:
                    raise ValidationError({"furacoes": f"A linha {index} tem 'Furação fim' inferior a 'Furação início'."})

        if self.operacoes_ocorrencias not in (None, ""):
            if not isinstance(self.operacoes_ocorrencias, list):
                raise ValidationError({"operacoes_ocorrencias": "A lista de operações e ocorrências é inválida."})
            tipos_validos = {chave for chave, _ in self.RELATORIO_OCORRENCIA_CHOICES}
            for index, item in enumerate(self.operacoes_ocorrencias, start=1):
                if not isinstance(item, dict):
                    raise ValidationError({"operacoes_ocorrencias": f"A linha {index} da lista de operações e ocorrências é inválida."})

                tipo = (item.get("tipo") or "").strip()
                hora_de = item.get("de")
                hora_ate = item.get("ate")

                if not tipo and not hora_de and not hora_ate:
                    continue

                if tipo not in tipos_validos:
                    raise ValidationError({"operacoes_ocorrencias": f"A linha {index} tem um tipo de ocorrência inválido."})

                if not hora_de or not hora_ate:
                    raise ValidationError({"operacoes_ocorrencias": f"A linha {index} tem de preencher 'De' e 'Até'."})

                try:
                    datetime.strptime(str(hora_de), "%H:%M")
                    datetime.strptime(str(hora_ate), "%H:%M")
                except ValueError as exc:
                    raise ValidationError({"operacoes_ocorrencias": f"A linha {index} contém horas inválidas."}) from exc

        if self.equipa_turno not in (None, ""):
            if not isinstance(self.equipa_turno, list):
                raise ValidationError({"equipa_turno": "A lista da equipa do turno é inválida."})
            for index, item in enumerate(self.equipa_turno, start=1):
                if not isinstance(item, dict):
                    raise ValidationError({"equipa_turno": f"A linha {index} da equipa do turno é inválida."})
                funcao = str(item.get("funcao") or "").strip()
                nome = str(item.get("nome") or "").strip()
                horas = item.get("horas")
                if not funcao and not nome and horas in (None, "", []):
                    continue
                if not funcao or not nome:
                    raise ValidationError({"equipa_turno": f"A linha {index} da equipa do turno tem de preencher 'Função' e 'Nome'."})
                try:
                    horas_valor = Decimal(str(horas)) if horas not in (None, "") else None
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ValidationError({"equipa_turno": f"A linha {index} da equipa do turno contém horas inválidas."}) from exc
                if horas_valor is not None and horas_valor < 0:
                    raise ValidationError({"equipa_turno": f"A linha {index} da equipa do turno não pode ter horas negativas."})

        horarios = [
            self.hora_inicio,
            self.hora_inicio_pausa,
            self.hora_fim_pausa,
            self.hora_fim,
        ]
        total_horarios = sum(1 for h in horarios if h is not None)

        if 0 < total_horarios < 4:
            raise ValidationError(
                "Preencha todos os horários do turno ou deixe todos em branco."
            )

        if total_horarios == 4:
            if not self.data:
                raise ValidationError({
                    "data": "A data é obrigatória quando preenche os horários."
                })

            inicio_dt = _juntar_data_hora(self.data, self.hora_inicio)
            inicio_pausa_dt = _hora_apos(self.data, self.hora_inicio, self.hora_inicio_pausa)
            fim_pausa_dt = _hora_apos(self.data, self.hora_inicio_pausa, self.hora_fim_pausa)
            fim_dt = _hora_apos(self.data, self.hora_fim_pausa, self.hora_fim)

            if inicio_pausa_dt < inicio_dt:
                raise ValidationError({
                    "hora_inicio_pausa": "A hora de início da pausa deve ser posterior à hora de início."
                })

            if fim_pausa_dt < inicio_pausa_dt:
                raise ValidationError({
                    "hora_fim_pausa": "A hora de fim da pausa deve ser posterior à hora de início da pausa."
                })

            if fim_dt < fim_pausa_dt:
                raise ValidationError({
                    "hora_fim": "A hora de fim deve ser posterior à hora de fim da pausa."
                })

        if self.horas_paragem is not None and self.horas_paragem > 0 and not self.tipo_paragem:
            raise ValidationError({
                "tipo_paragem": "Selecione se a paragem é Cliente ou Empresa."
            })

    def calcular_horas_trabalhadas(self):
        if not all([
            self.data,
            self.hora_inicio is not None,
            self.hora_inicio_pausa is not None,
            self.hora_fim_pausa is not None,
            self.hora_fim is not None,
        ]):
            return 0.0

        dt_inicio = _juntar_data_hora(self.data, self.hora_inicio)
        dt_inicio_pausa = _hora_apos(self.data, self.hora_inicio, self.hora_inicio_pausa)
        dt_fim_pausa = _hora_apos(self.data, self.hora_inicio_pausa, self.hora_fim_pausa)
        dt_fim = _hora_apos(self.data, self.hora_fim_pausa, self.hora_fim)

        periodo_total = (dt_fim - dt_inicio).total_seconds()
        pausa = (dt_fim_pausa - dt_inicio_pausa).total_seconds()

        horas = (periodo_total - pausa) / 3600
        return max(round(horas, 2), 0.0)

    def save(self, *args, **kwargs):
        if self.empregado_id and self.empregado and self.empregado.empresa_id:
            self.empresa_id = self.empregado.empresa_id
        elif self.projeto_id and self.projeto and self.projeto.empresa_id:
            self.empresa_id = self.projeto.empresa_id
        elif self.furo_id and self.furo and self.furo.empresa_id:
            self.empresa_id = self.furo.empresa_id

        self.horas_trabalhadas = self.calcular_horas_trabalhadas()
        self.horas_trabalhadas_furo = timedelta(hours=self.horas_trabalhadas or 0.0)

        self.full_clean()
        super().save(*args, **kwargs)
