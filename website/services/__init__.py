import calendar
import logging
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.utils.translation import gettext as _

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    SubscricaoEmpresa,
)
from projetos.models import Individual
from website import selectors

logger = logging.getLogger("core")


@dataclass
class ResultadoRegisto:
    sucesso: bool
    erros: list[str]
    user_id: int | None = None
    tipo_conta: str | None = None


def adicionar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return data_base.replace(year=ano, month=mes, day=dia)


def normalizar_periodo_cobranca(valor):
    try:
        periodo = int(valor or 1)
    except (TypeError, ValueError):
        periodo = 1
    return periodo if periodo in [1, 3, 6, 12] else 1


def obter_valor_plano_por_ciclo(plano, ciclo_subscricao):
    periodo_meses = normalizar_periodo_cobranca(ciclo_subscricao)
    if periodo_meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * periodo_meses


def validar_pedido_registo(payload):
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password1 = payload.get("password1") or ""
    password2 = payload.get("password2") or ""
    nome_empresa = (payload.get("nome_empresa") or "").strip()
    plano_id = payload.get("plano")
    tipo_conta = payload.get("tipo_conta") or "empresa"
    ciclo_subscricao = payload.get("ciclo_subscricao") or "1"

    erros = []

    if not username:
        erros.append(_("O username é obrigatório."))
    if User.objects.filter(username=username).exists():
        erros.append(_("Já existe um utilizador com esse username."))
    if email and User.objects.filter(email=email).exists():
        erros.append(_("Já existe um utilizador com esse email."))
    if not email:
        erros.append(_("O email é obrigatório para confirmares a conta."))

    if not password1 or not password2:
        erros.append(_("A password é obrigatória."))
    elif password1 != password2:
        erros.append(_("As passwords não coincidem."))

    plano = selectors.obter_plano_ativo_por_id(plano_id)
    if not plano:
        erros.append(_("Seleciona um plano válido."))
    else:
        periodo_meses = normalizar_periodo_cobranca(ciclo_subscricao)
        if plano.tipo == "empresa" and tipo_conta != "empresa":
            erros.append(_("O plano escolhido exige conta do tipo empresa."))
        if plano.tipo == "individual" and tipo_conta != "individual":
            erros.append(_("O plano escolhido exige conta do tipo individual."))
        if periodo_meses not in plano.periodos_cobranca_disponiveis_normalizados:
            erros.append(_("Seleciona um período de pagamento válido para o plano escolhido."))
    if tipo_conta == "empresa" and not nome_empresa:
        erros.append(_("O nome da empresa é obrigatório para conta empresa."))

    return {"erros": erros, "plano": plano}


def _resolver_from_email():
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    email_host_user = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    default_from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    if backend == "django.core.mail.backends.smtp.EmailBackend" and email_host_user:
        return email_host_user
    return default_from_email or email_host_user or "noreply@sistemafuracao.local"


def enviar_email_confirmacao_conta(*, user, request=None):
    backend_email = (getattr(settings, "EMAIL_BACKEND", "") or "").strip()
    if (not settings.DEBUG) and backend_email in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
    }:
        raise RuntimeError(
            "EMAIL_BACKEND não está configurado para entrega real de email em produção."
        )

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    caminho = reverse("website:confirmar_conta", kwargs={"uidb64": uid, "token": token})

    if request is not None:
        url_confirmacao = request.build_absolute_uri(caminho)
    else:
        base_url = getattr(settings, "SITE_BASE_URL", "").strip()
        if base_url:
            url_confirmacao = f"{base_url.rstrip('/')}{caminho}"
        else:
            dominio = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost:8000"
            protocolo = "https" if not settings.DEBUG else "http"
            url_confirmacao = f"{protocolo}://{dominio}{caminho}"

    assunto = _("Confirmação de conta - Sistema Furação")
    mensagem = (
        _("Olá!\n\n")
        + _("Obrigado por criares conta no Sistema Furação.\n")
        + _("Para ativares o acesso, confirma o teu email no link abaixo:\n\n")
        + f"{url_confirmacao}\n\n"
        + _("Se não foste tu, ignora esta mensagem.")
    )

    send_mail(
        subject=assunto,
        message=mensagem,
        from_email=_resolver_from_email(),
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info(
        "Email de confirmação enviado. user_id=%s, email='%s', backend='%s'",
        user.id,
        user.email,
        backend_email,
    )


@transaction.atomic
def executar_registo(payload, request=None):
    validacao = validar_pedido_registo(payload)
    erros = validacao["erros"]
    plano = validacao["plano"]
    if erros:
        return ResultadoRegisto(sucesso=False, erros=erros)

    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    password1 = payload.get("password1") or ""
    nome_empresa = (payload.get("nome_empresa") or "").strip()
    nome_responsavel = (payload.get("nome_responsavel") or "").strip()
    tipo_conta = payload.get("tipo_conta") or "empresa"
    ciclo_subscricao = payload.get("ciclo_subscricao") or "1"

    valor_subscricao = obter_valor_plano_por_ciclo(plano, ciclo_subscricao)
    hoje = timezone.now().date()
    proxima_renovacao = adicionar_meses(hoje, normalizar_periodo_cobranca(ciclo_subscricao))

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1,
        is_active=False,
    )

    empresa = None
    tipo_acesso = "individual"
    if tipo_conta == "empresa":
        empresa = Empresa.objects.create(
            nome=nome_empresa,
            nome_comercial=nome_empresa,
            email=email,
            responsavel_nome=nome_responsavel,
            responsavel_email=email,
            plano=plano,
            status="ativa",
            data_inicio=timezone.now().date(),
            ativo=True,
        )
        tipo_acesso = "empresa_admin"

    perfil = PerfilPlataforma.objects.create(
        user=user,
        tipo_acesso=tipo_acesso,
        empresa=empresa,
        ativo=True,
    )

    if tipo_conta == "individual":
        nome_individual = nome_responsavel or username
        Individual.objects.get_or_create(
            user=user,
            defaults={
                "nome": nome_individual,
                "email": email,
                "ativo": True,
            },
        )

    ciclo_normalizado = str(normalizar_periodo_cobranca(ciclo_subscricao))
    if tipo_conta == "empresa":
        subscricao = SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=plano,
            estado="pendente",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            data_inicio=hoje,
            data_fim=proxima_renovacao,
            proxima_renovacao=proxima_renovacao,
            renovacao_definida_manualmente=False,
            renovacao_automatica=False,
            observacoes="Subscrição inicial criada automaticamente no registo público.",
        )
        PagamentoEmpresa.objects.create(
            empresa=empresa,
            subscricao=subscricao,
            descricao="Cobrança inicial de registo",
            valor=valor_subscricao,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo automático para cobrança inicial da subscrição.",
        )
        MovimentoFinanceiroPlataforma.objects.create(
            empresa=empresa,
            plano=plano,
            subscricao=subscricao,
            tipo_movimento="cobranca",
            natureza_fluxo="entrada",
            categoria="subscricao",
            metodo_pagamento="manual",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            valor_bruto=valor_subscricao,
            valor_liquido=valor_subscricao,
            descricao="Cobrança inicial criada no registo público",
            entidade_nome=empresa.nome,
            data_competencia=hoje,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo criado automaticamente para futura exportação e integração financeira.",
        )
    else:
        MovimentoFinanceiroPlataforma.objects.create(
            perfil_plataforma=perfil,
            plano=plano,
            tipo_movimento="cobranca",
            natureza_fluxo="entrada",
            categoria="subscricao",
            metodo_pagamento="manual",
            ciclo_cobranca=ciclo_normalizado,
            valor=valor_subscricao,
            valor_bruto=valor_subscricao,
            valor_liquido=valor_subscricao,
            descricao="Cobrança inicial de conta individual criada no registo público",
            entidade_nome=username,
            data_competencia=hoje,
            data_vencimento=hoje,
            estado="pendente",
            observacoes="Registo criado automaticamente para futura exportação e integração financeira.",
        )

    try:
        enviar_email_confirmacao_conta(user=user, request=request)
    except Exception:
        transaction.set_rollback(True)
        return ResultadoRegisto(
            sucesso=False,
            erros=[
                _("Não foi possível enviar o email de confirmação. Verifica a configuração de email e tenta novamente.")
            ],
        )

    return ResultadoRegisto(sucesso=True, erros=[], user_id=user.id, tipo_conta=tipo_conta)


def reenviar_confirmacao_por_email(*, email, request=None):
    email = (email or "").strip()
    if not email:
        return 0

    utilizadores_inativos = User.objects.filter(
        email__iexact=email,
        is_active=False,
    ).order_by("-date_joined")

    enviados = 0
    for user in utilizadores_inativos:
        enviar_email_confirmacao_conta(user=user, request=request)
        enviados += 1

    return enviados
