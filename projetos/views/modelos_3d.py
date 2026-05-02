import csv
import io
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from core.permissions import admin_required
from projetos.models import Modelo3DBlock, Modelo3DImplicit, Modelo3DWireframe

MAX_WIREFRAME_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
WIREFRAME_ALLOWED_EXTENSIONS = {".obj", ".dxf"}
MAX_BLOCK_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
BLOCK_ALLOWED_EXTENSIONS = {".csv", ".json"}
MAX_IMPLICIT_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
IMPLICIT_ALLOWED_EXTENSIONS = {".csv", ".json"}


def _garantir_superuser(request):
    if request.user.is_superuser:
        return None
    messages.error(request, _("Esta área 3D avançada está disponível apenas para superuser."))
    return redirect("projetos:dashboard")


def _bytes_human_readable(size_bytes):
    units = ["B", "KB", "MB", "GB"]
    value = float(size_bytes or 0)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024.0
    return f"{value:.2f} {unit}"


def _construir_preview_wireframe(uploaded_file):
    nome = uploaded_file.name or ""
    extensao = ""
    if "." in nome:
        extensao = "." + nome.rsplit(".", 1)[-1].lower()

    if extensao not in WIREFRAME_ALLOWED_EXTENSIONS:
        return {
            "ok": False,
            "erro": _("Formato não suportado. Envia apenas ficheiros .obj ou .dxf."),
        }

    tamanho = uploaded_file.size or 0
    if tamanho > MAX_WIREFRAME_UPLOAD_BYTES:
        return {
            "ok": False,
            "erro": _("Ficheiro demasiado grande. Limite atual: 15 MB."),
        }

    raw_full = uploaded_file.read()
    raw = raw_full[:200_000]  # pré-visualização limitada
    texto = raw.decode("utf-8", errors="ignore")
    linhas = [linha.rstrip() for linha in texto.splitlines()[:20]]

    contagem_obj = {
        "vertices": 0,
        "faces": 0,
        "lines": 0,
    }
    contagem_dxf = {
        "entities_tokens": 0,
        "lines": 0,
    }

    if extensao == ".obj":
        for linha in texto.splitlines():
            strip = linha.strip()
            if strip.startswith("v "):
                contagem_obj["vertices"] += 1
            elif strip.startswith("f "):
                contagem_obj["faces"] += 1
            elif strip.startswith("l "):
                contagem_obj["lines"] += 1
    elif extensao == ".dxf":
        upper = texto.upper()
        contagem_dxf["entities_tokens"] = upper.count("ENTITIES")
        contagem_dxf["lines"] = len(texto.splitlines())

    return {
        "ok": True,
        "preview": {
            "nome": nome,
            "extensao": extensao,
            "tamanho_bytes": tamanho,
            "tamanho_humano": _bytes_human_readable(tamanho),
            "conteudo_texto": raw_full.decode("utf-8", errors="ignore"),
            "linhas_preview": linhas,
            "obj_stats": contagem_obj if extensao == ".obj" else None,
            "dxf_stats": contagem_dxf if extensao == ".dxf" else None,
        },
    }


def _nome_download_seguro(item):
    nome_base = item.nome or f"wireframe-{item.pk}"
    nome_base = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in nome_base).strip("._")
    if not nome_base:
        nome_base = f"wireframe-{item.pk}"
    ext = f".{item.formato}" if item.formato else ""
    if ext and not nome_base.lower().endswith(ext):
        nome_base = f"{nome_base}{ext}"
    return nome_base


def _construir_preview_block(uploaded_file):
    nome = uploaded_file.name or ""
    extensao = ""
    if "." in nome:
        extensao = "." + nome.rsplit(".", 1)[-1].lower()

    if extensao not in BLOCK_ALLOWED_EXTENSIONS:
        return {"ok": False, "erro": _("Formato não suportado. Envia apenas ficheiros .csv ou .json.")}

    tamanho = uploaded_file.size or 0
    if tamanho > MAX_BLOCK_UPLOAD_BYTES:
        return {"ok": False, "erro": _("Ficheiro demasiado grande. Limite atual: 20 MB.")}

    raw_full = uploaded_file.read()
    conteudo = raw_full.decode("utf-8", errors="ignore")
    linhas_preview = [linha.rstrip() for linha in conteudo.splitlines()[:20]]

    stats = {"registos": 0, "x_min": None, "x_max": None, "y_min": None, "y_max": None, "z_min": None, "z_max": None}
    erros = 0

    def acc(x, y, z):
        stats["registos"] += 1
        stats["x_min"] = x if stats["x_min"] is None else min(stats["x_min"], x)
        stats["x_max"] = x if stats["x_max"] is None else max(stats["x_max"], x)
        stats["y_min"] = y if stats["y_min"] is None else min(stats["y_min"], y)
        stats["y_max"] = y if stats["y_max"] is None else max(stats["y_max"], y)
        stats["z_min"] = z if stats["z_min"] is None else min(stats["z_min"], z)
        stats["z_max"] = z if stats["z_max"] is None else max(stats["z_max"], z)

    if extensao == ".csv":
        reader = csv.DictReader(io.StringIO(conteudo))
        for row in reader:
            try:
                x = float(row.get("x"))
                y = float(row.get("y"))
                z = float(row.get("z"))
                acc(x, y, z)
            except Exception:
                erros += 1
    else:
        try:
            payload = json.loads(conteudo or "[]")
            if isinstance(payload, list):
                for item in payload:
                    try:
                        x = float(item.get("x"))
                        y = float(item.get("y"))
                        z = float(item.get("z"))
                        acc(x, y, z)
                    except Exception:
                        erros += 1
            else:
                erros += 1
        except Exception:
            return {"ok": False, "erro": _("JSON inválido para block model.")}

    return {
        "ok": True,
        "preview": {
            "nome": nome,
            "extensao": extensao,
            "tamanho_bytes": tamanho,
            "tamanho_humano": _bytes_human_readable(tamanho),
            "conteudo_texto": conteudo,
            "linhas_preview": linhas_preview,
            "stats": stats,
            "erros": erros,
        },
    }


def _construir_preview_implicit(uploaded_file):
    nome = uploaded_file.name or ""
    extensao = ""
    if "." in nome:
        extensao = "." + nome.rsplit(".", 1)[-1].lower()

    if extensao not in IMPLICIT_ALLOWED_EXTENSIONS:
        return {"ok": False, "erro": _("Formato não suportado. Envia apenas ficheiros .csv ou .json.")}

    tamanho = uploaded_file.size or 0
    if tamanho > MAX_IMPLICIT_UPLOAD_BYTES:
        return {"ok": False, "erro": _("Ficheiro demasiado grande. Limite atual: 20 MB.")}

    raw_full = uploaded_file.read()
    conteudo = raw_full.decode("utf-8", errors="ignore")
    linhas_preview = [linha.rstrip() for linha in conteudo.splitlines()[:20]]

    stats = {
        "registos": 0,
        "x_min": None, "x_max": None,
        "y_min": None, "y_max": None,
        "z_min": None, "z_max": None,
        "dominios": {},
    }
    erros = 0

    def acc(x, y, z, dom):
        stats["registos"] += 1
        stats["x_min"] = x if stats["x_min"] is None else min(stats["x_min"], x)
        stats["x_max"] = x if stats["x_max"] is None else max(stats["x_max"], x)
        stats["y_min"] = y if stats["y_min"] is None else min(stats["y_min"], y)
        stats["y_max"] = y if stats["y_max"] is None else max(stats["y_max"], y)
        stats["z_min"] = z if stats["z_min"] is None else min(stats["z_min"], z)
        stats["z_max"] = z if stats["z_max"] is None else max(stats["z_max"], z)
        key = (dom or "default").strip() or "default"
        stats["dominios"][key] = stats["dominios"].get(key, 0) + 1

    if extensao == ".csv":
        reader = csv.DictReader(io.StringIO(conteudo))
        for row in reader:
            try:
                x = float(row.get("x"))
                y = float(row.get("y"))
                z = float(row.get("z"))
                dom = row.get("dominio") or row.get("domain") or "default"
                acc(x, y, z, dom)
            except Exception:
                erros += 1
    else:
        try:
            payload = json.loads(conteudo or "[]")
            if isinstance(payload, list):
                for item in payload:
                    try:
                        x = float(item.get("x"))
                        y = float(item.get("y"))
                        z = float(item.get("z"))
                        dom = item.get("dominio") or item.get("domain") or "default"
                        acc(x, y, z, dom)
                    except Exception:
                        erros += 1
            else:
                erros += 1
        except Exception:
            return {"ok": False, "erro": _("JSON inválido para implicit model.")}

    return {
        "ok": True,
        "preview": {
            "nome": nome,
            "extensao": extensao,
            "tamanho_bytes": tamanho,
            "tamanho_humano": _bytes_human_readable(tamanho),
            "conteudo_texto": conteudo,
            "linhas_preview": linhas_preview,
            "stats": stats,
            "erros": erros,
        },
    }


@login_required
@admin_required
def modelos_3d_hub(request):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    return render(request, "projetos/modelos_3d_hub.html")


@login_required
@admin_required
def modelo_3d_wireframe(request):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio

    preview = None
    if request.method == "POST":
        action = request.POST.get("action", "validate")
        ficheiro = request.FILES.get("wireframe_file")
        if not ficheiro:
            messages.error(request, _("Seleciona um ficheiro .obj ou .dxf para pré-visualizar."))
        else:
            resultado = _construir_preview_wireframe(ficheiro)
            if not resultado["ok"]:
                messages.error(request, resultado["erro"])
            else:
                preview = resultado["preview"]
                messages.success(request, _("Ficheiro lido com sucesso. Pré-visualização técnica gerada."))

                if action == "validate_and_save":
                    extensao_limpa = (preview.get("extensao") or "").replace(".", "")
                    resumo = {
                        "linhas_preview": preview.get("linhas_preview") or [],
                        "obj_stats": preview.get("obj_stats"),
                        "dxf_stats": preview.get("dxf_stats"),
                        "tamanho_humano": preview.get("tamanho_humano"),
                    }
                    Modelo3DWireframe.objects.create(
                        criado_por=request.user,
                        nome=preview.get("nome") or "wireframe",
                        formato=extensao_limpa,
                        conteudo_texto=preview.get("conteudo_texto") or "",
                        tamanho_bytes=preview.get("tamanho_bytes") or 0,
                        resumo_json=resumo,
                    )
                    messages.success(request, _("Ficheiro guardado na base de dados com sucesso."))

    historico_guardados = Modelo3DWireframe.objects.select_related("criado_por")[:10]

    return render(
        request,
        "projetos/modelo_3d_wireframe.html",
        {
            "wireframe_preview": preview,
            "wireframe_max_upload_mb": int(MAX_WIREFRAME_UPLOAD_BYTES / (1024 * 1024)),
            "wireframe_guardados": historico_guardados,
        },
    )


@login_required
@admin_required
def modelo_3d_block_model(request):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    preview = None
    if request.method == "POST":
        action = request.POST.get("action", "validate")
        ficheiro = request.FILES.get("block_file")
        if not ficheiro:
            messages.error(request, _("Seleciona um ficheiro .csv ou .json para block model."))
        else:
            resultado = _construir_preview_block(ficheiro)
            if not resultado["ok"]:
                messages.error(request, resultado["erro"])
            else:
                preview = resultado["preview"]
                messages.success(request, _("Ficheiro block model lido com sucesso."))
                if action == "validate_and_save":
                    formato = (preview.get("extensao") or "").replace(".", "")
                    Modelo3DBlock.objects.create(
                        criado_por=request.user,
                        nome=preview.get("nome") or "block-model",
                        formato=formato,
                        conteudo_texto=preview.get("conteudo_texto") or "",
                        tamanho_bytes=preview.get("tamanho_bytes") or 0,
                        resumo_json={
                            "stats": preview.get("stats") or {},
                            "erros": preview.get("erros") or 0,
                            "tamanho_humano": preview.get("tamanho_humano"),
                        },
                    )
                    messages.success(request, _("Block model guardado na base de dados com sucesso."))

    historico_guardados = Modelo3DBlock.objects.select_related("criado_por")[:10]
    return render(
        request,
        "projetos/modelo_3d_block_model.html",
        {
            "block_preview": preview,
            "block_max_upload_mb": int(MAX_BLOCK_UPLOAD_BYTES / (1024 * 1024)),
            "block_guardados": historico_guardados,
        },
    )


@login_required
@admin_required
def modelo_3d_implicit(request):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    preview = None
    if request.method == "POST":
        action = request.POST.get("action", "validate")
        ficheiro = request.FILES.get("implicit_file")
        dominio = (request.POST.get("dominio") or "default").strip() or "default"
        if not ficheiro:
            messages.error(request, _("Seleciona um ficheiro .csv ou .json para implicit model."))
        else:
            resultado = _construir_preview_implicit(ficheiro)
            if not resultado["ok"]:
                messages.error(request, resultado["erro"])
            else:
                preview = resultado["preview"]
                messages.success(request, _("Ficheiro implicit model lido com sucesso."))
                if action == "validate_and_save":
                    formato = (preview.get("extensao") or "").replace(".", "")
                    Modelo3DImplicit.objects.create(
                        criado_por=request.user,
                        nome=preview.get("nome") or "implicit-model",
                        formato=formato,
                        dominio=dominio,
                        conteudo_texto=preview.get("conteudo_texto") or "",
                        tamanho_bytes=preview.get("tamanho_bytes") or 0,
                        resumo_json={
                            "stats": preview.get("stats") or {},
                            "erros": preview.get("erros") or 0,
                            "tamanho_humano": preview.get("tamanho_humano"),
                        },
                    )
                    messages.success(request, _("Implicit model guardado na base de dados com sucesso."))

    historico_guardados = Modelo3DImplicit.objects.select_related("criado_por")[:10]
    return render(
        request,
        "projetos/modelo_3d_implicit.html",
        {
            "implicit_preview": preview,
            "implicit_max_upload_mb": int(MAX_IMPLICIT_UPLOAD_BYTES / (1024 * 1024)),
            "implicit_guardados": historico_guardados,
        },
    )


@login_required
@admin_required
def modelo_3d_wireframe_conteudo(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DWireframe, pk=pk)
    if item.formato not in {"obj", "dxf"}:
        raise Http404
    if not (item.conteudo_texto or "").strip():
        return HttpResponse(
            _("Este registo não tem conteúdo técnico guardado. Volta a carregar o ficheiro e guarda novamente."),
            status=409,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")


@login_required
@admin_required
def modelo_3d_wireframe_download(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DWireframe, pk=pk)
    if item.formato not in {"obj", "dxf"}:
        raise Http404
    nome = _nome_download_seguro(item)
    response = HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nome}"'
    return response


@login_required
@admin_required
def modelo_3d_wireframe_apagar(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    if request.method != "POST":
        return redirect("projetos:modelo_3d_wireframe")
    item = get_object_or_404(Modelo3DWireframe, pk=pk)
    nome = item.nome
    item.delete()
    messages.success(request, _("Modelo wireframe '%(nome)s' removido com sucesso.") % {"nome": nome})
    return redirect("projetos:modelo_3d_wireframe")


@login_required
@admin_required
def modelo_3d_block_conteudo(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DBlock, pk=pk)
    if item.formato not in {"csv", "json"}:
        raise Http404
    if not (item.conteudo_texto or "").strip():
        return HttpResponse(
            _("Este registo não tem conteúdo técnico guardado."),
            status=409,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")


def _normalizar_block_ui_config(payload):
    if not isinstance(payload, dict):
        return {}

    def _to_bool(value, default=False):
        return value if isinstance(value, bool) else default

    def _to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    return {
        "mostrar_como_voxels": _to_bool(payload.get("mostrar_como_voxels"), True),
        "valor_min": _to_float(payload.get("valor_min"), 0.0),
        "valor_max": _to_float(payload.get("valor_max"), 100.0),
        "z_min": _to_float(payload.get("z_min"), 0.0),
        "z_max": _to_float(payload.get("z_max"), 100.0),
        "animacao_rotacao": _to_bool(payload.get("animacao_rotacao"), False),
        "animacao_pulso": _to_bool(payload.get("animacao_pulso"), False),
    }


def _normalizar_implicit_ui_config(payload):
    if not isinstance(payload, dict):
        return {}

    def _to_bool(value, default=False):
        return value if isinstance(value, bool) else default

    def _to_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _to_str(value, default=""):
        return str(value) if value is not None else default

    checked_domains = payload.get("checkedDomains")
    if not isinstance(checked_domains, list):
        checked_domains = []
    checked_domains = [_to_str(v, "").strip() for v in checked_domains if _to_str(v, "").strip()]

    return {
        "showPoints": _to_bool(payload.get("showPoints"), True),
        "showSurface": _to_bool(payload.get("showSurface"), True),
        "surfaceMode": _to_str(payload.get("surfaceMode"), "delaunay") or "delaunay",
        "opacity": _to_float(payload.get("opacity"), 0.2),
        "selectedDomain": _to_str(payload.get("selectedDomain"), "all") or "all",
        "checkedDomains": checked_domains,
        "rotateAnim": _to_bool(payload.get("rotateAnim"), False),
        "pulseAnim": _to_bool(payload.get("pulseAnim"), False),
    }


@login_required
@admin_required
def modelo_3d_block_config(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return JsonResponse({"ok": False, "erro": _("Acesso negado.")}, status=403)

    item = get_object_or_404(Modelo3DBlock, pk=pk)

    if request.method == "GET":
        resumo = item.resumo_json or {}
        return JsonResponse({"ok": True, "ui_config": resumo.get("ui_config") or {}})

    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": _("Método não suportado.")}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "erro": _("JSON inválido.")}, status=400)

    ui_config = _normalizar_block_ui_config(payload.get("ui_config"))
    resumo = dict(item.resumo_json or {})
    resumo["ui_config"] = ui_config
    item.resumo_json = resumo
    item.save(update_fields=["resumo_json", "atualizado_em"])
    return JsonResponse({"ok": True})


@login_required
@admin_required
def modelo_3d_block_download(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DBlock, pk=pk)
    if item.formato not in {"csv", "json"}:
        raise Http404
    nome = _nome_download_seguro(item)
    response = HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nome}"'
    return response


@login_required
@admin_required
def modelo_3d_block_apagar(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    if request.method != "POST":
        return redirect("projetos:modelo_3d_block_model")
    item = get_object_or_404(Modelo3DBlock, pk=pk)
    nome = item.nome
    item.delete()
    messages.success(request, _("Modelo block '%(nome)s' removido com sucesso.") % {"nome": nome})
    return redirect("projetos:modelo_3d_block_model")


@login_required
@admin_required
def modelo_3d_implicit_conteudo(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DImplicit, pk=pk)
    if item.formato not in {"csv", "json"}:
        raise Http404
    if not (item.conteudo_texto or "").strip():
        return HttpResponse(
            _("Este registo não tem conteúdo técnico guardado."),
            status=409,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")


@login_required
@admin_required
def modelo_3d_implicit_config(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return JsonResponse({"ok": False, "erro": _("Acesso negado.")}, status=403)

    item = get_object_or_404(Modelo3DImplicit, pk=pk)

    if request.method == "GET":
        resumo = item.resumo_json or {}
        return JsonResponse({"ok": True, "ui_config": resumo.get("ui_config") or {}})

    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": _("Método não suportado.")}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "erro": _("JSON inválido.")}, status=400)

    ui_config = _normalizar_implicit_ui_config(payload.get("ui_config"))
    resumo = dict(item.resumo_json or {})
    resumo["ui_config"] = ui_config
    item.resumo_json = resumo
    item.save(update_fields=["resumo_json", "atualizado_em"])
    return JsonResponse({"ok": True})


@login_required
@admin_required
def modelo_3d_implicit_download(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    item = get_object_or_404(Modelo3DImplicit, pk=pk)
    if item.formato not in {"csv", "json"}:
        raise Http404
    nome = _nome_download_seguro(item)
    response = HttpResponse(item.conteudo_texto or "", content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{nome}"'
    return response


@login_required
@admin_required
def modelo_3d_implicit_apagar(request, pk):
    bloqueio = _garantir_superuser(request)
    if bloqueio:
        return bloqueio
    if request.method != "POST":
        return redirect("projetos:modelo_3d_implicit")
    item = get_object_or_404(Modelo3DImplicit, pk=pk)
    nome = item.nome
    item.delete()
    messages.success(request, _("Modelo implícito '%(nome)s' removido com sucesso.") % {"nome": nome})
    return redirect("projetos:modelo_3d_implicit")
