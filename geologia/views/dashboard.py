from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core.permissions import (
    admin_required,
    encarregado_obra_required,
    geologia_operacional_required,
    geologo_required,
)
from geologia.forms import (
    ConfiguracaoDroneSFForm,
    DroneSFForm,
    FonteCartograficaGeologicaForm,
    MissaoProgramadaDroneSFForm,
    ModuloDroneSFForm,
    OperacaoDroneSFTempoRealForm,
    SensorDroneSFForm,
)
from geologia.models import FonteCartograficaGeologica
from geologia.services.drone_sf_dashboard import (
    bridge_logs_context_sf,
    bridge_status_summary_sf,
    construir_missoes_programadas_contexto,
    confirmar_comando_bridge_sf,
    construir_form_comando_sf,
    criar_ou_obter_drone_sf_demo,
    motor_missoes_summary_sf,
    processar_comandos_pendentes_bridge_sf,
    processar_ingest_estado_bridge_sf,
    processar_log_event_bridge_sf,
    processar_form_modelo_sf,
    processar_execucao_missao_programada_sf,
    processar_remocao_missao_programada_sf,
    processar_toggle_missao_programada_sf,
    serializar_estado_operacao_sf,
)
from geologia.services.hub_page import (
    construir_contexto_drone_sf_hub,
    construir_contexto_geologia_hub,
)
from geologia.services.drone_sf_page import (
    processar_acao_missao_programada_sf,
    processar_fluxo_form_modelo_sf,
    processar_post_comando_sf,
    processar_post_operacao_detail_sf,
    resolver_contexto_bridge_sf,
)
from geologia.selectors.dashboard import (
    obter_comando_sf_operacao,
    obter_comandos_recentes_operacao_sf,
    obter_drone_sf,
    obter_drone_sf_simples,
    obter_furo_geologia_dashboard,
    obter_logs_furo_geologia,
    obter_missao_programada_drone_sf,
    obter_missoes_furo_geologia,
    obter_operacao_drone_sf,
    obter_operacao_sf_por_bridge_key,
    obter_ou_criar_configuracao_drone_sf,
    obter_ou_criar_operacao_drone_sf,
    obter_furos_geologia_hub_qs,
    obter_logs_geologia_hub_qs,
    obter_missoes_geologia_hub_qs,
    obter_semoforo_e_prioridades_furos_geologo,
)
from projetos.selectors.acesso import obter_empregado_por_user

from .common import obter_empresa_admin_geologia, obter_empresa_geologia_operacional


def _json_ok(payload=None, *, status=200):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def _json_erro(*, erro, status=400):
    return JsonResponse({"ok": False, "erro": erro}, status=status)


def _processar_post_form_modelo(
    *,
    request,
    form,
    mensagem_sucesso,
    mensagem_erro,
    redirect_name,
    redirect_kwargs,
):
    if request.method != "POST":
        return None
    resultado = processar_form_modelo_sf(
        form=form,
        mensagem_sucesso=mensagem_sucesso,
        mensagem_erro=mensagem_erro,
    )
    if resultado["ok"]:
        messages.success(request, resultado["mensagem"])
        return redirect(redirect_name, **redirect_kwargs)
    messages.error(request, resultado["mensagem"])
    return None


def _mensagem_sucesso_redirect(*, request, mensagem, redirect_name, **redirect_kwargs):
    messages.success(request, mensagem)
    return redirect(redirect_name, **redirect_kwargs)


def _fontes_cartograficas_padrao():
    return [
        {
            "id": "lneg-cgp1m-mapa",
            "nome": "LNEG · 1:1 000 000 · Mapa geológico",
            "descricao": "Carta geológica nacional em mosaico cacheado, estável para visualização direta dentro da plataforma.",
            "pais_regiao": "Portugal",
            "tipo_servico": "tile",
            "url_servico": "https://sig.lneg.pt/server/rest/services/CGP1M/MapServer/tile/{z}/{y}/{x}",
            "layer_names": "",
            "attribution": "Fonte: LNEG · CGP1M",
            "formato_imagem": "",
            "transparencia": False,
            "opacidade": 0.92,
            "centro_latitude": 39.5,
            "centro_longitude": -8.0,
            "zoom_inicial": 6,
            "visivel_por_defeito": True,
            "origem": "padrao",
            "identify_mode": "query",
            "identify_url": "https://sig.lneg.pt/server/rest/services/CGP1M/MapServer/2/query",
            "identify_title": "Carta Geológica de Portugal, escala 1:1 000 000",
            "identify_hint": "Geologia vetorial: identifica a unidade geológica no ponto.",
            "identify_fields": [
                {"key": "Codigo", "label": "Código"},
                {"key": "UC_desc", "label": "Descrição"},
                {"key": "Zona_TE", "label": "Zona Tectono-Estratigráfica"},
                {"key": "Eonotema", "label": "Eonotema"},
                {"key": "Eratema", "label": "Eratema"},
                {"key": "Sistema", "label": "Sistema"},
                {"key": "Serie", "label": "Série"},
                {"key": "LitologiasPredominantes", "label": "Litologias predominantes"},
            ],
            "external_url": "https://geoportal.lneg.pt/mapa/?mapa=CGP1M",
        },
        {
            "id": "lneg-cgp500k-mapa",
            "nome": "LNEG · 1:500 000 · Mapa geológico",
            "descricao": "Carta geológica vetorial intermédia, útil para leitura regional mais fina.",
            "pais_regiao": "Portugal",
            "tipo_servico": "tile",
            "url_servico": "https://sig.lneg.pt/server/rest/services/CGP500k/MapServer/tile/{z}/{y}/{x}",
            "layer_names": "",
            "attribution": "Fonte: LNEG · CGP500k",
            "formato_imagem": "",
            "transparencia": False,
            "opacidade": 0.88,
            "centro_latitude": 39.5,
            "centro_longitude": -8.0,
            "zoom_inicial": 7,
            "visivel_por_defeito": False,
            "origem": "padrao",
            "identify_mode": "query",
            "identify_url": "https://sig.lneg.pt/server/rest/services/CGP500k/MapServer/2/query",
            "identify_title": "Carta Geológica de Portugal, escala 1:500 000",
            "identify_hint": "Geologia vetorial: identifica a unidade geológica no ponto.",
            "external_url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp500k/",
        },
        {
            "id": "lneg-cgp200k-mapa",
            "nome": "LNEG · 1:200 000 · Mapa geológico",
            "descricao": "Mosaico raster 1:200 000 para enquadramento técnico regional.",
            "pais_regiao": "Portugal",
            "tipo_servico": "tile",
            "url_servico": "https://sig.lneg.pt/server/rest/services/CGP200k/MapServer/tile/{z}/{y}/{x}",
            "layer_names": "",
            "attribution": "Fonte: LNEG · CGP200k",
            "formato_imagem": "",
            "transparencia": False,
            "opacidade": 0.9,
            "centro_latitude": 39.5,
            "centro_longitude": -8.0,
            "zoom_inicial": 9,
            "visivel_por_defeito": False,
            "origem": "padrao",
            "identify_mode": "multi_query",
            "identify_urls": [
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/2/query",
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/3/query",
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/5/query",
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/7/query",
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/8/query",
                "https://sig.lneg.pt/server/rest/services/CGP200k_vetor/MapServer/9/query",
            ],
            "identify_title": "Carta Geológica de Portugal, escala 1:200 000",
            "identify_hint": "Geologia vetorial: identifica a unidade geológica no ponto.",
            "identify_fields": [
                {"key": "CODIGO", "label": "Código"},
                {"key": "UnidadeGeologica", "label": "Unidade geológica"},
                {"key": "Eonotema", "label": "Eonotema"},
                {"key": "Eratema", "label": "Eratema"},
                {"key": "Sistema", "label": "Sistema"},
                {"key": "Série", "label": "Série"},
                {"key": "Andar", "label": "Andar"},
            ],
            "external_url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp200k/",
        },
        {
            "id": "lneg-cgp25k-folhas",
            "nome": "LNEG · 1:25 000 · Índice de folhas publicadas",
            "descricao": "Índice documental de folhas e metadados públicos na escala 1:25 000, útil para localizar rapidamente a publicação mais próxima do projeto.",
            "pais_regiao": "Portugal",
            "tipo_servico": "wms",
            "url_servico": "https://sig.lneg.pt/server/services/geoPortal/CartografiaOficial/MapServer/WMSServer",
            "layer_names": "1",
            "attribution": "Fonte: LNEG · Cartografia Oficial",
            "formato_imagem": "image/png",
            "transparencia": True,
            "opacidade": 0.58,
            "centro_latitude": 39.5,
            "centro_longitude": -8.0,
            "zoom_inicial": 14,
            "visivel_por_defeito": False,
            "origem": "padrao",
            "identify_mode": "query",
            "identify_url": "https://sig.lneg.pt/server/rest/services/geoPortal/CartografiaOficial/MapServer/1/query",
            "identify_title": "Cartografia oficial publicada, escala 1:25 000",
            "identify_badge": "Camada documental",
            "identify_hint": "Camada documental: identifica a folha publicada e a documentação disponível.",
            "identify_fields": [
                {"key": "Codigo", "label": "Código"},
                {"key": "Nome", "label": "Folha"},
                {"key": "Ano", "label": "Ano"},
                {"key": "Autores", "label": "Autores"},
                {"key": "Edicao", "label": "Edição"},
                {"key": "Papel", "label": "Formato papel"},
                {"key": "Digital", "label": "Formato digital"},
                {"key": "Nota", "label": "Notícia explicativa"},
                {"key": "Nota_Autor", "label": "Autor da notícia"},
                {"key": "Nota_Ano", "label": "Ano da notícia"},
                {"key": "Nota_Paginas", "label": "Páginas da notícia"},
            ],
            "external_url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/",
        },
        {
            "id": "lneg-cgp50k-mapa",
            "nome": "LNEG · 1:50 000 · Mapa geológico",
            "descricao": "Mosaico raster de maior detalhe entre as cartas nacionais base aqui disponíveis.",
            "pais_regiao": "Portugal",
            "tipo_servico": "tile",
            "url_servico": "https://sig.lneg.pt/server/rest/services/CGP50k/MapServer/tile/{z}/{y}/{x}",
            "layer_names": "",
            "attribution": "Fonte: LNEG · CGP50k",
            "formato_imagem": "",
            "transparencia": False,
            "opacidade": 0.9,
            "centro_latitude": 39.5,
            "centro_longitude": -8.0,
            "zoom_inicial": 12,
            "visivel_por_defeito": False,
            "origem": "padrao",
            "identify_mode": "query",
            "identify_url": "https://sig.lneg.pt/server/rest/services/geoPortal/CartografiaOficial/MapServer/2/query",
            "identify_title": "Carta Geológica de Portugal, escala 1:50 000",
            "identify_badge": "Folha publicada",
            "identify_hint": "Folha publicada: identifica a folha oficial e os respetivos metadados.",
            "identify_fields": [
                {"key": "Codigo", "label": "Código"},
                {"key": "Nome", "label": "Folha"},
                {"key": "Ano", "label": "Ano"},
                {"key": "Autores", "label": "Autores"},
                {"key": "Edicao", "label": "Edição"},
                {"key": "Papel", "label": "Formato papel"},
                {"key": "Digital", "label": "Formato digital"},
                {"key": "Nota", "label": "Notícia explicativa"},
                {"key": "Nota_Autor", "label": "Autor da notícia"},
                {"key": "Nota_Ano", "label": "Ano da notícia"},
                {"key": "Nota_Paginas", "label": "Páginas da notícia"},
            ],
            "external_url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp50k/",
        },
    ]


def _serializar_fonte_cartografica_modelo(fonte):
    return {
        "id": str(fonte.id),
        "nome": fonte.nome,
        "descricao": fonte.descricao,
        "pais_regiao": fonte.pais_regiao,
        "tipo_servico": fonte.tipo_servico,
        "url_servico": fonte.url_servico,
        "layer_names": fonte.layer_names,
        "attribution": fonte.attribution,
        "formato_imagem": fonte.formato_imagem or "image/png",
        "transparencia": fonte.transparencia,
        "opacidade": fonte.opacidade,
        "centro_latitude": fonte.centro_latitude,
        "centro_longitude": fonte.centro_longitude,
        "zoom_inicial": fonte.zoom_inicial,
        "visivel_por_defeito": fonte.visivel_por_defeito,
        "origem": "empresa",
    }


def _obter_fontes_cartograficas_contexto(*, empresa):
    fontes_empresa = [
        _serializar_fonte_cartografica_modelo(item)
        for item in FonteCartograficaGeologica.objects.filter(empresa=empresa, ativo=True).order_by("ordem", "nome")
    ]
    return _fontes_cartograficas_padrao() + fontes_empresa, fontes_empresa


def _obter_fonte_cartografica_empresa(*, pk, empresa):
    try:
        return FonteCartograficaGeologica.objects.get(pk=pk, empresa=empresa)
    except FonteCartograficaGeologica.DoesNotExist as exc:
        raise FonteCartograficaGeologica.DoesNotExist from exc


def _cartografia_oficial_contexto():
    return {
        "titulo": "Cartografia oficial",
        "subtitulo": "Acesso rápido à cartografia geológica pública do LNEG, organizada por escala e utilidade prática para enquadramento regional, análise intermédia e leitura mais próxima do projeto.",
        "alerta_escala": "As escalas pequenas são excelentes para contexto regional. Para interpretação local, a plataforma deve continuar a privilegiar o detalhe do furo, das amostras, dos logs e da cartografia de maior resolução.",
        "atalhos_rapidos": [
            {
                "titulo": "Centro de cartografia geológica",
                "descricao": "Visão geral do catálogo de cartografia geológica aberta do LNEG.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/",
                "etiqueta": "Abrir catálogo",
            },
            {
                "titulo": "WMS oficial 1:1 000 000",
                "descricao": "Ligação preparada para futura integração cartográfica na plataforma.",
                "url": "https://sig.lneg.pt/server/services/CGP1M/MapServer/WMSServer?request=GetCapabilities&service=WMS",
                "etiqueta": "Abrir WMS",
            },
            {
                "titulo": "Serviço REST oficial 1:1 000 000",
                "descricao": "Página técnica do serviço, útil para ver layers, cache e operações do mapa.",
                "url": "https://sig.lneg.pt/server/rest/services/CGP1M/MapServer",
                "etiqueta": "Abrir REST",
            },
        ],
        "colecoes": [
            {
                "titulo": "Escala 1:1 000 000",
                "descricao": "Síntese nacional útil para enquadramento geológico macro e leitura regional do território.",
                "utilidade": "Ideal para contexto nacional e alinhamento inicial do projeto.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp1m/",
                "fontes": [
                    "Metadados",
                    "JPG/PDF",
                    "Shapefile",
                    "GeoPackage",
                    "WMS/WMTS",
                ],
            },
            {
                "titulo": "Escala 1:500 000",
                "descricao": "Referência intermédia publicada pelos Serviços Geológicos de Portugal, útil para leitura regional alargada.",
                "utilidade": "Boa para transição entre visão nacional e análise regional.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp500k/",
                "fontes": [
                    "Metadados",
                    "JPG/PDF",
                    "Folha Norte",
                    "Folha Sul",
                ],
            },
            {
                "titulo": "Escala 1:200 000",
                "descricao": "Informação geológica mais detalhada, com folhas publicadas e notícias explicativas em vários casos.",
                "utilidade": "Muito útil para enquadramento regional técnico antes de abrir o detalhe do furo.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp200k/",
                "fontes": [
                    "Metadados",
                    "JPG/PDF",
                    "Raster georreferenciado",
                    "Notícia explicativa",
                ],
            },
            {
                "titulo": "Escala 1:25 000",
                "descricao": "Folhas publicadas de detalhe local, úteis para localizar rapidamente a cartografia oficial mais próxima e a respetiva documentação associada.",
                "utilidade": "Boa para consulta fina de publicação disponível e enquadramento documental local.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/",
                "fontes": [
                    "Metadados",
                    "Folhas publicadas",
                    "Notícia explicativa",
                    "Autores e edição",
                ],
            },
            {
                "titulo": "Escala 1:50 000",
                "descricao": "Cartografia geológica de base do território nacional, dividida por folhas e com georreferenciação melhorada em PT-TM06/ETRS89 em junho de 2024.",
                "utilidade": "A escala mais relevante deste conjunto para aproximação ao contexto local do projeto.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cgp50k/",
                "fontes": [
                    "PDF",
                    "Raster georreferenciado",
                    "Notícia explicativa",
                    "Folhas locais",
                ],
            },
            {
                "titulo": "Açores",
                "descricao": "Cartas geológicas de várias ilhas, com escalas 1:25 000 e 1:50 000 conforme a ilha.",
                "utilidade": "Essencial para operação e estudo em contexto insular açoriano.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cartografia_geologica_acores/",
                "fontes": [
                    "Metadados",
                    "JPG/PDF",
                    "Notícia explicativa",
                    "Folhas por ilha",
                ],
            },
            {
                "titulo": "Madeira",
                "descricao": "Cartas geológicas da Madeira, Porto Santo, Desertas e Selvagens, com escalas 1:25 000 e 1:50 000.",
                "utilidade": "Útil para contexto geológico regional insular e apoio a estudos locais.",
                "url": "https://geoportal.lneg.pt/pt/dados_abertos/cartografia_geologica/cartografia_geologica_madeira/",
                "fontes": [
                    "Metadados",
                    "JPG/PDF",
                    "Notícia explicativa",
                    "Folhas por ilha",
                ],
            },
        ],
        "proximos_passos": [
            "Ligar o WMS/WMTS ao mapa geológico da plataforma.",
            "Permitir abrir a folha oficial adequada a partir do projeto ou do furo ativo.",
            "Sugerir a escala mais útil com base na localização e no contexto do projeto.",
            "Cruzar o enquadramento regional com logs, litologia e modelos 3D.",
        ],
    }


@login_required
@admin_required
def geologia_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    return render(
        request,
        "geologia/hub.html",
        construir_contexto_geologia_hub(empresa=empresa, contexto_geologia=contexto_geologia),
    )


@login_required
@geologo_required
def geologia_geologo_dashboard(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para aceder à geologia.")
        return redirect("projetos:area_empregado")

    empresa = empregado.empresa
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)
    semaforo_furos, top_prioritarios, metadados_score = obter_semoforo_e_prioridades_furos_geologo(
        empresa=empresa,
        limite_top=5,
    )
    fontes_mapa, fontes_empresa = _obter_fontes_cartograficas_contexto(empresa=empresa)

    return render(
        request,
        "geologia/empregado_geologo_dashboard.html",
        {
            "empregado": empregado,
            "empresa_geologia": empresa,
            "furos": furos_qs[:12],
            "logs_recentes": logs_qs[:8],
            "missoes_recentes": missoes_qs[:6],
            "total_furos": furos_qs.count(),
            "total_logs": logs_qs.count(),
            "total_missoes": missoes_qs.count(),
            "semaforo_furos": semaforo_furos,
            "top_furos_prioritarios": top_prioritarios,
            "metadados_score": metadados_score,
            "cartografia_oficial": _cartografia_oficial_contexto(),
            "fontes_cartograficas_mapa": fontes_mapa,
            "fontes_cartograficas_empresa": fontes_empresa,
        },
    )


@login_required
@encarregado_obra_required
def geologia_encarregado_dashboard(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para aceder à geologia.")
        return redirect("projetos:area_empregado")

    empresa = empregado.empresa
    furos_qs = obter_furos_geologia_hub_qs(empresa=empresa)
    logs_qs = obter_logs_geologia_hub_qs(empresa=empresa)
    missoes_qs = obter_missoes_geologia_hub_qs(empresa=empresa)
    fontes_mapa, fontes_empresa = _obter_fontes_cartograficas_contexto(empresa=empresa)

    return render(
        request,
        "geologia/empregado_encarregado_dashboard.html",
        {
            "empregado": empregado,
            "empresa_geologia": empresa,
            "furos": furos_qs[:12],
            "logs_recentes": logs_qs[:6],
            "missoes_recentes": missoes_qs[:6],
            "total_furos": furos_qs.count(),
            "total_logs": logs_qs.count(),
            "total_missoes": missoes_qs.count(),
            "cartografia_oficial": _cartografia_oficial_contexto(),
            "fontes_cartograficas_mapa": fontes_mapa,
            "fontes_cartograficas_empresa": fontes_empresa,
        },
    )


@login_required
@geologia_operacional_required
def cartografia_oficial(request):
    empresa, _, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    return render(
        request,
        "geologia/cartografia_oficial.html",
        {
            "empresa_geologia": empresa,
            "cartografia_oficial": _cartografia_oficial_contexto(),
        },
    )


@login_required
@geologia_operacional_required
def mapa_cartografico(request):
    empresa, _, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    fontes_mapa, fontes_empresa = _obter_fontes_cartograficas_contexto(empresa=empresa)

    return render(
        request,
        "geologia/mapa_cartografico.html",
        {
            "empresa_geologia": empresa,
            "fontes_cartograficas_mapa": fontes_mapa,
            "fontes_cartograficas_empresa": fontes_empresa,
            "fontes_cartograficas_padrao_total": len(_fontes_cartograficas_padrao()),
        },
    )


@login_required
@geologo_required
def fonte_cartografica_create(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    form = FonteCartograficaGeologicaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        fonte = form.save(commit=False)
        fonte.empresa = empregado.empresa
        fonte.criado_por = request.user
        fonte.save()
        messages.success(request, "Fonte cartográfica adicionada com sucesso.")
        return redirect("geologia:mapa_cartografico")

    return render(
        request,
        "geologia/fonte_cartografica_form.html",
        {
            "empresa_geologia": empregado.empresa,
            "form": form,
            "titulo": "Adicionar mapa cartográfico",
            "subtitulo": "Regista uma nova fonte cartográfica privada da empresa para aparecer no mapa interno da geologia.",
            "url_cancelar": "geologia:fontes_cartograficas_manage",
        },
    )


@login_required
@geologo_required
def fontes_cartograficas_manage(request):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    fontes_empresa = FonteCartograficaGeologica.objects.filter(empresa=empregado.empresa).order_by("ordem", "nome")
    return render(
        request,
        "geologia/fontes_cartograficas_manage.html",
        {
            "empresa_geologia": empregado.empresa,
            "fontes_empresa": fontes_empresa,
            "fontes_empresa_preview": [_serializar_fonte_cartografica_modelo(item) for item in fontes_empresa],
            "total_fontes_ativas": fontes_empresa.filter(ativo=True).count(),
        },
    )


@login_required
@geologo_required
def fonte_cartografica_update(request, pk):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    try:
        fonte = _obter_fonte_cartografica_empresa(pk=pk, empresa=empregado.empresa)
    except FonteCartograficaGeologica.DoesNotExist:
        messages.error(request, "A fonte cartográfica pedida não pertence à tua empresa.")
        return redirect("geologia:fontes_cartograficas_manage")

    form = FonteCartograficaGeologicaForm(request.POST or None, instance=fonte)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fonte cartográfica atualizada com sucesso.")
        return redirect("geologia:fontes_cartograficas_manage")

    return render(
        request,
        "geologia/fonte_cartografica_form.html",
        {
            "empresa_geologia": empregado.empresa,
            "form": form,
            "fonte": fonte,
            "titulo": "Editar mapa cartográfico",
            "subtitulo": "Atualiza uma fonte cartográfica privada da tua empresa.",
            "url_cancelar": "geologia:fontes_cartograficas_manage",
        },
    )


@login_required
@geologo_required
@require_POST
def fonte_cartografica_toggle(request, pk):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    try:
        fonte = _obter_fonte_cartografica_empresa(pk=pk, empresa=empregado.empresa)
    except FonteCartograficaGeologica.DoesNotExist:
        messages.error(request, "A fonte cartográfica pedida não pertence à tua empresa.")
        return redirect("geologia:fontes_cartograficas_manage")

    fonte.ativo = not fonte.ativo
    fonte.save(update_fields=["ativo", "atualizado_em"])
    messages.success(
        request,
        "Fonte cartográfica ativada com sucesso." if fonte.ativo else "Fonte cartográfica desativada com sucesso.",
    )
    return redirect("geologia:fontes_cartograficas_manage")


@login_required
@geologo_required
@require_POST
def fonte_cartografica_duplicate(request, pk):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    try:
        fonte = _obter_fonte_cartografica_empresa(pk=pk, empresa=empregado.empresa)
    except FonteCartograficaGeologica.DoesNotExist:
        messages.error(request, "A fonte cartográfica pedida não pertence à tua empresa.")
        return redirect("geologia:fontes_cartograficas_manage")

    copia = FonteCartograficaGeologica(
        empresa=empregado.empresa,
        criado_por=request.user,
        nome=f"{fonte.nome} (cópia)",
        descricao=fonte.descricao,
        pais_regiao=fonte.pais_regiao,
        tipo_servico=fonte.tipo_servico,
        url_servico=fonte.url_servico,
        layer_names=fonte.layer_names,
        attribution=fonte.attribution,
        formato_imagem=fonte.formato_imagem,
        transparencia=fonte.transparencia,
        opacidade=fonte.opacidade,
        centro_latitude=fonte.centro_latitude,
        centro_longitude=fonte.centro_longitude,
        zoom_inicial=fonte.zoom_inicial,
        visivel_por_defeito=False,
        ativo=False,
        ordem=fonte.ordem,
    )
    copia.save()
    messages.success(request, f"Fonte cartográfica duplicada com sucesso: {copia.nome}.")
    return redirect("geologia:fonte_cartografica_update", pk=copia.pk)


@login_required
@geologo_required
@require_POST
def fonte_cartografica_delete(request, pk):
    empregado = obter_empregado_por_user(request.user)
    if not empregado or not empregado.empresa_id:
        messages.error(request, "A tua conta não está ligada a uma empresa para gerir fontes cartográficas.")
        return redirect("projetos:area_empregado")

    try:
        fonte = _obter_fonte_cartografica_empresa(pk=pk, empresa=empregado.empresa)
    except FonteCartograficaGeologica.DoesNotExist:
        messages.error(request, "A fonte cartográfica pedida não pertence à tua empresa.")
        return redirect("geologia:fontes_cartograficas_manage")

    nome = fonte.nome
    fonte.delete()
    messages.success(request, f"Fonte cartográfica '{nome}' apagada com sucesso.")
    return redirect("geologia:fontes_cartograficas_manage")


@login_required
@admin_required
def drone_sf_hub(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    return render(
        request,
        "geologia/drone_sf_hub.html",
        construir_contexto_drone_sf_hub(empresa=empresa, contexto_geologia=contexto_geologia),
    )


@login_required
@admin_required
@require_POST
def drone_sf_demo_create(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro
    if empresa is None:
        messages.error(request, "Seleciona uma empresa antes de criar o Drone S_F demo.")
        return redirect("geologia:drone_sf_hub")

    drone = criar_ou_obter_drone_sf_demo(empresa=empresa)
    messages.success(request, "Drone S_F demo preparado com sucesso.")
    return redirect("geologia:drone_sf_detail", pk=drone.pk)


@login_required
@admin_required
def drone_sf_create(request):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    form = DroneSFForm(request.POST or None, empresa=empresa)
    fluxo = processar_fluxo_form_modelo_sf(
        method=request.method,
        form=form,
        processar_form_modelo_sf_fn=processar_form_modelo_sf,
        mensagem_sucesso="Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o Drone S_F.",
    )
    if fluxo["handled"]:
        if fluxo["ok"]:
            messages.success(request, fluxo["mensagem"])
            return redirect("geologia:drone_sf_detail", pk=fluxo["objeto"].pk)
        messages.error(request, fluxo["mensagem"])

    return render(
        request,
        "geologia/drone_sf_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "titulo": "Novo Drone S_F",
            "subtitulo": "Criar a base do drone próprio da plataforma.",
        },
    )


@login_required
@admin_required
def drone_sf_detail(request, pk):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf(pk=pk, empresa=empresa)
    configuracao, _ = obter_ou_criar_configuracao_drone_sf(drone)
    config_form = ConfiguracaoDroneSFForm(
        request.POST or None,
        instance=configuracao,
        drone=drone,
        empresa=drone.empresa,
    )
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=config_form,
        mensagem_sucesso="Configuração do Drone S_F atualizada.",
        mensagem_erro="Não foi possível atualizar a configuração do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

    return render(
        request,
        "geologia/drone_sf_detail.html",
        {
            "drone": drone,
            "configuracao": configuracao,
            "config_form": config_form,
            "empresa_geologia": empresa,
        },
    )


@login_required
@admin_required
def drone_sf_modulo_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    form = ModuloDroneSFForm(request.POST or None, drone=drone, empresa=drone.empresa)
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=form,
        mensagem_sucesso="Módulo do Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o módulo do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

    return render(
        request,
        "geologia/drone_sf_item_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "drone": drone,
            "titulo": f"Novo módulo - {drone.nome}",
            "subtitulo": "Componentes principais do drone, como estrutura, propulsão, computação e comunicação.",
            "botao_label": "Guardar módulo",
        },
    )


@login_required
@admin_required
def drone_sf_sensor_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    form = SensorDroneSFForm(request.POST or None, drone=drone, empresa=drone.empresa)
    resposta_post = _processar_post_form_modelo(
        request=request,
        form=form,
        mensagem_sucesso="Sensor do Drone S_F criado com sucesso.",
        mensagem_erro="Não foi possível criar o sensor do Drone S_F.",
        redirect_name="geologia:drone_sf_detail",
        redirect_kwargs={"pk": drone.pk},
    )
    if resposta_post:
        return resposta_post

    return render(
        request,
        "geologia/drone_sf_item_form.html",
        {
            "form": form,
            "empresa_geologia": empresa,
            "drone": drone,
            "titulo": f"Novo sensor - {drone.nome}",
            "subtitulo": "Sensores de proximidade, som, RGB e outros módulos de leitura do Drone S_F.",
            "botao_label": "Guardar sensor",
        },
    )


@login_required
@admin_required
def drone_sf_operacao_detail(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao_edicao = None
    missao_edicao_id = request.GET.get("editar_missao") or request.POST.get("missao_programada_id")
    if missao_edicao_id:
        missao_edicao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_edicao_id)
    operacao, _ = obter_ou_criar_operacao_drone_sf(drone)
    operacao_form = OperacaoDroneSFTempoRealForm(
        request.POST or None,
        instance=operacao,
        drone=drone,
        empresa=drone.empresa,
        prefix="operacao_sf",
    )
    comando_form = construir_form_comando_sf(
        operacao=operacao,
        empresa=drone.empresa,
    )
    missao_programada_form = MissaoProgramadaDroneSFForm(
        request.POST or None,
        instance=missao_edicao,
        prefix="missao_sf",
        drone=drone,
        empresa=drone.empresa,
        initial={
            "nome": f"Missão diária {drone.nome}",
            "tipo_frequencia": "diaria",
            "hora_execucao": "08:00",
            "latitude_alvo": operacao.alvo_latitude,
            "longitude_alvo": operacao.alvo_longitude,
            "altitude_alvo_m": operacao.alvo_altitude_m or 35.0,
            "gravar_video": True,
            "captar_foto": False,
            "pairar_no_destino": False,
            "regressar_base": True,
            "ativar_sensores": True,
            "usar_live_view": True,
        },
    )
    resposta_post = processar_post_operacao_detail_sf(
        request_method=request.method,
        action=request.POST.get("sf_action"),
        operacao_form=operacao_form,
        missao_programada_form=missao_programada_form,
        missao_edicao=missao_edicao,
        empresa=drone.empresa,
        utilizador=request.user,
    )
    if resposta_post["handled"]:
        if resposta_post["ok"]:
            messages.success(request, resposta_post["message"])
        else:
            messages.error(request, resposta_post["message"])
        return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)

    missoes_programadas = construir_missoes_programadas_contexto(drone, limit=20)

    return render(
        request,
        "geologia/drone_sf_operacao_detail.html",
        {
            "drone": drone,
            "operacao": operacao,
            "operacao_form": operacao_form,
            "comando_form": comando_form,
            "missao_programada_form": missao_programada_form,
            "missao_edicao": missao_edicao,
            "comandos_recentes": obter_comandos_recentes_operacao_sf(operacao, limit=10),
            "missoes_programadas": missoes_programadas,
            "bridge_logs": bridge_logs_context_sf(operacao),
            "bridge_status_summary": bridge_status_summary_sf(operacao),
            "motor_missoes_summary": motor_missoes_summary_sf(operacao),
            "empresa_geologia": empresa,
        },
    )


@login_required
@admin_required
def drone_sf_comando_create(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao = obter_operacao_drone_sf(drone)
    resultado_comando = processar_post_comando_sf(
        request_method=request.method,
        request_post=request.POST,
        operacao=operacao,
        empresa=drone.empresa,
        utilizador=request.user,
    )
    if resultado_comando["handled"]:
        if resultado_comando["ok"]:
            messages.success(request, resultado_comando["message"])
        else:
            messages.error(request, resultado_comando["message"])
    return redirect("geologia:drone_sf_operacao_detail", drone_id=drone.pk)


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_toggle(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)

    novo_estado = request.POST.get("ativa") == "1"
    resultado = processar_acao_missao_programada_sf(
        acao="toggle",
        processar_toggle_fn=processar_toggle_missao_programada_sf,
        missao=missao,
        ativa=novo_estado,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_executar(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao = obter_operacao_drone_sf(drone)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)

    resultado = processar_acao_missao_programada_sf(
        acao="executar",
        processar_execucao_fn=processar_execucao_missao_programada_sf,
        missao=missao,
        operacao=operacao,
        utilizador=request.user,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


@login_required
@admin_required
@require_POST
def drone_sf_missao_programada_delete(request, drone_id, missao_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return resposta_erro

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    missao = obter_missao_programada_drone_sf(drone=drone, missao_id=missao_id)
    resultado = processar_acao_missao_programada_sf(
        acao="remover",
        processar_remocao_fn=processar_remocao_missao_programada_sf,
        missao=missao,
    )
    return _mensagem_sucesso_redirect(
        request=request,
        mensagem=resultado["mensagem"],
        redirect_name="geologia:drone_sf_operacao_detail",
        drone_id=drone.pk,
    )


@csrf_exempt
@require_POST
def api_drone_sf_bridge_ingest_estado(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    processar_ingest_estado_bridge_sf(operacao, payload)
    return _json_ok(
        {
            "estado": {
                "estado": operacao.estado,
                "estado_label": operacao.get_estado_display(),
                "ultimo_heartbeat": operacao.ultimo_heartbeat.isoformat() if operacao.ultimo_heartbeat else "",
            }
        }
    )


@csrf_exempt
@require_GET
def api_drone_sf_bridge_comandos_pendentes(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="GET",
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]

    comandos = processar_comandos_pendentes_bridge_sf(operacao)
    return _json_ok({"comandos": comandos})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_confirmar_comando(request, comando_id):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    comando = obter_comando_sf_operacao(operacao=operacao, comando_id=comando_id)
    erro_response = confirmar_comando_bridge_sf(comando=comando, payload=payload)
    if erro_response is not None:
        return erro_response
    return _json_ok({"comando_id": str(comando.id), "status": comando.status})


@csrf_exempt
@require_POST
def api_drone_sf_bridge_log_event(request):
    contexto = resolver_contexto_bridge_sf(
        request=request,
        obter_operacao_por_bridge_key_fn=obter_operacao_sf_por_bridge_key,
        metodo="POST",
        requer_payload_json=True,
    )
    if not contexto["ok"]:
        return contexto["erro_response"]
    operacao = contexto["operacao"]
    payload = contexto["payload"]

    processar_log_event_bridge_sf(operacao, payload)
    return _json_ok()


@login_required
@admin_required
@require_GET
def api_drone_sf_estado(request, drone_id):
    empresa, _, resposta_erro = obter_empresa_admin_geologia(request)
    if resposta_erro:
        return _json_erro(erro="Sem permissões para consultar o estado do Drone S_F.", status=403)

    drone = obter_drone_sf_simples(pk=drone_id, empresa=empresa)
    operacao, _ = obter_ou_criar_operacao_drone_sf(drone)
    return _json_ok({"estado": serializar_estado_operacao_sf(operacao)})


@login_required
@geologia_operacional_required
def furo_geologia_dashboard(request, furo_id):
    empresa, _, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_geologia_dashboard(furo_id=furo_id, empresa=empresa)
    logs = obter_logs_furo_geologia(furo)
    missoes = obter_missoes_furo_geologia(furo)

    return render(
        request,
        "geologia/furo_dashboard.html",
        {
            "furo": furo,
            "logs": logs,
            "missoes": missoes,
        },
    )
