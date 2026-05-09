import io
import os
import zipfile
from collections import defaultdict
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from projetos.models import ClienteComercial, ClienteContrato, ClienteContratoAdenda, ClienteContratoWorkflowHistorico
from projetos.models.cliente_contrato import adicionar_meses_data


def _registar_workflow_cliente_contrato(*, cliente_contrato, workflow_anterior, workflow_novo, user=None, observacao=""):
    ClienteContratoWorkflowHistorico.objects.create(
        contrato=cliente_contrato,
        empresa=cliente_contrato.empresa,
        workflow_anterior=workflow_anterior or "",
        workflow_novo=workflow_novo,
        observacao=observacao or "",
        alterado_por=user if getattr(user, "is_authenticated", False) else None,
    )


def criar_cliente_contrato(*, form, empresa, user=None):
    obj = form.save(commit=False)
    obj.empresa = empresa
    obj.save()
    _registar_workflow_cliente_contrato(
        cliente_contrato=obj,
        workflow_anterior="",
        workflow_novo=obj.workflow_comercial,
        user=user,
        observacao=form.cleaned_data.get("observacao_workflow") or "Estado inicial do contrato.",
    )
    return obj


def atualizar_cliente_contrato(*, form, user=None):
    workflow_anterior = (
        ClienteContrato.objects.filter(pk=form.instance.pk).values_list("workflow_comercial", flat=True).first() or ""
    )
    observacao_workflow = form.cleaned_data.get("observacao_workflow") or ""
    obj = form.save()
    if workflow_anterior != obj.workflow_comercial:
        _registar_workflow_cliente_contrato(
            cliente_contrato=obj,
            workflow_anterior=workflow_anterior,
            workflow_novo=obj.workflow_comercial,
            user=user,
            observacao=observacao_workflow,
        )
    return obj


@transaction.atomic
def aplicar_sugestao_workflow_cliente_contrato(*, cliente_contrato, workflow_novo, user=None, observacao=""):
    sugestoes = obter_sugestoes_workflow_cliente_contrato(cliente_contrato=cliente_contrato)
    sugestoes_validas = {item["workflow"] for item in sugestoes}
    if workflow_novo not in sugestoes_validas:
        raise ValueError("Sugestão de workflow inválida.")

    workflow_anterior = cliente_contrato.workflow_comercial or ""
    if workflow_anterior == workflow_novo:
        return False

    cliente_contrato.workflow_comercial = workflow_novo
    cliente_contrato.save(update_fields=["workflow_comercial", "atualizado_em"])
    _registar_workflow_cliente_contrato(
        cliente_contrato=cliente_contrato,
        workflow_anterior=workflow_anterior,
        workflow_novo=workflow_novo,
        user=user,
        observacao=observacao or "Workflow aplicado a partir da sugestão assistida.",
    )
    return True


def apagar_cliente_contrato(*, cliente_contrato):
    cliente_contrato.delete()


def obter_ou_criar_ficha_cliente_comercial(*, empresa, nome_cliente, create_if_missing=True):
    nome_normalizado = (nome_cliente or "").strip()
    if not nome_normalizado:
        raise ValueError("Nome de cliente inválido.")

    ficha = ClienteComercial.objects.filter(
        empresa=empresa,
        nome_cliente__iexact=nome_normalizado,
    ).first()
    if ficha:
        return ficha, False
    if not create_if_missing:
        return None, False

    ficha = ClienteComercial.objects.create(
        empresa=empresa,
        nome_cliente=nome_normalizado,
    )
    return ficha, True


def atualizar_ficha_cliente_comercial(*, form, ficha_cliente):
    obj = form.save(commit=False)
    obj.pk = ficha_cliente.pk
    obj.empresa = ficha_cliente.empresa
    obj.nome_cliente = ficha_cliente.nome_cliente
    obj.save()
    return obj


def construir_timeline_ficha_cliente_comercial(*, ficha_cliente_model):
    if not ficha_cliente_model:
        return []

    timeline = [
        {
            "tipo": "ficha_cliente",
            "data": ficha_cliente_model.criado_em.date(),
            "titulo": "Ficha comercial do cliente criada",
            "detalhe": "Foi criada uma ficha comercial própria para consolidar o relacionamento com este cliente.",
            "contrato_ref": "-",
            "projeto_nome": "-",
        }
    ]

    if ficha_cliente_model.contacto_principal_nome or ficha_cliente_model.contacto_principal_email or ficha_cliente_model.contacto_principal_telefone:
        timeline.append(
            {
                "tipo": "contacto_principal",
                "data": ficha_cliente_model.atualizado_em.date(),
                "titulo": "Contacto principal definido",
                "detalhe": (
                    ficha_cliente_model.contacto_principal_nome
                    or ficha_cliente_model.contacto_principal_email
                    or ficha_cliente_model.contacto_principal_telefone
                ),
                "contrato_ref": "-",
                "projeto_nome": "-",
            }
        )

    if ficha_cliente_model.contacto_secundario_nome or ficha_cliente_model.contacto_secundario_email or ficha_cliente_model.contacto_secundario_telefone:
        timeline.append(
            {
                "tipo": "contacto_secundario",
                "data": ficha_cliente_model.atualizado_em.date(),
                "titulo": "Contacto secundário definido",
                "detalhe": (
                    ficha_cliente_model.contacto_secundario_nome
                    or ficha_cliente_model.contacto_secundario_email
                    or ficha_cliente_model.contacto_secundario_telefone
                ),
                "contrato_ref": "-",
                "projeto_nome": "-",
            }
        )

    timeline.append(
        {
            "tipo": "classificacao",
            "data": ficha_cliente_model.atualizado_em.date(),
            "titulo": "Classificação comercial registada",
            "detalhe": ficha_cliente_model.get_classificacao_comercial_display(),
            "contrato_ref": "-",
            "projeto_nome": "-",
        }
    )

    if ficha_cliente_model.notas_comerciais:
        timeline.append(
            {
                "tipo": "notas",
                "data": ficha_cliente_model.atualizado_em.date(),
                "titulo": "Notas comerciais atualizadas",
                "detalhe": ficha_cliente_model.notas_comerciais[:180],
                "contrato_ref": "-",
                "projeto_nome": "-",
            }
        )

    if ficha_cliente_model.atualizado_em.date() != ficha_cliente_model.criado_em.date():
        timeline.append(
            {
                "tipo": "ficha_atualizada",
                "data": ficha_cliente_model.atualizado_em.date(),
                "titulo": "Ficha comercial atualizada",
                "detalhe": "A informação estratégica do cliente foi revista ou enriquecida.",
                "contrato_ref": "-",
                "projeto_nome": "-",
            }
        )

    return timeline


def obter_data_fim_efetiva_cliente_contrato(*, cliente_contrato):
    ultima_adenda = (
        cliente_contrato.adendas.filter(nova_data_fim__isnull=False)
        .order_by("-nova_data_fim", "-data_adenda", "-criado_em")
        .first()
    )
    if ultima_adenda and ultima_adenda.nova_data_fim:
        return ultima_adenda.nova_data_fim
    return cliente_contrato.data_fim


def obter_total_adendas_cliente_contrato(*, cliente_contrato):
    return cliente_contrato.adendas.aggregate(total=Sum("valor_adicional")).get("total") or 0.0


def obter_alertas_operacionais_cliente_contrato(*, cliente_contrato):
    hoje = timezone.localdate()
    data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    alertas = []

    if cliente_contrato.workflow_comercial == "renovacao_pendente":
        alertas.append(
            {
                "codigo": "workflow_renovacao",
                "gravidade": "alta",
                "titulo": "Renovação pendente",
                "detalhe": "Este contrato está marcado como renovação pendente e exige seguimento comercial.",
            }
        )
    elif cliente_contrato.workflow_comercial == "em_negociacao":
        alertas.append(
            {
                "codigo": "workflow_negociacao",
                "gravidade": "baixa",
                "titulo": "Em negociação",
                "detalhe": "O contrato está em fase de negociação comercial.",
            }
        )
    elif cliente_contrato.workflow_comercial == "perdido":
        alertas.append(
            {
                "codigo": "workflow_perdido",
                "gravidade": "alta",
                "titulo": "Contrato perdido",
                "detalhe": "O contrato foi marcado como perdido e deve ser revisto antes de nova faturação.",
            }
        )
    elif cliente_contrato.workflow_comercial == "renovado":
        alertas.append(
            {
                "codigo": "workflow_renovado",
                "gravidade": "baixa",
                "titulo": "Renovado",
                "detalhe": "O contrato já foi marcado comercialmente como renovado.",
            }
        )

    if cliente_contrato.status == "suspenso":
        alertas.append(
            {
                "codigo": "contrato_suspenso",
                "gravidade": "alta",
                "titulo": "Contrato suspenso",
                "detalhe": "O contrato está suspenso e deve ser revisto comercialmente.",
            }
        )

    if not cliente_contrato.contacto_email and not cliente_contrato.contacto_telefone:
        alertas.append(
            {
                "codigo": "sem_contacto",
                "gravidade": "media",
                "titulo": "Sem contacto definido",
                "detalhe": "O contrato não tem email nem telefone de contacto registados.",
            }
        )

    if data_fim_efetiva:
        dias_para_fim = (data_fim_efetiva - hoje).days
        if dias_para_fim < 0:
            alertas.append(
                {
                    "codigo": "contrato_vencido",
                    "gravidade": "alta",
                    "titulo": "Contrato vencido",
                    "detalhe": f"O contrato venceu há {abs(dias_para_fim)} dia(s).",
                }
            )
        elif dias_para_fim <= cliente_contrato.dias_alerta_vencimento:
            alertas.append(
                {
                    "codigo": "janela_renovacao",
                    "gravidade": "media",
                    "titulo": "Em janela de renovação",
                    "detalhe": f"O contrato termina em {dias_para_fim} dia(s).",
                }
            )

    if cliente_contrato.ultimo_contacto_em:
        dias_sem_contacto = (hoje - cliente_contrato.ultimo_contacto_em).days
        if dias_sem_contacto >= cliente_contrato.dias_alerta_sem_contacto:
            alertas.append(
                {
                    "codigo": "sem_contacto_recente",
                    "gravidade": "media",
                    "titulo": "Cliente sem contacto recente",
                    "detalhe": f"Não existe contacto registado há {dias_sem_contacto} dia(s).",
                }
            )
    elif cliente_contrato.data_inicio:
        dias_desde_inicio = (hoje - cliente_contrato.data_inicio).days
        if dias_desde_inicio >= cliente_contrato.dias_alerta_sem_contacto:
            alertas.append(
                {
                    "codigo": "sem_primeiro_contacto",
                    "gravidade": "baixa",
                    "titulo": "Sem contacto registado",
                    "detalhe": f"O contrato já arrancou há {dias_desde_inicio} dia(s) e ainda não tem contacto registado.",
                }
            )

    if cliente_contrato.proximo_followup_em:
        dias_followup = (cliente_contrato.proximo_followup_em - hoje).days
        if dias_followup < 0:
            alertas.append(
                {
                    "codigo": "followup_atrasado",
                    "gravidade": "alta",
                    "titulo": "Follow-up em atraso",
                    "detalhe": f"O próximo follow-up estava previsto há {abs(dias_followup)} dia(s).",
                }
            )
        elif dias_followup <= 3:
            alertas.append(
                {
                    "codigo": "followup_proximo",
                    "gravidade": "baixa",
                    "titulo": "Follow-up próximo",
                    "detalhe": f"O próximo follow-up está previsto para daqui a {dias_followup} dia(s).",
                }
            )

    return alertas


def obter_sugestoes_workflow_cliente_contrato(*, cliente_contrato):
    hoje = timezone.localdate()
    data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    sugestoes = []

    def adicionar_sugestao(workflow, prioridade, titulo, motivo):
        if any(item["workflow"] == workflow for item in sugestoes):
            return
        sugestoes.append(
            {
                "workflow": workflow,
                "label": dict(ClienteContrato.WORKFLOW_COMERCIAL_CHOICES).get(workflow, workflow),
                "prioridade": prioridade,
                "titulo": titulo,
                "motivo": motivo,
                "ja_ativo": cliente_contrato.workflow_comercial == workflow,
            }
        )

    if data_fim_efetiva:
        dias_para_fim = (data_fim_efetiva - hoje).days
        if dias_para_fim <= cliente_contrato.dias_alerta_vencimento and cliente_contrato.workflow_comercial not in {
            "renovacao_pendente",
            "renovado",
            "perdido",
        }:
            adicionar_sugestao(
                "renovacao_pendente",
                "alta" if dias_para_fim < 0 else "media",
                "Renovação a acompanhar",
                (
                    f"O contrato já venceu há {abs(dias_para_fim)} dia(s)."
                    if dias_para_fim < 0
                    else f"O contrato termina em {dias_para_fim} dia(s), dentro da janela de renovação."
                ),
            )

        if dias_para_fim > cliente_contrato.dias_alerta_vencimento and cliente_contrato.workflow_comercial == "renovacao_pendente":
            adicionar_sugestao(
                "renovado",
                "baixa",
                "Renovação já estabilizada",
                "O fim efetivo do contrato já foi prolongado para fora da janela de alerta.",
            )

    if cliente_contrato.proximo_followup_em:
        dias_followup = (cliente_contrato.proximo_followup_em - hoje).days
        if dias_followup <= 3 and cliente_contrato.workflow_comercial == "estavel":
            adicionar_sugestao(
                "em_negociacao",
                "media" if dias_followup < 0 else "baixa",
                "Follow-up comercial ativo",
                (
                    f"O follow-up está em atraso há {abs(dias_followup)} dia(s)."
                    if dias_followup < 0
                    else f"O follow-up está marcado para daqui a {dias_followup} dia(s)."
                ),
            )

    if cliente_contrato.ultimo_contacto_em:
        dias_sem_contacto = (hoje - cliente_contrato.ultimo_contacto_em).days
        if dias_sem_contacto >= cliente_contrato.dias_alerta_sem_contacto and cliente_contrato.workflow_comercial == "estavel":
            adicionar_sugestao(
                "em_negociacao",
                "media",
                "Cliente precisa de reativação comercial",
                f"Já passaram {dias_sem_contacto} dia(s) sem contacto registado.",
            )

    if cliente_contrato.status == "suspenso" and cliente_contrato.workflow_comercial not in {"perdido", "renovacao_pendente"}:
        adicionar_sugestao(
            "perdido",
            "alta",
            "Contrato suspenso com risco comercial",
            "O contrato está suspenso e deve ser revisto para fecho ou recuperação comercial.",
        )

    ordem_prioridade = {"alta": 0, "media": 1, "baixa": 2}
    return sorted(sugestoes, key=lambda item: (ordem_prioridade.get(item["prioridade"], 9), item["label"]))


def construir_painel_comercial_clientes(*, contratos, incluir_empresa=False):
    hoje = timezone.localdate()
    grupos = {}

    for contrato in contratos:
        processar_renovacao_automatica_cliente_contrato(cliente_contrato=contrato)
        contrato.refresh_from_db()

        data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=contrato)
        total_adendas = obter_total_adendas_cliente_contrato(cliente_contrato=contrato)
        alertas_operacionais = obter_alertas_operacionais_cliente_contrato(cliente_contrato=contrato)
        sugestoes_workflow = obter_sugestoes_workflow_cliente_contrato(cliente_contrato=contrato)
        dias_para_fim = (data_fim_efetiva - hoje).days if data_fim_efetiva else None

        chave = (contrato.empresa_id if incluir_empresa else 0, (contrato.nome_cliente or "").strip().lower())
        if chave not in grupos:
            grupos[chave] = {
                "empresa_id": contrato.empresa_id if incluir_empresa else None,
                "empresa_nome": getattr(contrato.empresa, "nome", "") if incluir_empresa else "",
                "nome_cliente": contrato.nome_cliente,
                "total_contratos": 0,
                "contratos_ativos": 0,
                "contratos_vencidos": 0,
                "contratos_com_alerta": 0,
                "followups_atrasados": 0,
                "valor_base_total": 0.0,
                "valor_total_estimado": 0.0,
                "proximo_followup": None,
                "workflows": defaultdict(int),
                "contratos": [],
            }

        grupo = grupos[chave]
        grupo["total_contratos"] += 1
        if contrato.status == "ativo":
            grupo["contratos_ativos"] += 1
        if dias_para_fim is not None and dias_para_fim < 0:
            grupo["contratos_vencidos"] += 1
        if alertas_operacionais:
            grupo["contratos_com_alerta"] += 1
        if contrato.proximo_followup_em and contrato.proximo_followup_em < hoje:
            grupo["followups_atrasados"] += 1
        if contrato.proximo_followup_em and (
            grupo["proximo_followup"] is None or contrato.proximo_followup_em < grupo["proximo_followup"]
        ):
            grupo["proximo_followup"] = contrato.proximo_followup_em

        grupo["valor_base_total"] += float(contrato.valor_contratado or 0.0)
        grupo["valor_total_estimado"] += float((contrato.valor_contratado or 0.0) + total_adendas)
        grupo["workflows"][contrato.get_workflow_comercial_display()] += 1
        grupo["contratos"].append(
            {
                "pk": contrato.pk,
                "numero_contrato": contrato.numero_contrato,
                "projeto_nome": getattr(contrato.projeto, "nome", "") or "-",
                "status_display": contrato.get_status_display(),
                "workflow_display": contrato.get_workflow_comercial_display(),
                "data_fim_efetiva": data_fim_efetiva,
                "dias_para_fim": dias_para_fim,
                "alertas_operacionais": alertas_operacionais,
                "sugestao_workflow_principal": sugestoes_workflow[0] if sugestoes_workflow else None,
                "valor_total_estimado": float((contrato.valor_contratado or 0.0) + total_adendas),
                "proximo_followup_em": contrato.proximo_followup_em,
            }
        )

    painel = []
    for grupo in grupos.values():
        grupo["contratos"].sort(
            key=lambda item: (
                item["proximo_followup_em"] or date.max,
                item["data_fim_efetiva"] or date.max,
                item["numero_contrato"] or "",
            )
        )
        grupo["workflows_resumo"] = ", ".join(
            f"{workflow}: {total}" for workflow, total in sorted(grupo["workflows"].items(), key=lambda item: item[0])
        )
        painel.append(grupo)

    painel.sort(key=lambda item: ((item["empresa_nome"] or "").lower(), (item["nome_cliente"] or "").lower()))
    return painel


def construir_ficha_cliente_comercial(*, contratos, nome_cliente, empresa_nome="", ficha_cliente_model=None):
    contratos = list(contratos)
    painel = construir_painel_comercial_clientes(contratos=contratos, incluir_empresa=bool(empresa_nome))
    grupo = next((item for item in painel if (item["nome_cliente"] or "").strip().lower() == (nome_cliente or "").strip().lower()), None)
    if not grupo:
        return None

    contactos = []
    timeline = []
    timeline.extend(construir_timeline_ficha_cliente_comercial(ficha_cliente_model=ficha_cliente_model))
    for contrato in contratos:
        if (contrato.nome_cliente or "").strip().lower() != (nome_cliente or "").strip().lower():
            continue

        if contrato.contacto_nome or contrato.contacto_email or contrato.contacto_telefone:
            contactos.append(
                {
                    "contrato_pk": contrato.pk,
                    "contrato_ref": contrato.numero_contrato or "-",
                    "nome": contrato.contacto_nome or "-",
                    "email": contrato.contacto_email or "-",
                    "telefone": contrato.contacto_telefone or "-",
                    "ultimo_contacto_em": contrato.ultimo_contacto_em,
                    "proximo_followup_em": contrato.proximo_followup_em,
                }
            )

        eventos_contrato = construir_timeline_cliente_contrato(cliente_contrato=contrato)
        for evento in eventos_contrato:
            timeline.append(
                {
                    **evento,
                    "contrato_pk": contrato.pk,
                    "contrato_ref": contrato.numero_contrato or "-",
                    "projeto_nome": getattr(contrato.projeto, "nome", "") or "-",
                }
            )

    contactos.sort(
        key=lambda item: (
            item["proximo_followup_em"] or date.max,
            item["ultimo_contacto_em"] or date.max,
            item["contrato_ref"],
        )
    )
    timeline = sorted(timeline, key=lambda item: (item["data"], item["titulo"]), reverse=True)

    return {
        "empresa_nome": empresa_nome or grupo["empresa_nome"],
        "empresa_id": grupo["empresa_id"],
        "nome_cliente": grupo["nome_cliente"],
        "ficha_cliente_model": ficha_cliente_model,
        "contacto_principal_nome": getattr(ficha_cliente_model, "contacto_principal_nome", "") or "",
        "contacto_principal_email": getattr(ficha_cliente_model, "contacto_principal_email", "") or "",
        "contacto_principal_telefone": getattr(ficha_cliente_model, "contacto_principal_telefone", "") or "",
        "contacto_secundario_nome": getattr(ficha_cliente_model, "contacto_secundario_nome", "") or "",
        "contacto_secundario_email": getattr(ficha_cliente_model, "contacto_secundario_email", "") or "",
        "contacto_secundario_telefone": getattr(ficha_cliente_model, "contacto_secundario_telefone", "") or "",
        "classificacao_comercial": getattr(ficha_cliente_model, "classificacao_comercial", "estavel") or "estavel",
        "classificacao_comercial_label": (
            ficha_cliente_model.get_classificacao_comercial_display() if ficha_cliente_model else "Estável"
        ),
        "notas_comerciais": getattr(ficha_cliente_model, "notas_comerciais", "") or "",
        "total_contratos": grupo["total_contratos"],
        "contratos_ativos": grupo["contratos_ativos"],
        "contratos_vencidos": grupo["contratos_vencidos"],
        "contratos_com_alerta": grupo["contratos_com_alerta"],
        "followups_atrasados": grupo["followups_atrasados"],
        "valor_base_total": grupo["valor_base_total"],
        "valor_total_estimado": grupo["valor_total_estimado"],
        "proximo_followup": grupo["proximo_followup"],
        "workflows_resumo": grupo["workflows_resumo"],
        "contratos": grupo["contratos"],
        "contactos": contactos,
        "timeline": timeline,
    }


def gerar_pdf_ficha_cliente_comercial(*, ficha_cliente):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            "Exportação PDF indisponível: instala `reportlab` no ambiente (`pip install reportlab==4.2.2`)."
        ) from exc

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Sistema Furação</b> | Ficha Comercial do Cliente", styles["Title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>Cliente:</b> {ficha_cliente['nome_cliente']}", styles["Heading2"]))
    if ficha_cliente.get("empresa_nome"):
        story.append(Paragraph(f"<b>Empresa:</b> {ficha_cliente['empresa_nome']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Classificação:</b> {ficha_cliente.get('classificacao_comercial_label') or '-'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Data:</b> {timezone.localdate().strftime('%d/%m/%Y')}", styles["Normal"]))
    story.append(Spacer(1, 5 * mm))

    resumo = Table(
        [
            ["Contratos", str(ficha_cliente["total_contratos"]), "Ativos", str(ficha_cliente["contratos_ativos"])],
            ["Com alerta", str(ficha_cliente["contratos_com_alerta"]), "Follow-ups em atraso", str(ficha_cliente["followups_atrasados"])],
            ["Valor base", f"{ficha_cliente['valor_base_total']:.2f}", "Valor estimado", f"{ficha_cliente['valor_total_estimado']:.2f}"],
        ],
        colWidths=[34 * mm, 36 * mm, 46 * mm, 46 * mm],
    )
    resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(resumo)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("<b>Contactos principais</b>", styles["Heading3"]))
    contactos_texto = (
        f"Principal: {ficha_cliente.get('contacto_principal_nome') or '-'} | "
        f"{ficha_cliente.get('contacto_principal_email') or '-'} | "
        f"{ficha_cliente.get('contacto_principal_telefone') or '-'}<br/>"
        f"Secundário: {ficha_cliente.get('contacto_secundario_nome') or '-'} | "
        f"{ficha_cliente.get('contacto_secundario_email') or '-'} | "
        f"{ficha_cliente.get('contacto_secundario_telefone') or '-'}"
    )
    story.append(Paragraph(contactos_texto, styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Resumo comercial</b>", styles["Heading3"]))
    story.append(
        Paragraph(
            f"Workflows: {ficha_cliente.get('workflows_resumo') or '-'}<br/>"
            f"Próximo follow-up: {(ficha_cliente.get('proximo_followup').strftime('%d/%m/%Y') if ficha_cliente.get('proximo_followup') else '-')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Notas comerciais</b>", styles["Heading3"]))
    story.append(Paragraph((ficha_cliente.get("notas_comerciais") or "-").replace("\n", "<br/>"), styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Portfolio contratual</b>", styles["Heading3"]))
    linhas_contratos = [["Contrato", "Projeto", "Estado", "Workflow", "Fim efetivo", "Valor"]]
    for contrato in ficha_cliente["contratos"]:
        linhas_contratos.append(
            [
                contrato["numero_contrato"] or "-",
                contrato["projeto_nome"] or "-",
                contrato["status_display"] or "-",
                contrato["workflow_display"] or "-",
                contrato["data_fim_efetiva"].strftime("%d/%m/%Y") if contrato["data_fim_efetiva"] else "-",
                f"{contrato['valor_total_estimado']:.2f}",
            ]
        )
    tabela_contratos = Table(linhas_contratos, colWidths=[26 * mm, 38 * mm, 22 * mm, 30 * mm, 28 * mm, 20 * mm], repeatRows=1)
    tabela_contratos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(tabela_contratos)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Timeline comercial do cliente</b>", styles["Heading3"]))
    for evento in ficha_cliente["timeline"][:18]:
        story.append(
            Paragraph(
                f"• {evento['data'].strftime('%d/%m/%Y')} | <b>{evento['titulo']}</b> — {evento['detalhe']}",
                styles["Normal"],
            )
        )

    doc.build(story)
    pdf_bytes = output.getvalue()
    nome = f"ficha-cliente-{slugify(ficha_cliente['nome_cliente']) or 'cliente'}.pdf"
    return pdf_bytes, nome


def construir_timeline_cliente_contrato(*, cliente_contrato, anexos=None, adendas=None, workflow_historico=None):
    anexos = anexos if anexos is not None else cliente_contrato.anexos.all()
    adendas = adendas if adendas is not None else cliente_contrato.adendas.all()
    workflow_historico = (
        workflow_historico
        if workflow_historico is not None
        else cliente_contrato.historico_workflow.select_related("alterado_por").all()
    )

    timeline = [
        {
            "tipo": "contrato",
            "data": cliente_contrato.criado_em.date(),
            "titulo": "Contrato registado na plataforma",
            "detalhe": cliente_contrato.numero_contrato or cliente_contrato.nome_cliente,
        }
    ]

    if cliente_contrato.data_inicio:
        timeline.append(
            {
                "tipo": "inicio",
                "data": cliente_contrato.data_inicio,
                "titulo": "Início contratual",
                "detalhe": "Arranque formal do contrato.",
            }
        )

    if cliente_contrato.ultimo_contacto_em:
        timeline.append(
            {
                "tipo": "contacto",
                "data": cliente_contrato.ultimo_contacto_em,
                "titulo": "Último contacto comercial",
                "detalhe": cliente_contrato.contacto_nome or "Contacto registado na ficha do contrato.",
            }
        )

    if cliente_contrato.proximo_followup_em:
        timeline.append(
            {
                "tipo": "followup",
                "data": cliente_contrato.proximo_followup_em,
                "titulo": "Próximo follow-up",
                "detalhe": "Ação comercial agendada para acompanhamento.",
            }
        )

    for adenda in adendas:
        timeline.append(
            {
                "tipo": "adenda",
                "data": adenda.data_adenda,
                "titulo": adenda.titulo,
                "detalhe": adenda.descricao or adenda.get_origem_display(),
            }
        )

    for registo_workflow in workflow_historico:
        alterado_por = (
            registo_workflow.alterado_por.get_username()
            if registo_workflow.alterado_por_id and registo_workflow.alterado_por
            else "Sistema Furação"
        )
        detalhe = (
            f"{registo_workflow.get_workflow_anterior_label()} → "
            f"{registo_workflow.get_workflow_novo_label()} · {alterado_por}"
        )
        if registo_workflow.observacao:
            detalhe = f"{detalhe} · {registo_workflow.observacao}"
        timeline.append(
            {
                "tipo": "workflow",
                "data": registo_workflow.criado_em.date(),
                "titulo": "Mudança de workflow comercial",
                "detalhe": detalhe,
            }
        )

    for anexo in anexos:
        timeline.append(
            {
                "tipo": "anexo",
                "data": anexo.criado_em.date(),
                "titulo": f"Anexo: {anexo.titulo}",
                "detalhe": anexo.descricao or "Documento anexado ao contrato.",
            }
        )

    data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    if data_fim_efetiva:
        timeline.append(
            {
                "tipo": "vencimento",
                "data": data_fim_efetiva,
                "titulo": "Fim efetivo do contrato",
                "detalhe": "Data final atualmente válida para o contrato.",
            }
        )

    return sorted(timeline, key=lambda item: (item["data"], item["titulo"]), reverse=True)


def gerar_pdf_ficha_cliente_contrato(*, cliente_contrato, anexos=None, adendas=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError(
            "Exportação PDF indisponível: instala `reportlab` no ambiente (`pip install reportlab==4.2.2`)."
        ) from exc

    anexos = list(anexos if anexos is not None else cliente_contrato.anexos.all())
    adendas = list(adendas if adendas is not None else cliente_contrato.adendas.all())
    timeline = construir_timeline_cliente_contrato(cliente_contrato=cliente_contrato, anexos=anexos, adendas=adendas)
    alertas = obter_alertas_operacionais_cliente_contrato(cliente_contrato=cliente_contrato)
    data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    total_adendas = obter_total_adendas_cliente_contrato(cliente_contrato=cliente_contrato)
    valor_total = (cliente_contrato.valor_contratado or 0.0) + total_adendas

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Sistema Furação</b> | Dossiê Comercial do Contrato", styles["Title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>Cliente:</b> {cliente_contrato.nome_cliente}", styles["Heading2"]))
    story.append(Paragraph(f"<b>Contrato:</b> {cliente_contrato.numero_contrato or '-'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Estado:</b> {cliente_contrato.get_status_display()}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    tabela_resumo = Table(
        [
            ["Projeto", getattr(cliente_contrato.projeto, "nome", "-") or "-"],
            ["Cobrança", cliente_contrato.get_tipo_cobranca_display()],
            ["Valor contratado", f"{cliente_contrato.valor_contratado:.2f} {cliente_contrato.moeda}"],
            ["Total adendas", f"{total_adendas:.2f} {cliente_contrato.moeda}"],
            ["Valor total", f"{valor_total:.2f} {cliente_contrato.moeda}"],
            ["SLA", f"{cliente_contrato.sla_resposta_horas} h"],
            ["Início", cliente_contrato.data_inicio.strftime("%d/%m/%Y") if cliente_contrato.data_inicio else "-"],
            ["Fim base", cliente_contrato.data_fim.strftime("%d/%m/%Y") if cliente_contrato.data_fim else "-"],
            ["Fim efetivo", data_fim_efetiva.strftime("%d/%m/%Y") if data_fim_efetiva else "-"],
            ["Renovação automática", "Sim" if cliente_contrato.renovacao_automatica else "Não"],
        ],
        colWidths=[48 * mm, 120 * mm],
    )
    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tabela_resumo)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("<b>Contacto comercial</b>", styles["Heading3"]))
    story.append(
        Paragraph(
            (
                f"Nome: {cliente_contrato.contacto_nome or '-'}<br/>"
                f"Email: {cliente_contrato.contacto_email or '-'}<br/>"
                f"Telefone: {cliente_contrato.contacto_telefone or '-'}<br/>"
                f"Último contacto: {cliente_contrato.ultimo_contacto_em.strftime('%d/%m/%Y') if cliente_contrato.ultimo_contacto_em else '-'}<br/>"
                f"Próximo follow-up: {cliente_contrato.proximo_followup_em.strftime('%d/%m/%Y') if cliente_contrato.proximo_followup_em else '-'}"
            ),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Alertas operacionais</b>", styles["Heading3"]))
    if alertas:
        for alerta in alertas:
            story.append(Paragraph(f"• <b>{alerta['titulo']}</b>: {alerta['detalhe']}", styles["Normal"]))
    else:
        story.append(Paragraph("Sem alertas operacionais neste momento.", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Adendas</b>", styles["Heading3"]))
    if adendas:
        linhas_adenda = [["Data", "Título", "Origem", "Valor", "Nova data fim"]]
        for adenda in adendas:
            linhas_adenda.append(
                [
                    adenda.data_adenda.strftime("%d/%m/%Y"),
                    adenda.titulo,
                    adenda.get_origem_display(),
                    f"{adenda.valor_adicional:.2f} {cliente_contrato.moeda}",
                    adenda.nova_data_fim.strftime("%d/%m/%Y") if adenda.nova_data_fim else "-",
                ]
            )
        tabela_adendas = Table(linhas_adenda, colWidths=[24 * mm, 64 * mm, 36 * mm, 28 * mm, 34 * mm], repeatRows=1)
        tabela_adendas.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(tabela_adendas)
    else:
        story.append(Paragraph("Sem adendas registadas.", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Timeline comercial</b>", styles["Heading3"]))
    for evento in timeline[:12]:
        story.append(Paragraph(f"• {evento['data'].strftime('%d/%m/%Y')} | <b>{evento['titulo']}</b> — {evento['detalhe']}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("<b>Notas</b>", styles["Heading3"]))
    story.append(Paragraph((cliente_contrato.notas or "-").replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)
    return output.getvalue()


def gerar_zip_dossier_cliente_contrato(*, cliente_contrato, anexos=None, adendas=None):
    anexos = list(anexos if anexos is not None else cliente_contrato.anexos.all())
    adendas = list(adendas if adendas is not None else cliente_contrato.adendas.all())
    pdf_bytes = gerar_pdf_ficha_cliente_contrato(cliente_contrato=cliente_contrato, anexos=anexos, adendas=adendas)

    contrato_slug = slugify(cliente_contrato.numero_contrato or cliente_contrato.nome_cliente) or "contrato"
    zip_buffer = io.BytesIO()
    manifest_lines = [
        f"Cliente: {cliente_contrato.nome_cliente}",
        f"Contrato: {cliente_contrato.numero_contrato or '-'}",
        f"Projeto: {getattr(cliente_contrato.projeto, 'nome', '-') or '-'}",
        f"Estado: {cliente_contrato.get_status_display()}",
        f"Anexos: {len(anexos)}",
        f"Adendas: {len(adendas)}",
    ]

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"{contrato_slug}/00_ficha_contrato.pdf", pdf_bytes)
        zip_file.writestr(f"{contrato_slug}/01_manifesto.txt", "\n".join(manifest_lines))

        for indice, anexo in enumerate(anexos, start=1):
            nome_base = os.path.basename(anexo.ficheiro.name or f"anexo-{indice}")
            try:
                anexo.ficheiro.open("rb")
                zip_file.writestr(f"{contrato_slug}/anexos/{indice:02d}-{nome_base}", anexo.ficheiro.read())
            finally:
                try:
                    anexo.ficheiro.close()
                except Exception:
                    pass

        for indice, adenda in enumerate(adendas, start=1):
            if not adenda.ficheiro:
                continue
            nome_base = os.path.basename(adenda.ficheiro.name or f"adenda-{indice}")
            try:
                adenda.ficheiro.open("rb")
                zip_file.writestr(f"{contrato_slug}/adendas/{indice:02d}-{nome_base}", adenda.ficheiro.read())
            finally:
                try:
                    adenda.ficheiro.close()
                except Exception:
                    pass

    return zip_buffer.getvalue(), f"{contrato_slug}-dossier-comercial.zip"


def criar_cliente_contrato_anexo(*, form, cliente_contrato):
    obj = form.save(commit=False)
    obj.contrato = cliente_contrato
    obj.empresa = cliente_contrato.empresa
    obj.save()
    return obj


def apagar_cliente_contrato_anexo(*, anexo):
    anexo.delete()


def criar_cliente_contrato_adenda(*, form, cliente_contrato):
    obj = form.save(commit=False)
    obj.contrato = cliente_contrato
    obj.empresa = cliente_contrato.empresa
    if not obj.data_fim_anterior:
        obj.data_fim_anterior = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    obj.save()
    return obj


def atualizar_cliente_contrato_adenda(*, form, cliente_contrato):
    obj = form.save(commit=False)
    obj.contrato = cliente_contrato
    obj.empresa = cliente_contrato.empresa
    if not obj.data_fim_anterior:
        atual = getattr(form.instance, "data_fim_anterior", None)
        obj.data_fim_anterior = atual or cliente_contrato.data_fim
    obj.save()
    return obj


def apagar_cliente_contrato_adenda(*, adenda):
    adenda.delete()


@transaction.atomic
def processar_renovacao_automatica_cliente_contrato(*, cliente_contrato):
    if not cliente_contrato.renovacao_automatica:
        return False
    if cliente_contrato.status != "ativo":
        return False
    data_fim_base = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=cliente_contrato)
    if not data_fim_base:
        return False

    hoje = timezone.localdate()
    if data_fim_base >= hoje:
        return False

    renovado = False
    data_fim_atual = data_fim_base

    while data_fim_atual < hoje:
        nova_data_fim = adicionar_meses_data(data_fim_atual, cliente_contrato.periodo_renovacao_meses)
        ClienteContratoAdenda.objects.create(
            empresa=cliente_contrato.empresa,
            contrato=cliente_contrato,
            titulo=f"Renovação automática até {nova_data_fim:%d/%m/%Y}",
            descricao=(
                "Adenda automática gerada pela configuração de renovação do contrato "
                f"com período de {cliente_contrato.periodo_renovacao_meses} mês(es)."
            ),
            data_adenda=hoje,
            data_fim_anterior=data_fim_atual,
            nova_data_fim=nova_data_fim,
            origem="renovacao_automatica",
        )
        data_fim_atual = nova_data_fim
        renovado = True

    return renovado
