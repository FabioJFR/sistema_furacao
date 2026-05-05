from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from plataforma.models import PerfilPlataforma
from projetos.models import EmpregadoProjeto, Empregados, Individual, SalarioBaseFuncao


# TODO futuro:
# - centralizar validações multiempresa num helper/base service reutilizável
# - substituir password temporária hardcoded por geração segura + fluxo de ativação
# - adicionar auditoria para aprovações, criação de utilizadores e encerramento de ligações



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _obter_salario_base_funcao(*, empresa=None, funcao=None):
    funcao_valor = (funcao or "").strip()
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if not empresa_id or not funcao_valor:
        return 0.0

    salario = (
        SalarioBaseFuncao.objects.filter(empresa_id=empresa_id, funcao=funcao_valor)
        .values_list("salario_base", flat=True)
        .first()
    )
    return float(salario or 0.0)



def _obter_ou_criar_grupo_empregados():
    grupo, _ = Group.objects.get_or_create(name="Empregados")
    return grupo



def _gerar_username_empregado(empregado):
    base = (empregado.email or empregado.nome or "").strip()
    if "@" in base:
        base = base.split("@", 1)[0]
    base = slugify(base).replace("-", "") or f"empregado{str(empregado.pk)[:8]}"
    return base[:150]


def _gerar_username_disponivel(base_username):
    base = (base_username or "empregado").strip()[:150] or "empregado"
    if not User.objects.filter(username__iexact=base).exists():
        return base

    for i in range(2, 10000):
        sufixo = str(i)
        candidato = f"{base[:150 - len(sufixo)]}{sufixo}"
        if not User.objects.filter(username__iexact=candidato).exists():
            return candidato

    raise ValidationError("Não foi possível gerar um nome de utilizador disponível.")



def _validar_ligacao_empresa(ligacao, empresa=None):
    if empresa is None:
        return

    empresa_id = _resolver_empresa_id(empresa)

    if ligacao.empresa_id and ligacao.empresa_id != empresa_id:
        raise ValidationError("A ligação não pertence à empresa atual.")
    if ligacao.empregado.empresa_id and ligacao.empregado.empresa_id != empresa_id:
        raise ValidationError("O empregado da ligação não pertence à empresa atual.")
    if ligacao.projeto.empresa_id and ligacao.projeto.empresa_id != empresa_id:
        raise ValidationError("O projeto da ligação não pertence à empresa atual.")



def validar_empregado_empresa(empregado, empresa=None):
    if not empregado:
        raise ValidationError("Empregado inválido.")

    if empresa is not None and empregado.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O empregado não pertence à empresa atual.")



def recalcular_resumo_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    registos = empregado.registos_diarios.all()

    if empresa is not None:
        registos = registos.filter(empresa_id=_resolver_empresa_id(empresa))

    total_horas = registos.aggregate(total=Sum("horas_trabalhadas"))["total"] or 0
    horas_mes = registos.filter(data__gte=inicio_mes, data__lte=hoje).aggregate(
        total=Sum("horas_trabalhadas")
    )["total"] or 0
    horas_hoje = registos.filter(data=hoje).aggregate(total=Sum("horas_trabalhadas"))["total"] or 0

    total_metros = registos.aggregate(total=Sum("metros_furados"))["total"] or 0
    metros_mes = registos.filter(data__gte=inicio_mes, data__lte=hoje).aggregate(
        total=Sum("metros_furados")
    )["total"] or 0
    metros_hoje = registos.filter(data=hoje).aggregate(total=Sum("metros_furados"))["total"] or 0

    total_furos = registos.exclude(furo__isnull=True).values("furo").distinct().count()
    total_dias_com_registo = registos.values("data").distinct().count()

    media_m_h = total_metros / total_horas if total_horas > 0 else 0
    media_m_d = total_metros / total_dias_com_registo if total_dias_com_registo > 0 else 0

    empregado.horas_total = total_horas
    empregado.horas_trabalhadas_mes = horas_mes
    empregado.horas_diarias = horas_hoje

    empregado.total_metros_furados = total_metros
    empregado.metros_furados_mes = metros_mes
    empregado.metros_furados_hoje = metros_hoje
    empregado.total_furos_trabalhados = total_furos
    empregado.media_metros_por_hora = round(media_m_h, 2)
    empregado.media_metros_por_dia = round(media_m_d, 2)

    empregado.save(
        update_fields=[
            "horas_total",
            "horas_trabalhadas_mes",
            "horas_diarias",
            "total_metros_furados",
            "metros_furados_mes",
            "metros_furados_hoje",
            "total_furos_trabalhados",
            "media_metros_por_hora",
            "media_metros_por_dia",
        ]
    )



def criar_utilizador_para_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    username_base = _gerar_username_empregado(empregado)
    password = "123456"

    if empregado.user_id:
        raise ValidationError("Este empregado já tem um utilizador associado.")

    # Se já existir um utilizador com o username base, tentamos primeiro
    # reaproveitar uma conta solta com o mesmo email (sem empregado associado).
    user_existente = User.objects.filter(username__iexact=username_base).first()
    if user_existente:
        tem_empregado = Empregados.objects.filter(user=user_existente).exclude(pk=empregado.pk).exists()
        email_empregado = (empregado.email or "").strip().lower()
        email_user = (user_existente.email or "").strip().lower()
        if not tem_empregado and email_empregado and email_user and email_empregado == email_user:
            empregado.user = user_existente
            empregado.save(update_fields=["user"])
            user_existente.is_active = True
            user_existente.save(update_fields=["is_active"])
            grupo = _obter_ou_criar_grupo_empregados()
            user_existente.groups.add(grupo)
            return empregado

    username = _gerar_username_disponivel(username_base)
    user = User.objects.create_user(
        username=username,
        password=password,
        email=empregado.email,
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )

    empregado.user = user
    empregado.save(update_fields=["user"])

    grupo = _obter_ou_criar_grupo_empregados()
    user.groups.add(grupo)

    return empregado



def criar_empregado_com_utilizador(empregado, empresa=None):
    return criar_utilizador_para_empregado(empregado, empresa=empresa)



def aprovar_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    # Aprovação deve funcionar mesmo quando existem dados legados com validações
    # de modelo que não estão diretamente ligadas a este fluxo.
    data_aprovacao = timezone.now()
    Empregados.objects.filter(pk=empregado.pk).update(
        aprovado=True,
        data_aprovacao=data_aprovacao,
    )
    empregado.aprovado = True
    empregado.data_aprovacao = data_aprovacao

    if empregado.user:
        empregado.user.is_active = True
        empregado.user.save(update_fields=["is_active"])

        grupo = _obter_ou_criar_grupo_empregados()
        empregado.user.groups.add(grupo)

    return empregado



def terminar_ligacao_projeto_empregado(ligacao, empresa=None):
    _validar_ligacao_empresa(ligacao, empresa=empresa)

    ligacao.ativo = False
    if not ligacao.data_fim:
        ligacao.data_fim = timezone.now().date()
    ligacao.save(update_fields=["ativo", "data_fim"])
    return ligacao



def terminar_projeto_empregado(ligacao, empresa=None):
    return terminar_ligacao_projeto_empregado(ligacao, empresa=empresa)



def empregado_ja_tem_projeto_ativo(empregado, projeto, excluir_ligacao_id=None, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    if empresa is not None and projeto.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O projeto não pertence à empresa atual.")

    qs = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        projeto=projeto,
        ativo=True,
    )

    if empresa is not None:
        qs = qs.filter(empresa_id=_resolver_empresa_id(empresa))

    if excluir_ligacao_id:
        qs = qs.exclude(id=excluir_ligacao_id)

    return qs.exists()


def garantir_ligacao_projeto_por_furo(empregado, furo, empresa=None, data_inicio=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    if not furo:
        raise ValidationError("Furo inválido.")

    projeto = getattr(furo, "projeto", None)
    if not projeto:
        raise ValidationError("O furo selecionado não está associado a um projeto.")

    if empresa is not None and projeto.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O projeto do furo não pertence à empresa atual.")

    ligacoes_ativas = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        projeto=projeto,
        ativo=True,
    )

    if empresa is not None:
        ligacoes_ativas = ligacoes_ativas.filter(empresa_id=_resolver_empresa_id(empresa))

    ligacao_existente = ligacoes_ativas.order_by("-data_inicio", "-id").first()
    if ligacao_existente:
        return ligacao_existente, False

    nova_data_inicio = data_inicio
    if nova_data_inicio:
        conflito_mesma_data = EmpregadoProjeto.objects.filter(
            empregado=empregado,
            projeto=projeto,
            data_inicio=nova_data_inicio,
        )
        if empresa is not None:
            conflito_mesma_data = conflito_mesma_data.filter(empresa_id=_resolver_empresa_id(empresa))
        if conflito_mesma_data.exists():
            nova_data_inicio = None

    ligacao = EmpregadoProjeto.objects.create(
        empregado=empregado,
        projeto=projeto,
        empresa_id=_resolver_empresa_id(empresa) if empresa is not None else projeto.empresa_id,
        data_inicio=nova_data_inicio,
        ativo=True,
    )
    return ligacao, True


def registar_conta_publica(*, tipo_conta, nome, email, telefone=None, funcao=None, especialidade=None):
    if tipo_conta == "individual":
        Individual.objects.create(
            user=None,
            nome=nome,
            email=email,
            telefone=telefone,
            especialidade=especialidade,
        )
        return "individual"

    Empregados.objects.create(
        user=None,
        nome=nome,
        email=email,
        telefone=telefone,
        funcao=funcao,
        empresa=None,
        salario=0.0,
        aprovado=False,
    )
    return "empregado"


@transaction.atomic
def criar_empregado_com_user_form(*, form, empresa):
    username = form.cleaned_data["username"]
    password = form.cleaned_data["password"]

    user = User.objects.create_user(
        username=username,
        email=form.cleaned_data.get("email") or "",
        password=password,
        first_name=(form.cleaned_data.get("nome") or "").split(" ")[0],
        is_staff=False,
        is_superuser=False,
        is_active=False,
    )

    empregado = form.save(commit=False)
    empregado.user = user
    empregado.empresa = empresa
    empregado.salario = _obter_salario_base_funcao(
        empresa=empresa,
        funcao=form.cleaned_data.get("funcao"),
    )
    empregado.aprovado = False
    empregado.data_aprovacao = None
    empregado.save()
    form.save_m2m()
    return user, empregado


@transaction.atomic
def criar_empregado_admin(*, form, empresa):
    return criar_empregado_com_user_form(form=form, empresa=empresa)


@transaction.atomic
def atualizar_empregado_admin(*, form, empresa):
    funcao_anterior = None
    user_anterior_id = None
    if form.instance and form.instance.pk:
        dados_anteriores = (
            Empregados.objects.filter(pk=form.instance.pk)
            .values_list("funcao", "user_id")
            .first()
        )
        if dados_anteriores:
            funcao_anterior, user_anterior_id = dados_anteriores

    empregado = form.save(commit=False)
    empregado.empresa = empresa

    # Proteção: ao editar, não perder ligação User<->Empregado quando o campo
    # user não vem preenchido no POST.
    if not empregado.user_id and user_anterior_id:
        empregado.user_id = user_anterior_id

    funcao_nova = form.cleaned_data.get("funcao")
    funcao_alterada = (funcao_nova or "") != (funcao_anterior or "")
    if form.cleaned_data.get("aplicar_salario_base_funcao") or funcao_alterada:
        empregado.salario = _obter_salario_base_funcao(
            empresa=empresa,
            funcao=funcao_nova,
        )
    empregado.save()
    form.save_m2m()
    return empregado


@transaction.atomic
def apagar_empregado_admin(*, empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)
    empregado_id = empregado.id
    empregado.delete()
    return empregado_id


@transaction.atomic
def registar_utilizador_e_perfil(*, user, tipo_conta, nome, email, telefone=None, funcao=None, especialidade=None, empresa=None):
    if tipo_conta == "individual":
        Individual.objects.create(
            user=user,
            nome=nome,
            email=email,
            telefone=telefone,
            especialidade=especialidade,
        )
        PerfilPlataforma.objects.create(
            user=user,
            tipo_acesso="individual",
            empresa=None,
            ativo=True,
        )
        return "individual"

    Empregados.objects.create(
        user=user,
        nome=nome,
        email=email,
        telefone=telefone,
        funcao=funcao,
        empresa=empresa,
        salario=_obter_salario_base_funcao(empresa=empresa, funcao=funcao),
        aprovado=False,
    )
    return "empregado"


@transaction.atomic
def processar_registo_empregado_form(*, form):
    if not form.is_valid():
        return {"estado": "form_invalido"}

    user = form.save(commit=False)
    user.email = form.cleaned_data["email"]
    tipo_conta = form.cleaned_data["tipo_conta"]
    user.is_active = tipo_conta == "individual"
    user.save()

    resultado_registo = registar_utilizador_e_perfil(
        user=user,
        tipo_conta=tipo_conta,
        nome=form.cleaned_data["nome"],
        email=form.cleaned_data["email"],
        telefone=form.cleaned_data.get("telefone"),
        funcao=form.cleaned_data.get("funcao"),
        especialidade=form.cleaned_data.get("especialidade"),
        empresa=getattr(form, "empresa_resolvida", None),
    )

    return {
        "estado": "ok",
        "resultado_registo": resultado_registo,
        "user": user,
    }


def processar_fluxo_registo_empregado_form(
    *,
    method,
    post_data,
    form_class,
):
    if method == "POST":
        form = form_class(post_data)
        resultado = processar_registo_empregado_form(form=form)
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(),
        "resultado": None,
    }


@transaction.atomic
def garantir_individual_para_user(user):
    individual = Individual.objects.filter(user=user).first()
    if individual:
        return individual, False

    nome = (
        user.get_full_name().strip()
        or user.username
        or user.email
        or "Conta Individual"
    )
    individual = Individual.objects.create(
        user=user,
        nome=nome,
        email=user.email or "",
        ativo=True,
    )
    return individual, True


@transaction.atomic
def guardar_ligacao_projeto_empregado(
    *,
    empregado,
    empresa,
    projeto,
    ativo=True,
    data_inicio=None,
    data_fim=None,
    ligacao=None,
):
    validar_empregado_empresa(empregado, empresa=empresa)

    if projeto.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O projeto não pertence à empresa atual.")

    if ligacao is None:
        ligacao = EmpregadoProjeto()

    ligacao.empregado = empregado
    ligacao.empresa = empresa
    ligacao.projeto = projeto
    ligacao.ativo = ativo
    ligacao.data_inicio = data_inicio
    ligacao.data_fim = data_fim

    existe_ativa = empregado_ja_tem_projeto_ativo(
        empregado=empregado,
        projeto=projeto,
        excluir_ligacao_id=ligacao.id,
        empresa=empresa,
    )
    if ativo and existe_ativa:
        raise ValidationError("Este empregado já está associado de forma ativa a este projeto.")

    ligacao.save()
    return ligacao


def processar_guardar_ligacao_projeto_form(
    *,
    form,
    empregado,
    empresa,
    ligacao=None,
):
    if not form.is_valid():
        return None, "form_invalido"
    try:
        ligacao_guardada = guardar_ligacao_projeto_empregado(
            ligacao=ligacao,
            empregado=empregado,
            empresa=empresa,
            projeto=form.cleaned_data["projeto"],
            ativo=form.cleaned_data.get("ativo", ligacao.ativo if ligacao else True),
            data_inicio=form.cleaned_data.get("data_inicio"),
            data_fim=form.cleaned_data.get("data_fim"),
        )
        return ligacao_guardada, None
    except ValidationError as erro:
        form.add_error("projeto", str(erro))
        return None, "validacao"


@transaction.atomic
def guardar_ficheiro_empregado(*, form, empregado, empresa):
    validar_empregado_empresa(empregado, empresa=empresa)
    ficheiro = form.save(commit=False)
    ficheiro.empregado = empregado
    ficheiro.empresa = empresa
    ficheiro.save()
    return ficheiro


def processar_guardar_ficheiro_empregado_form(*, form, empregado, empresa):
    if not form.is_valid():
        return None, "form_invalido"
    ficheiro = guardar_ficheiro_empregado(
        form=form,
        empregado=empregado,
        empresa=empresa,
    )
    return ficheiro, None


def processar_submissao_ligacao_projeto_admin_form(
    *,
    form,
    empregado,
    empresa,
    ligacao=None,
):
    ligacao_guardada, erro = processar_guardar_ligacao_projeto_form(
        form=form,
        empregado=empregado,
        empresa=empresa,
        ligacao=ligacao,
    )
    return {
        "ok": erro is None,
        "ligacao": ligacao_guardada,
        "erro": erro,
        "erros_form": form.errors,
    }


def processar_fluxo_ligacao_projeto_admin_form(
    *,
    method,
    post_data,
    form_class,
    empresa,
    empregado,
    ligacao=None,
):
    if method == "POST":
        form = form_class(
            post_data,
            instance=ligacao,
            empresa=empresa,
            empregado=empregado,
        )
        resultado = processar_submissao_ligacao_projeto_admin_form(
            form=form,
            empregado=empregado,
            empresa=empresa,
            ligacao=ligacao,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    form = form_class(
        instance=ligacao,
        empresa=empresa,
        empregado=empregado,
    )
    return {
        "form": form,
        "resultado": None,
    }


def processar_submissao_ficheiro_empregado_admin_form(*, form, empregado, empresa):
    ficheiro, erro = processar_guardar_ficheiro_empregado_form(
        form=form,
        empregado=empregado,
        empresa=empresa,
    )
    return {
        "ok": erro is None,
        "ficheiro": ficheiro,
        "erro": erro,
        "erros_form": form.errors,
    }


def processar_fluxo_ficheiro_empregado_admin_form(
    *,
    method,
    post_data,
    files_data,
    form_class,
    empregado,
    empresa,
):
    if method == "POST":
        form = form_class(post_data, files_data)
        resultado = processar_submissao_ficheiro_empregado_admin_form(
            form=form,
            empregado=empregado,
            empresa=empresa,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(),
        "resultado": None,
    }


@transaction.atomic
def remover_ficheiro_empregado(*, ficheiro):
    ficheiro_id = ficheiro.id
    if ficheiro.ficheiro:
        ficheiro.ficheiro.delete(save=False)
    ficheiro.delete()
    return ficheiro_id


def processar_aprovacao_empregado(*, empregado, empresa=None):
    return aprovar_empregado(empregado, empresa=empresa)


@transaction.atomic
def rejeitar_empregado_pendente(*, empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)
    user = empregado.user
    empregado_nome = empregado.nome
    empregado_id = empregado.id

    if user:
        user.is_active = False
        user.save(update_fields=["is_active"])

    empregado.delete()
    return {
        "empregado_id": empregado_id,
        "empregado_nome": empregado_nome,
    }


def processar_rejeicao_empregado_pendente(*, empregado, empresa=None):
    return rejeitar_empregado_pendente(empregado=empregado, empresa=empresa)


def processar_acao_pendente_empregado(*, acao, empregado, empresa=None):
    if acao == "aprovar":
        aprovado = processar_aprovacao_empregado(empregado=empregado, empresa=empresa)
        return {
            "ok": True,
            "tipo": "aprovar",
            "empregado": aprovado,
            "resultado": None,
        }
    if acao == "rejeitar":
        resultado = processar_rejeicao_empregado_pendente(empregado=empregado, empresa=empresa)
        return {
            "ok": True,
            "tipo": "rejeitar",
            "empregado": None,
            "resultado": resultado,
        }
    raise ValidationError("Ação inválida para empregado pendente.")


def processar_acao_terminar_ligacao_projeto(*, ligacao, empresa=None):
    ligacao_terminada = terminar_ligacao_projeto_empregado(ligacao, empresa=empresa)
    return {
        "ok": True,
        "ligacao": ligacao_terminada,
    }


def processar_acao_remover_ficheiro_empregado(*, ficheiro):
    ficheiro_id = remover_ficheiro_empregado(ficheiro=ficheiro)
    return {
        "ok": True,
        "ficheiro_id": ficheiro_id,
    }


def processar_fluxo_apagar_empregado_admin(*, method, empregado, empresa=None):
    if method != "POST":
        return {
            "ok": False,
            "empregado_id": None,
            "erro": "metodo_invalido",
        }

    empregado_id = apagar_empregado_admin(empregado=empregado, empresa=empresa)
    return {
        "ok": True,
        "empregado_id": empregado_id,
        "erro": None,
    }


def processar_fluxo_terminar_ligacao_projeto(*, method, ligacao, empresa=None):
    if method != "POST":
        return {
            "ok": False,
            "ligacao": None,
            "erro": "metodo_invalido",
        }

    resultado = processar_acao_terminar_ligacao_projeto(ligacao=ligacao, empresa=empresa)
    return {
        "ok": True,
        "ligacao": resultado["ligacao"],
        "erro": None,
    }


def processar_fluxo_remover_ficheiro_empregado(*, method, ficheiro):
    if method != "POST":
        return {
            "ok": False,
            "ficheiro_id": None,
            "erro": "metodo_invalido",
        }

    resultado = processar_acao_remover_ficheiro_empregado(ficheiro=ficheiro)
    return {
        "ok": True,
        "ficheiro_id": resultado["ficheiro_id"],
        "erro": None,
    }


def processar_submissao_empregado_admin_form(*, form, empresa, acao):
    if not form.is_valid():
        return {
            "ok": False,
            "user": None,
            "empregado": None,
            "mensagem_erro": "Existem erros no formulário. Corrija os campos assinalados.",
            "erro_tecnico": None,
            "erros_form": form.errors,
        }

    try:
        if acao == "create":
            user, empregado = criar_empregado_admin(form=form, empresa=empresa)
            return {
                "ok": True,
                "user": user,
                "empregado": empregado,
                "mensagem_erro": None,
                "erro_tecnico": None,
                "erros_form": None,
            }
        if acao == "update":
            empregado = atualizar_empregado_admin(form=form, empresa=empresa)
            return {
                "ok": True,
                "user": None,
                "empregado": empregado,
                "mensagem_erro": None,
                "erro_tecnico": None,
                "erros_form": None,
            }
        raise ValidationError("Ação inválida para submissão de empregado.")
    except Exception as exc:  # pragma: no cover - proteção de camada de serviço
        return {
            "ok": False,
            "user": None,
            "empregado": None,
            "mensagem_erro": "Erro ao guardar empregado. Verifique os dados e tente novamente.",
            "erro_tecnico": exc,
            "erros_form": form.errors,
        }


def processar_fluxo_empregado_admin_form(
    *,
    method,
    post_data,
    files_data,
    form_class,
    empresa,
    acao,
    instance=None,
):
    if method == "POST":
        form = form_class(
            post_data,
            files_data,
            instance=instance,
            empresa=empresa,
        )
        resultado = processar_submissao_empregado_admin_form(
            form=form,
            empresa=empresa,
            acao=acao,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    form = form_class(
        instance=instance,
        empresa=empresa,
    )
    return {
        "form": form,
        "resultado": None,
    }


def construir_resumo_registos_projeto_empregado(*, registos):
    total_metros = sum((r.metros_furados or 0) for r in registos)
    total_horas = sum((r.horas_trabalhadas or 0) for r in registos)
    total_registos = registos.count() if hasattr(registos, "count") else len(registos)
    media_metros_hora = round(total_metros / total_horas, 2) if total_horas else 0
    return {
        "total_metros": round(total_metros, 2),
        "total_horas": round(total_horas, 2),
        "total_registos": total_registos,
        "media_metros_hora": media_metros_hora,
    }
