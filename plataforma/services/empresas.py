from dataclasses import dataclass
from datetime import date, timedelta
import calendar

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from plataforma.models import Empresa, Plano


def adicionar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def normalizar_periodo_meses(ciclo_cobranca):
    valor = str(ciclo_cobranca or "").strip()
    if valor == "mensal":
        return 1
    if valor == "anual":
        return 12
    try:
        meses = int(valor)
    except (TypeError, ValueError):
        meses = 1
    return meses if meses in [1, 3, 6, 12] else 1


def calcular_proxima_renovacao(data_inicio, ciclo_cobranca):
    return adicionar_meses(data_inicio, normalizar_periodo_meses(ciclo_cobranca))


def obter_valor_por_ciclo(plano, ciclo_cobranca):
    meses = normalizar_periodo_meses(ciclo_cobranca)
    if meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * meses


def calcular_alerta_renovacao(subscricao_atual):
    if not subscricao_atual or not subscricao_atual.proxima_renovacao:
        return None
    hoje = timezone.now().date()
    if subscricao_atual.proxima_renovacao <= hoje:
        return "Renovação em atraso ou a vencer hoje."
    if subscricao_atual.proxima_renovacao <= (hoje + timedelta(days=7)):
        return "Renovação próxima nos próximos 7 dias."
    return None


@dataclass
class ResultadoAlteracaoPlano:
    ok: bool
    erro: str | None = None
    empresa: Empresa | None = None
    plano: Plano | None = None


@dataclass
class ResultadoRenovacaoSubscricao:
    ok: bool
    erro: str | None = None
    nova_data: date | None = None


@dataclass
class ResultadoSubmissaoAlteracaoPlano:
    ok: bool
    erro: str | None = None
    plano: Plano | None = None
    ciclo_subscricao: str | None = None


@dataclass
class ResultadoLogoEmpresa:
    ok: bool
    erro: str | None = None


@dataclass
class ResultadoGeologiaScoreConfig:
    ok: bool
    erro: str | None = None


@dataclass
class ResultadoComplianceScoreConfig:
    ok: bool
    erro: str | None = None


DEFAULT_GEOLOGIA_SCORE_CONFIG = {
    "pesos": {
        "sem_logs": 12,
        "conflito_intervalo": 9,
        "pendente_validacao": 3,
        "sem_anexo": 1,
        "sem_log_24h": 4,
        "sem_log_48h": 7,
    },
    "janelas_horas": {
        "atencao": 24,
        "critico": 48,
    },
}

DEFAULT_COMPLIANCE_SCORE_CONFIG = {
    "pesos": {
        "vencidas": 4,
        "criticas": 3,
        "altas": 2,
        "vence_7d": 2,
        "abertas": 1,
    },
    "thresholds": {
        "medio": 6,
        "alto": 12,
    },
}


def _contar_modelo_empresa(app_label, model_name, empresa):
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return 0
    return model.objects.filter(empresa=empresa).count()


def obter_metricas_operacionais_empresa(empresa):
    return {
        "total_projetos": _contar_modelo_empresa("projetos", "Projeto", empresa),
        "total_furos": _contar_modelo_empresa("projetos", "Furo", empresa),
        "total_empregados": _contar_modelo_empresa("projetos", "Empregados", empresa),
    }


def construir_contexto_empresa_detail(
    *,
    empresa,
    perfil,
    subscricao_atual,
    movimentos_financeiros,
    plano_trial_contexto,
):
    metricas = obter_metricas_operacionais_empresa(empresa)
    return {
        "empresa": empresa,
        "perfil": perfil,
        **metricas,
        "subscricao_atual": subscricao_atual,
        "movimentos_financeiros": movimentos_financeiros,
        "alerta_renovacao": calcular_alerta_renovacao(subscricao_atual),
        "plano_trial_contexto": plano_trial_contexto,
    }


def construir_contexto_alterar_plano_empresa(
    *,
    empresa,
    perfil,
    planos,
    subscricao_atual,
    estados_empresa,
    plano_trial_contexto,
):
    return {
        "empresa": empresa,
        "perfil": perfil,
        "planos": planos,
        "subscricao_atual": subscricao_atual,
        "estados_empresa": estados_empresa,
        "titulo": f"Alterar Plano - {empresa.nome}",
        "plano_trial_contexto": plano_trial_contexto,
    }


@transaction.atomic
def atualizar_renovacao_subscricao(subscricao_atual, nova_data: date):
    if not subscricao_atual:
        raise ValidationError("A empresa não tem subscrição ativa para atualizar a renovação.")
    if subscricao_atual.data_inicio and nova_data < subscricao_atual.data_inicio:
        raise ValidationError("A próxima renovação não pode ser anterior ao início da subscrição.")

    subscricao_atual.proxima_renovacao = nova_data
    subscricao_atual.data_fim = nova_data
    subscricao_atual.renovacao_definida_manualmente = True
    subscricao_atual.save(
        update_fields=[
            "proxima_renovacao",
            "data_fim",
            "renovacao_definida_manualmente",
            "atualizado_em",
        ]
    )
    return subscricao_atual


def processar_submissao_renovacao_subscricao(*, subscricao_atual, nova_data_raw):
    valor = str(nova_data_raw or "").strip()
    if not valor:
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="Indique uma data para a próxima renovação.",
        )

    try:
        nova_data = date.fromisoformat(valor)
    except ValueError:
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="A data indicada para a renovação é inválida.",
        )

    try:
        atualizar_renovacao_subscricao(subscricao_atual, nova_data)
    except Exception as exc:
        return ResultadoRenovacaoSubscricao(ok=False, erro=str(exc))

    return ResultadoRenovacaoSubscricao(ok=True, nova_data=nova_data)


def processar_fluxo_renovacao_subscricao(*, method, subscricao_atual, nova_data_raw):
    if method != "POST":
        return ResultadoRenovacaoSubscricao(
            ok=False,
            erro="metodo_invalido",
        )
    return processar_submissao_renovacao_subscricao(
        subscricao_atual=subscricao_atual,
        nova_data_raw=nova_data_raw,
    )


@transaction.atomic
def alterar_plano_empresa(*, empresa, subscricao_atual, novo_plano, ciclo_subscricao, estado_empresa):
    if ciclo_subscricao not in ["1", "3", "6", "12"]:
        return ResultadoAlteracaoPlano(ok=False, erro="Selecione um período de pagamento válido.")

    estados_empresa_validos = {valor for valor, _ in Empresa.STATUS_CHOICES}
    if estado_empresa not in estados_empresa_validos:
        return ResultadoAlteracaoPlano(ok=False, erro="Selecione um estado válido para a empresa.")

    if int(ciclo_subscricao) not in novo_plano.periodos_cobranca_disponiveis_normalizados:
        return ResultadoAlteracaoPlano(ok=False, erro="O plano selecionado não permite esse período de pagamento.")
    empresa.plano = novo_plano
    empresa.status = estado_empresa
    empresa.save(update_fields=["plano", "status", "atualizado_em"])

    if subscricao_atual:
        subscricao_atual.plano = novo_plano
        subscricao_atual.ciclo_cobranca = ciclo_subscricao
        subscricao_atual.valor = obter_valor_por_ciclo(novo_plano, ciclo_subscricao)

        if not subscricao_atual.renovacao_definida_manualmente:
            proxima_renovacao = calcular_proxima_renovacao(
                subscricao_atual.data_inicio,
                ciclo_subscricao,
            )
            subscricao_atual.proxima_renovacao = proxima_renovacao
            subscricao_atual.data_fim = proxima_renovacao

        subscricao_atual.save()

    return ResultadoAlteracaoPlano(ok=True, empresa=empresa, plano=novo_plano)


def processar_submissao_alteracao_plano_empresa(
    *,
    empresa,
    subscricao_atual,
    plano_id,
    ciclo_subscricao,
    estado_empresa,
    obter_plano_ativo_fn,
):
    novo_plano = obter_plano_ativo_fn(plano_id)
    resultado = alterar_plano_empresa(
        empresa=empresa,
        subscricao_atual=subscricao_atual,
        novo_plano=novo_plano,
        ciclo_subscricao=ciclo_subscricao,
        estado_empresa=estado_empresa,
    )
    if not resultado.ok:
        return ResultadoSubmissaoAlteracaoPlano(ok=False, erro=resultado.erro)

    return ResultadoSubmissaoAlteracaoPlano(
        ok=True,
        plano=novo_plano,
        ciclo_subscricao=ciclo_subscricao,
    )


def processar_fluxo_alteracao_plano_empresa(
    *,
    method,
    empresa,
    subscricao_atual,
    plano_id,
    ciclo_subscricao,
    estado_empresa,
    obter_plano_ativo_fn,
):
    if method != "POST":
        return ResultadoSubmissaoAlteracaoPlano(
            ok=False,
            erro="metodo_invalido",
        )
    return processar_submissao_alteracao_plano_empresa(
        empresa=empresa,
        subscricao_atual=subscricao_atual,
        plano_id=plano_id,
        ciclo_subscricao=ciclo_subscricao,
        estado_empresa=estado_empresa,
        obter_plano_ativo_fn=obter_plano_ativo_fn,
    )


def normalizar_geologia_score_config(config_raw):
    config = config_raw if isinstance(config_raw, dict) else {}
    pesos_in = config.get("pesos") if isinstance(config.get("pesos"), dict) else {}
    janelas_in = config.get("janelas_horas") if isinstance(config.get("janelas_horas"), dict) else {}

    pesos = dict(DEFAULT_GEOLOGIA_SCORE_CONFIG["pesos"])
    janelas = dict(DEFAULT_GEOLOGIA_SCORE_CONFIG["janelas_horas"])

    for chave in pesos:
        try:
            valor = int(pesos_in.get(chave, pesos[chave]))
        except (TypeError, ValueError):
            valor = pesos[chave]
        pesos[chave] = max(0, min(100, valor))

    for chave in janelas:
        try:
            valor = int(janelas_in.get(chave, janelas[chave]))
        except (TypeError, ValueError):
            valor = janelas[chave]
        janelas[chave] = max(1, min(240, valor))

    if janelas["critico"] <= janelas["atencao"]:
        janelas["critico"] = max(janelas["atencao"] + 1, DEFAULT_GEOLOGIA_SCORE_CONFIG["janelas_horas"]["critico"])

    return {
        "pesos": pesos,
        "janelas_horas": janelas,
    }


def normalizar_compliance_score_config(config_raw):
    config = config_raw if isinstance(config_raw, dict) else {}
    pesos_in = config.get("pesos") if isinstance(config.get("pesos"), dict) else {}
    thresholds_in = config.get("thresholds") if isinstance(config.get("thresholds"), dict) else {}

    pesos = dict(DEFAULT_COMPLIANCE_SCORE_CONFIG["pesos"])
    thresholds = dict(DEFAULT_COMPLIANCE_SCORE_CONFIG["thresholds"])

    for chave in pesos:
        try:
            valor = int(pesos_in.get(chave, pesos[chave]))
        except (TypeError, ValueError):
            valor = pesos[chave]
        pesos[chave] = max(0, min(100, valor))

    for chave in thresholds:
        try:
            valor = int(thresholds_in.get(chave, thresholds[chave]))
        except (TypeError, ValueError):
            valor = thresholds[chave]
        thresholds[chave] = max(0, min(500, valor))

    if thresholds["alto"] <= thresholds["medio"]:
        thresholds["alto"] = max(
            thresholds["medio"] + 1,
            DEFAULT_COMPLIANCE_SCORE_CONFIG["thresholds"]["alto"],
        )

    return {
        "pesos": pesos,
        "thresholds": thresholds,
    }


@transaction.atomic
def atualizar_geologia_score_config_empresa(empresa, cleaned_data):
    config = {
        "pesos": {
            "sem_logs": int(cleaned_data["sem_logs"]),
            "conflito_intervalo": int(cleaned_data["conflito_intervalo"]),
            "pendente_validacao": int(cleaned_data["pendente_validacao"]),
            "sem_anexo": int(cleaned_data["sem_anexo"]),
            "sem_log_24h": int(cleaned_data["sem_log_24h"]),
            "sem_log_48h": int(cleaned_data["sem_log_48h"]),
        },
        "janelas_horas": {
            "atencao": int(cleaned_data["janela_atencao_horas"]),
            "critico": int(cleaned_data["janela_critico_horas"]),
        },
    }
    empresa.geologia_score_config = normalizar_geologia_score_config(config)
    empresa.save(update_fields=["geologia_score_config", "atualizado_em"])
    return empresa


def processar_fluxo_geologia_score_config(*, method, empresa, form):
    if method != "POST":
        return ResultadoGeologiaScoreConfig(ok=False, erro="metodo_invalido")
    if not form.is_valid():
        return ResultadoGeologiaScoreConfig(ok=False, erro="form_invalido")
    atualizar_geologia_score_config_empresa(empresa, form.cleaned_data)
    return ResultadoGeologiaScoreConfig(ok=True)


@transaction.atomic
def atualizar_compliance_score_config_empresa(empresa, cleaned_data):
    config = {
        "pesos": {
            "vencidas": int(cleaned_data["peso_vencidas"]),
            "criticas": int(cleaned_data["peso_criticas"]),
            "altas": int(cleaned_data["peso_altas"]),
            "vence_7d": int(cleaned_data["peso_vence_7d"]),
            "abertas": int(cleaned_data["peso_abertas"]),
        },
        "thresholds": {
            "medio": int(cleaned_data["threshold_medio"]),
            "alto": int(cleaned_data["threshold_alto"]),
        },
    }
    empresa.compliance_score_config = normalizar_compliance_score_config(config)
    empresa.save(update_fields=["compliance_score_config", "atualizado_em"])
    return empresa


def processar_fluxo_compliance_score_config(*, method, empresa, form):
    if method != "POST":
        return ResultadoComplianceScoreConfig(ok=False, erro="metodo_invalido")
    if not form.is_valid():
        return ResultadoComplianceScoreConfig(ok=False, erro="form_invalido")
    atualizar_compliance_score_config_empresa(empresa, form.cleaned_data)
    return ResultadoComplianceScoreConfig(ok=True)


@transaction.atomic
def toggle_ativa_empresa(empresa):
    empresa.ativo = not empresa.ativo
    if empresa.ativo:
        if empresa.status in ["suspensa", "cancelada"]:
            empresa.status = "ativa"
        mensagem = f"Empresa '{empresa.nome}' reativada com sucesso."
    else:
        empresa.status = "suspensa"
        mensagem = f"Empresa '{empresa.nome}' suspensa com sucesso."

    empresa.save(update_fields=["ativo", "status", "atualizado_em"])
    return empresa, mensagem


def processar_fluxo_toggle_ativa_empresa(*, method, empresa):
    if method != "POST":
        return {
            "ok": False,
            "erro": "metodo_invalido",
            "empresa": empresa,
            "mensagem": None,
        }

    empresa_atualizada, mensagem = toggle_ativa_empresa(empresa)
    return {
        "ok": True,
        "erro": None,
        "empresa": empresa_atualizada,
        "mensagem": mensagem,
    }


@transaction.atomic
def atualizar_logo_empresa(*, method, empresa, logo_file):
    if method != "POST":
        return ResultadoLogoEmpresa(ok=False, erro="metodo_invalido")

    if not logo_file:
        return ResultadoLogoEmpresa(ok=False, erro="Selecione um ficheiro de logo.")

    empresa.logo = logo_file
    try:
        empresa.save(update_fields=["logo", "atualizado_em"])
    except ValidationError as exc:
        if hasattr(exc, "message_dict") and exc.message_dict:
            mensagens = []
            for _, errs in exc.message_dict.items():
                if isinstance(errs, list):
                    mensagens.extend([str(e) for e in errs])
                else:
                    mensagens.append(str(errs))
            detalhe = " | ".join(mensagens)
        else:
            detalhe = str(exc)
        return ResultadoLogoEmpresa(
            ok=False,
            erro=f"Logotipo inválido: {detalhe}. Usa PNG/JPG/WEBP/GIF.",
        )
    return ResultadoLogoEmpresa(ok=True)


@transaction.atomic
def remover_logo_empresa(*, method, empresa):
    if method != "POST":
        return ResultadoLogoEmpresa(ok=False, erro="metodo_invalido")

    if not empresa.logo:
        return ResultadoLogoEmpresa(ok=False, erro="A empresa não tem logo para remover.")

    empresa.logo.delete(save=False)
    empresa.logo = None
    empresa.save(update_fields=["logo", "atualizado_em"])
    return ResultadoLogoEmpresa(ok=True)
