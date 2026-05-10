from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from projetos.models import AssiduidadeRegisto, NotificacaoGestao


def _titulo_notificacao_ferias(estado_base, data_inicio):
    return f"{estado_base} · {data_inicio.strftime('%d/%m/%Y')}"


def _origem_url_notificacao_ferias(obj):
    url = reverse("projetos:calendario_turnos_empregado")
    if obj.pk:
        return f"{url}?assiduidade={obj.pk}"
    return url


def _criar_notificacao_ferias_empregado(*, obj, estado_base, detalhes=""):
    if not obj.empregado_id or not obj.empresa_id:
        return None
    return NotificacaoGestao.objects.create(
        empresa=obj.empresa,
        responsavel=obj.empregado,
        titulo=_titulo_notificacao_ferias(estado_base, obj.data_inicio),
        tipo="ferias_empregado",
        prioridade="media",
        estado="aberta",
        origem_url=_origem_url_notificacao_ferias(obj),
        detalhes=(detalhes or "").strip(),
    )


def _resolver_notificacoes_estado_ferias(*, obj):
    if not obj.empregado_id or not obj.empresa_id:
        return
    origem_url = _origem_url_notificacao_ferias(obj)
    origem_url_base = reverse("projetos:calendario_turnos_empregado")
    for estado_base in [
        "Pedido de férias submetido",
        "Pedido de férias aprovado",
        "Pedido de férias rejeitado",
    ]:
        NotificacaoGestao.objects.filter(
            empresa=obj.empresa,
            responsavel=obj.empregado,
            tipo="ferias_empregado",
            titulo=_titulo_notificacao_ferias(estado_base, obj.data_inicio),
            origem_url__in=[origem_url, origem_url_base, ""],
            estado__in=["aberta", "em_andamento"],
        ).update(estado="resolvida", atualizado_em=timezone.now())


def criar_assiduidade(*, form, empresa):
    obj = form.save(commit=False)
    obj.empresa = empresa
    validar_saldo_ferias_assiduidade(obj=obj)
    obj.save()
    if obj.tipo == "ferias":
        notificacoes_por_estado = {
            "pendente": (
                "Pedido de férias submetido",
                "O teu pedido de férias foi registado e está a aguardar aprovação da empresa.",
            ),
            "aprovado": (
                "Pedido de férias aprovado",
                "A empresa aprovou o teu pedido de férias.",
            ),
            "rejeitado": (
                "Pedido de férias rejeitado",
                "A empresa rejeitou o teu pedido de férias. Consulta o calendário e fala com a gestão se precisares de mais contexto.",
            ),
        }
        notificacao = notificacoes_por_estado.get(obj.estado)
        if notificacao:
            estado_base, detalhes = notificacao
            _resolver_notificacoes_estado_ferias(obj=obj)
            _criar_notificacao_ferias_empregado(
                obj=obj,
                estado_base=estado_base,
                detalhes=detalhes,
            )
    return obj


def atualizar_assiduidade(*, form):
    obj = form.save(commit=False)
    validar_saldo_ferias_assiduidade(obj=obj)
    obj.save()
    form.save_m2m()
    return obj


def apagar_assiduidade(*, obj):
    obj.delete()


def aprovar_assiduidade(*, obj):
    estado_anterior = obj.estado
    obj.estado = "aprovado"
    try:
        validar_saldo_ferias_assiduidade(obj=obj)
    except ValidationError:
        obj.estado = estado_anterior
        raise
    obj.save(update_fields=["estado", "atualizado_em"])
    if obj.tipo == "ferias":
        _resolver_notificacoes_estado_ferias(obj=obj)
        _criar_notificacao_ferias_empregado(
            obj=obj,
            estado_base="Pedido de férias aprovado",
            detalhes="A empresa aprovou o teu pedido de férias.",
        )
    return obj


def rejeitar_assiduidade(*, obj):
    obj.estado = "rejeitado"
    obj.save(update_fields=["estado", "atualizado_em"])
    if obj.tipo == "ferias":
        _resolver_notificacoes_estado_ferias(obj=obj)
        _criar_notificacao_ferias_empregado(
            obj=obj,
            estado_base="Pedido de férias rejeitado",
            detalhes="A empresa rejeitou o teu pedido de férias. Consulta o calendário e fala com a gestão se precisares de mais contexto.",
        )
    return obj


def _iterar_datas_intervalo(data_inicio, data_fim):
    atual = data_inicio
    limite = data_fim or data_inicio
    while atual <= limite:
        yield atual
        atual += timedelta(days=1)


def _datas_bloqueadas_ferias(*, empregado, datas):
    primeira_data = min(datas)
    ultima_data = max(datas)
    datas_set = set(datas)
    existentes = (
        AssiduidadeRegisto.objects.filter(
            empresa=empregado.empresa,
            empregado=empregado,
            tipo="ferias",
            estado__in=["pendente", "aprovado"],
            data_inicio__lte=ultima_data,
        )
        .filter(Q(data_fim__isnull=True, data_inicio__gte=primeira_data) | Q(data_fim__gte=primeira_data))
    )

    bloqueadas = set()
    for pedido in existentes:
        for dia in _iterar_datas_intervalo(pedido.data_inicio, pedido.data_fim):
            if dia in datas_set:
                bloqueadas.add(dia)
    return bloqueadas


def _validar_saldo_ferias(*, empregado, datas):
    por_ano = {}
    for dia in datas:
        por_ano[dia.year] = por_ano.get(dia.year, 0) + 1

    for ano, total_novos in por_ano.items():
        saldo_disponivel = max(
            int(empregado.dias_ferias_anuais or 0)
            - empregado.dias_ferias_gozados(ano=ano)
            - empregado.dias_ferias_pendentes(ano=ano),
            0,
        )
        if total_novos > saldo_disponivel:
            raise ValidationError(
                f"O pedido excede o saldo de férias disponível para {ano}: "
                f"{saldo_disponivel} dia(s) disponível(eis), {total_novos} dia(s) selecionado(s)."
            )


def _contar_dias_ferias_por_ano(*, queryset):
    total_por_ano = {}
    for pedido in queryset:
        for dia in _iterar_datas_intervalo(pedido.data_inicio, pedido.data_fim):
            total_por_ano[dia.year] = total_por_ano.get(dia.year, 0) + 1
    return total_por_ano


def _datas_sobrepostas_ferias(*, queryset, datas):
    datas_set = set(datas)
    sobrepostas = set()
    for pedido in queryset:
        for dia in _iterar_datas_intervalo(pedido.data_inicio, pedido.data_fim):
            if dia in datas_set:
                sobrepostas.add(dia)
    return sobrepostas


def validar_saldo_ferias_assiduidade(*, obj):
    if obj.tipo != "ferias" or obj.estado not in {"pendente", "aprovado"}:
        return
    if not obj.empregado_id or not obj.empresa_id or not obj.data_inicio:
        return

    datas_pedido = list(_iterar_datas_intervalo(obj.data_inicio, obj.data_fim))
    pedido_por_ano = {}
    for dia in datas_pedido:
        pedido_por_ano[dia.year] = pedido_por_ano.get(dia.year, 0) + 1

    anos = sorted(pedido_por_ano)
    inicio = date(anos[0], 1, 1)
    fim = date(anos[-1], 12, 31)
    existentes = (
        AssiduidadeRegisto.objects.filter(
            empresa_id=obj.empresa_id,
            empregado_id=obj.empregado_id,
            tipo="ferias",
            estado__in=["pendente", "aprovado"],
            data_inicio__lte=fim,
        )
        .filter(Q(data_fim__isnull=True, data_inicio__gte=inicio) | Q(data_fim__gte=inicio))
    )
    if obj.pk:
        existentes = existentes.exclude(pk=obj.pk)

    datas_sobrepostas = _datas_sobrepostas_ferias(queryset=existentes, datas=datas_pedido)
    if datas_sobrepostas:
        datas_formatadas = ", ".join(dia.strftime("%d/%m/%Y") for dia in sorted(datas_sobrepostas))
        raise ValidationError(
            "As férias selecionadas sobrepõem-se a pedido(s) pendente(s)/aprovado(s): "
            f"{datas_formatadas}."
        )

    ocupados_por_ano = _contar_dias_ferias_por_ano(queryset=existentes)
    for ano, total_pedido in pedido_por_ano.items():
        limite = int(obj.empregado.dias_ferias_anuais or 0)
        saldo = max(limite - ocupados_por_ano.get(ano, 0), 0)
        if total_pedido > saldo:
            raise ValidationError(
                f"O pedido excede o saldo de férias disponível para {ano}: "
                f"{saldo} dia(s) disponível(eis), {total_pedido} dia(s) no registo."
            )


def criar_pedidos_ferias_empregado(*, empregado, datas, motivo="", notas=""):
    datas = sorted(set(datas))
    if not datas:
        raise ValidationError("Seleciona pelo menos um dia para pedir férias.")

    datas_bloqueadas = _datas_bloqueadas_ferias(empregado=empregado, datas=datas)
    datas_para_criar = [dia for dia in datas if dia not in datas_bloqueadas]
    _validar_saldo_ferias(empregado=empregado, datas=datas_para_criar)
    criados = []

    for dia in datas_para_criar:
        criados.append(
            AssiduidadeRegisto.objects.create(
                empresa=empregado.empresa,
                empregado=empregado,
                tipo="ferias",
                estado="pendente",
                data_inicio=dia,
                data_fim=dia,
                horas=0.0,
                motivo=(motivo or "").strip(),
                notas=(notas or "").strip(),
            )
        )
        _criar_notificacao_ferias_empregado(
            obj=criados[-1],
            estado_base="Pedido de férias submetido",
            detalhes="O teu pedido de férias foi registado e está a aguardar aprovação da empresa.",
        )

    if not criados:
        raise ValidationError("Os dias selecionados já têm um pedido de assiduidade pendente/aprovado.")

    return {
        "criados": criados,
        "datas_bloqueadas": sorted(datas_bloqueadas),
    }
