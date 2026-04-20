import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from plataforma.models import Empresa, PagamentoEmpresa, PerfilPlataforma, Plano, SubscricaoEmpresa

logger = logging.getLogger("core")


# TODO futuro:
# - substituir a password temporária por convite por email / ativação segura
# - gerar referências de pagamento automaticamente
# - registar auditoria completa do onboarding
# - criar empresa/conta “solo” para planos individuais sem estrutura multiutilizador completa
# - criar Empregados automaticamente quando o onboarding exigir integração imediata com a app projetos
# - ligar criação da subscrição a regras reais de faturação/renovação
# - calcular impostos, descontos e ciclos diferentes (mensal/anual) por plano


def _normalizar_username(username, email):
    valor = (username or "").strip()
    if valor:
        return valor

    if email:
        return email.strip().lower()

    logger.warning("Onboarding sem username e sem email válido para normalização do utilizador.")
    raise ValidationError({
        "username": "É necessário indicar um username ou email para o administrador da empresa."
    })



def _validar_dados_onboarding(
    *,
    nome_empresa,
    nome_admin,
    username_admin,
    email_admin,
    password_admin,
    tipo_acesso,
    plano=None,
):
    if not nome_empresa or not str(nome_empresa).strip():
        logger.warning("Validação falhou no onboarding: nome_empresa em falta.")
        raise ValidationError({"nome_empresa": "O nome da empresa é obrigatório."})

    if not nome_admin or not str(nome_admin).strip():
        logger.warning("Validação falhou no onboarding: nome_admin em falta.")
        raise ValidationError({"nome_admin": "O nome do administrador é obrigatório."})

    if not email_admin or not str(email_admin).strip():
        logger.warning("Validação falhou no onboarding: email_admin em falta.")
        raise ValidationError({"email_admin": "O email do administrador é obrigatório."})

    if not password_admin or len(str(password_admin)) < 8:
        logger.warning("Validação falhou no onboarding: password_admin inválida ou demasiado curta.")
        raise ValidationError({
            "password_admin": "A palavra-passe do administrador deve ter pelo menos 8 caracteres."
        })

    if tipo_acesso not in ["empresa_admin", "empresa_gestor"]:
        logger.warning("Validação falhou no onboarding: tipo_acesso inválido (%s).", tipo_acesso)
        raise ValidationError({
            "tipo_acesso": "O tipo de acesso inicial deve ser empresa_admin ou empresa_gestor."
        })

    username_normalizado = _normalizar_username(username_admin, email_admin)

    if User.objects.filter(username__iexact=username_normalizado).exists():
        logger.warning("Validação falhou no onboarding: username '%s' já existe.", username_normalizado)
        raise ValidationError({
            "username_admin": "Já existe um utilizador com esse username."
        })

    if User.objects.filter(email__iexact=email_admin.strip()).exists():
        logger.warning("Validação falhou no onboarding: email '%s' já existe.", email_admin.strip().lower())
        raise ValidationError({
            "email_admin": "Já existe um utilizador com esse email."
        })

    if Empresa.objects.filter(nome__iexact=str(nome_empresa).strip()).exists():
        logger.warning("Validação falhou no onboarding: empresa '%s' já existe.", str(nome_empresa).strip())
        raise ValidationError({
            "nome_empresa": "Já existe uma empresa com esse nome."
        })

    if plano is not None and not isinstance(plano, Plano):
        logger.warning("Validação falhou no onboarding: plano inválido (%s).", plano)
        raise ValidationError({"plano": "Plano inválido."})

    return username_normalizado


def _obter_datas_subscricao_inicial(data_inicio_subscricao=None, data_fim_subscricao=None):
    hoje = timezone.now().date()
    data_inicio = data_inicio_subscricao or hoje

    # TODO futuro:
    # - diferenciar automaticamente ciclo mensal vs anual conforme a subscrição/plano escolhido
    # - suportar período experimental (trial)
    # - alinhar vencimento com billing real da plataforma
    data_fim = data_fim_subscricao or (data_inicio + timedelta(days=30))

    if data_fim < data_inicio:
        logger.warning(
            "Validação falhou no onboarding: data_fim_subscricao (%s) anterior a data_inicio_subscricao (%s).",
            data_fim,
            data_inicio,
        )
        raise ValidationError({
            "data_fim_subscricao": "A data fim da subscrição não pode ser anterior à data de início."
        })

    return data_inicio, data_fim


@transaction.atomic
def criar_empresa_com_admin(
    *,
    nome_empresa,
    nome_admin,
    email_admin,
    password_admin,
    username_admin=None,
    nif=None,
    telefone=None,
    morada=None,
    pais=None,
    cidade=None,
    observacoes=None,
    plano=None,
    tipo_acesso="empresa_admin",
    estado_empresa="teste",
    ativa=True,
    criar_subscricao_inicial=True,
    valor_subscricao=None,
    data_inicio_subscricao=None,
    data_fim_subscricao=None,
    criar_pagamento_inicial=False,
    valor_pagamento=None,
    data_vencimento_pagamento=None,
    referencia_pagamento=None,
    observacoes_pagamento=None,
):
    logger.info(
        "Início do onboarding de empresa: nome_empresa='%s', email_admin='%s', tipo_acesso='%s', criar_subscricao_inicial=%s, criar_pagamento_inicial=%s",
        str(nome_empresa).strip(),
        str(email_admin).strip().lower(),
        tipo_acesso,
        criar_subscricao_inicial,
        criar_pagamento_inicial,
    )
    username_normalizado = _validar_dados_onboarding(
        nome_empresa=nome_empresa,
        nome_admin=nome_admin,
        username_admin=username_admin,
        email_admin=email_admin,
        password_admin=password_admin,
        tipo_acesso=tipo_acesso,
        plano=plano,
    )

    hoje = timezone.now().date()
    data_inicio, data_fim = _obter_datas_subscricao_inicial(
        data_inicio_subscricao=data_inicio_subscricao,
        data_fim_subscricao=data_fim_subscricao,
    )

    empresa = Empresa.objects.create(
        nome=str(nome_empresa).strip(),
        nif=(nif or "").strip(),
        email=str(email_admin).strip().lower(),
        telefone=(telefone or "").strip(),
        morada=(morada or "").strip(),
        pais=(pais or "").strip(),
        cidade=(cidade or "").strip(),
        plano=plano,
        status=estado_empresa,
        ativo=ativa,
        data_inicio=hoje,
        observacoes=(observacoes or "").strip(),
    )
    logger.info("Empresa criada com sucesso no onboarding: empresa_id=%s, nome='%s'", empresa.pk, empresa.nome)

    primeiro_nome = str(nome_admin).strip().split(" ")[0]
    ultimo_nome = " ".join(str(nome_admin).strip().split(" ")[1:])

    user = User.objects.create_user(
        username=username_normalizado,
        email=str(email_admin).strip().lower(),
        password=password_admin,
        first_name=primeiro_nome,
        last_name=ultimo_nome,
        is_active=True,
    )
    logger.info("Utilizador administrador criado no onboarding: user_id=%s, username='%s'", user.pk, user.username)

    perfil = PerfilPlataforma.objects.create(
        user=user,
        tipo_acesso=tipo_acesso,
        empresa=empresa,
        ativo=True,
    )
    logger.info(
        "Perfil de plataforma criado no onboarding: user_id=%s, tipo_acesso='%s', empresa_id=%s",
        user.pk,
        tipo_acesso,
        empresa.pk,
    )

    subscricao = None
    if criar_subscricao_inicial:
        if plano is None:
            logger.warning("Onboarding com criar_subscricao_inicial=True mas sem plano definido.")
            raise ValidationError({
                "plano": "Para criar subscrição inicial é necessário indicar um plano."
            })

        valor_final_subscricao = valor_subscricao
        if valor_final_subscricao is None:
            valor_final_subscricao = plano.preco_mensal or 0

        subscricao = SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=plano,
            estado="ativa" if ativa else "pendente",
            valor=valor_final_subscricao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            renovacao_automatica=False,
        )
        logger.info(
            "Subscrição inicial criada no onboarding: subscricao_id=%s, empresa_id=%s, plano='%s', valor=%s, estado='%s'",
            subscricao.pk,
            empresa.pk,
            plano.nome,
            subscricao.valor,
            subscricao.estado,
        )

    pagamento = None
    if criar_pagamento_inicial:
        if valor_pagamento is None:
            if subscricao is not None:
                valor_pagamento = subscricao.valor
            elif plano is not None:
                valor_pagamento = plano.preco_mensal or 0
            else:
                logger.warning("Onboarding com criar_pagamento_inicial=True mas sem valor_pagamento determinável.")
                raise ValidationError({
                    "valor_pagamento": "Não foi possível determinar o valor do pagamento inicial."
                })

        pagamento = PagamentoEmpresa.objects.create(
            empresa=empresa,
            subscricao=subscricao,
            descricao="Pagamento inicial de onboarding",
            valor=valor_pagamento,
            data_vencimento=data_vencimento_pagamento or data_inicio,
            estado="pendente",
            referencia=(referencia_pagamento or "").strip(),
            observacoes=(observacoes_pagamento or "").strip(),
        )
        logger.info(
            "Pagamento inicial criado no onboarding: pagamento_id=%s, empresa_id=%s, valor=%s, estado='%s'",
            pagamento.pk,
            empresa.pk,
            pagamento.valor,
            pagamento.estado,
        )

    logger.info(
        "Onboarding concluído com sucesso: empresa_id=%s, user_admin_id=%s, subscricao_id=%s, pagamento_id=%s",
        empresa.pk,
        user.pk,
        subscricao.pk if subscricao else None,
        pagamento.pk if pagamento else None,
    )
    return {
        "empresa": empresa,
        "user_admin": user,
        "perfil_admin": perfil,
        "subscricao": subscricao,
        "pagamento": pagamento,
    }