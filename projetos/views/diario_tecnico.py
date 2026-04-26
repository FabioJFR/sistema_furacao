import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from projetos.decorators import empregado_required
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto

logger = logging.getLogger("core")

# Multiempresa: o diário técnico deve ser mostrado apenas a empregados com empresa válida.

def _obter_empregado_autenticado_diario(request):
    logger.debug(
        "A resolver empregado autenticado em diario_tecnico.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, _ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em diario_tecnico.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None

@login_required
@empregado_required
def diario_tecnico(request):
    logger.info(
        "Entrada na view diario_tecnico. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_diario(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view diario_tecnico. user_id=%s", request.user.id)
        return resposta_erro

    secoes = [
        {
            "id": "introducao",
            "titulo": "Introdução ao Diamond Drilling",
            "icone": "🛠️",
            "conteudo": [
                "O diamond drilling tem como objetivo recuperar testemunho (core) com boa qualidade e boa produtividade.",
                "A escolha correta da broca, da matriz e dos parâmetros de perfuração tem impacto direto na penetração, recuperação e vida útil do equipamento.",
                "Um ajudante novo deve aprender primeiro os nomes dos componentes, os diâmetros usados e os cuidados de segurança e manutenção."
            ]
        },
        {
            "id": "diametros",
            "titulo": "Diâmetros mais comuns",
            "icone": "📏",
            "conteudo": [
                "AQ – série pequena para testemunho mais fino.",
                "BQ – série pequena/média, usada em alguns trabalhos mais leves.",
                "NQ – uma das séries mais comuns em exploração.",
                "HQ – muito comum quando se pretende melhor recuperação e testemunho maior.",
                "PQ – usada quando se quer testemunho maior e melhor recuperação, mas com maior custo e esforço do equipamento.",
                "Também existem variantes como NQ2, NQ3, HQ3 e PQ3, dependendo do sistema e do tipo de core barrel."
            ]
        },
        {
            "id": "brocas",
            "titulo": "Brocas (Bits)",
            "icone": "🧱",
            "conteudo": [
                "A escolha da broca depende da dureza da rocha, abrasividade, fraturação, profundidade esperada e tipo de perfuradora.",
                "A dureza da rocha pode ser avaliada com base na escala de Mohs e em scratch test.",
                "Usar a broca errada pode provocar baixa penetração, desgaste prematuro e perda de produtividade.",
                "Exemplos de famílias mostradas nos teus documentos: HERO, HERO Abrasive, T Xtreme, Rock Star, Azure, Ferro, Kuby, Lava e Kraken."
            ]
        },
        {
            "id": "matrizes",
            "titulo": "Seleção de Matrizes",
            "icone": "🧪",
            "conteudo": [
                "As matrizes são escolhidas conforme a dureza e comportamento do terreno.",
                "Nos teus PDFs aparecem matrizes para terrenos brandos, médios, duros e muito duros.",
                "Em terrenos abrasivos, há linhas desenvolvidas especificamente para resistir melhor ao desgaste, como a HERO Abrasive.",
                "A tabela de seleção de matrizes deve ficar visível nesta página como referência rápida para o sondador."
            ]
        },
        {
            "id": "configuracoes",
            "titulo": "Configuração das Brocas",
            "icone": "🌊",
            "conteudo": [
                "A configuração da broca inclui número, forma e largura das waterways.",
                "Existem configurações como standard, pie shaped, turbo pie shaped, cyclone, lateral discharge, deep lateral discharge e face discharge.",
                "Em terreno fraturado ou brando, waterways mais largas e com boa evacuação ajudam a reduzir problemas de lavagem do core e acumulação de cuttings.",
                "Em terreno duro e competente, waterways mais estreitas podem funcionar melhor com maior pressão e melhor arrefecimento na face da broca."
            ]
        },
        {
            "id": "parametros",
            "titulo": "Parâmetros de Perfuração",
            "icone": "📊",
            "conteudo": [
                "ROP (Rate of Penetration) é a velocidade a que a broca avança na rocha.",
                "RPM é a rotação da coluna/broca.",
                "WOB (Weight on Bit) é o peso aplicado sobre a broca.",
                "Fluxo de água é essencial para arrefecer a broca e evacuar os cuttings.",
                "Todos estes parâmetros estão ligados entre si: alterar um influencia os outros."
            ]
        },
        {
            "id": "vida_broca",
            "titulo": "Como aumentar a vida útil da broca",
            "icone": "⏳",
            "conteudo": [
                "Escolher corretamente a matriz para o terreno.",
                "Usar a configuração adequada de waterways.",
                "Garantir fluxo de água suficiente.",
                "Evitar queimar a broca com parâmetros errados.",
                "Monitorizar desgaste e fazer afiação/ajustes quando necessário."
            ]
        },
        {
            "id": "rods",
            "titulo": "Cuidados com os Drill Rods",
            "icone": "🔩",
            "conteudo": [
                "Limpar sempre as roscas antes de ligar os rods.",
                "Não usar rods com roscas danificadas.",
                "Aplicar composto/lubrificante adequado nas roscas.",
                "Evitar pancadas entre rods durante transporte e armazenamento.",
                "Rods com fugas reduzem pressão e fluxo de água para a broca, prejudicando a perfuração."
            ]
        },
        {
            "id": "seguranca",
            "titulo": "Segurança e boas práticas",
            "icone": "⛑️",
            "conteudo": [
                "Usar sempre EPI adequado.",
                "Nunca aproximar mãos ou roupa de partes em rotação.",
                "Conferir mangueiras, água, fixações e área de trabalho antes de iniciar.",
                "Manter zona de rods organizada e limpa.",
                "Comunicar sempre com o sondador antes de qualquer intervenção."
            ]
        },
        {
            "id": "videos",
            "titulo": "Vídeos e recursos",
            "icone": "🎥",
            "conteudo": [
                "Nesta primeira versão, esta secção fica preparada para adicionares links de YouTube, Vimeo ou vídeos internos.",
                "Também vamos poder associar PDFs, imagens de bits, componentes e notas internas da empresa."
            ]
        },
    ]

    referencias = [
        {
            "titulo": "Como escolher a broca correta",
            "arquivo": "Epiroc Guia - Exploracion minera - Como elegir la broca correcta.pdf",
            "resumo": "Escolha da broca com base em dureza, abrasividade, tipo de rocha e configuração."
        },
        {
            "titulo": "Seleção de matrizes",
            "arquivo": "Seleccion de matrices.pdf",
            "resumo": "Tabela visual de matrizes e famílias de brocas por dureza do terreno."
        },
        {
            "titulo": "Aumentar a vida útil da broca",
            "arquivo": "Epiroc guide Extending core bit life.pdf",
            "resumo": "Boas práticas para aumentar a vida útil da broca e reduzir paragens."
        },
        {
            "titulo": "Proteger e manusear os drill rods",
            "arquivo": "Epiroc Guide Protecting and Handling your Drill Rods.pdf",
            "resumo": "Cuidados com roscas, limpeza, fugas e lubrificação."
        },
        {
            "titulo": "Parâmetros de perfuração",
            "arquivo": "Epiroc Guide to Drilling Parameters.pdf",
            "resumo": "ROP, RPM, fluxo de água, WOB e interações entre parâmetros."
        },
        {
            "titulo": "Melhorar a taxa de penetração",
            "arquivo": "Epiroc Guide to improving rate of penetration.pdf",
            "resumo": "Como melhorar produtividade através de escolha de broca, configuração e parâmetros."
        },
    ]

    context = {
        "empregado": empregado,
        "secoes": secoes,
        "referencias": referencias,
    }
    logger.info(
        "View diario_tecnico carregada com sucesso. user_id=%s, empregado_id=%s, total_secoes=%s, total_referencias=%s",
        request.user.id,
        empregado.id,
        len(secoes),
        len(referencias),
    )
    return render(request, "projetos/diario_tecnico.html", context)
