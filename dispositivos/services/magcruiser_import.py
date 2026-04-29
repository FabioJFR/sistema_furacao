import csv
import io
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from dispositivos.services.ingestao import guardar_leitura_dispositivo
from dispositivos.models import LeituraBrutaDispositivo
from projetos.models import Furo, Projeto


_COL_MAP = {
    "depth": "depth",
    "md": "depth",
    "measured_depth": "depth",
    "profundidade": "depth",
    "inc": "inc",
    "inclination": "inc",
    "inclinacao": "inc",
    "dip": "inc",
    "azi": "azi",
    "azimuth": "azi",
    "azimute": "azi",
    "mag": "mag",
    "magnetismo": "mag",
    "magfield": "mag",
    "mag_field": "mag",
    "temp": "temp",
    "temperature": "temp",
    "temperatura": "temp",
    "hole": "hole_name",
    "hole_name": "hole_name",
    "drillhole": "hole_name",
    "holeid": "hole_name",
    "furo": "hole_name",
    "nome_furo": "hole_name",
}


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    texto = str(value).strip().replace(",", ".")
    if not texto:
        return None
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Valor numérico inválido: '{value}'.") from exc


def _row_to_raw_payload(row):
    parts = [
        f"DEPTH={row['depth']}",
        f"INC={row['inc']}",
        f"AZI={row['azi']}",
    ]
    if row.get("mag") is not None:
        parts.append(f"MAG={row['mag']}")
    if row.get("temp") is not None:
        parts.append(f"TEMP={row['temp']}")
    return ";".join(parts)


def _decode_uploaded(uploaded_file):
    raw = uploaded_file.read()
    if isinstance(raw, str):
        return raw
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _normalize_row(row):
    normalized = {"depth": None, "inc": None, "azi": None, "mag": None, "temp": None, "hole_name": None}
    for key, value in row.items():
        canonical = _COL_MAP.get(str(key or "").strip().lower())
        if not canonical:
            continue
        if canonical == "hole_name":
            texto = str(value or "").strip()
            normalized[canonical] = texto or None
        else:
            normalized[canonical] = _to_decimal(value)

    if normalized["depth"] is None or normalized["inc"] is None or normalized["azi"] is None:
        return None
    return normalized


def _parse_csv_text(texto):
    sample = texto[:2000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"

    reader = csv.DictReader(io.StringIO(texto), dialect=dialect)
    rows = []
    for row in reader:
        parsed = _normalize_row(row)
        if parsed:
            rows.append(parsed)
    return rows


def _parse_las_text(texto):
    rows = []
    in_ascii = False
    for line in texto.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith("#"):
            continue
        upper = clean.upper()
        if upper.startswith("~A"):
            in_ascii = True
            continue
        if not in_ascii:
            continue
        if clean.startswith("~"):
            break

        chunks = clean.replace(",", ".").split()
        if len(chunks) < 3:
            continue
        depth = _to_decimal(chunks[0])
        inc = _to_decimal(chunks[1])
        azi = _to_decimal(chunks[2])
        mag = _to_decimal(chunks[3]) if len(chunks) > 3 else None
        rows.append({"depth": depth, "inc": inc, "azi": azi, "mag": mag, "temp": None, "hole_name": None})
    return rows


def _normalizar_nome_furo(nome):
    return slugify(str(nome or "").strip().lower())


def _obter_projeto_importacao(empresa):
    projeto = (
        Projeto.objects.filter(empresa=empresa, nome__iexact="Importação MagCruiser")
        .order_by("criado_em")
        .first()
    )
    if projeto:
        return projeto
    return Projeto.objects.create(
        empresa=empresa,
        nome="Importação MagCruiser",
        cliente="Importação automática",
    )


def _obter_ou_criar_furo_por_nome(*, empresa, nome_furo, criar_em_falta):
    nome = str(nome_furo or "").strip()
    if not nome:
        return None, False

    furo = Furo.objects.filter(empresa=empresa, nome__iexact=nome).order_by("data").first()
    if furo:
        return furo, False

    if not criar_em_falta:
        return None, False

    projeto = _obter_projeto_importacao(empresa)
    furo = Furo.objects.create(
        projeto=projeto,
        empresa=empresa,
        nome=nome,
        tipo="fundo",
        profundidade_inicial=0.0,
        profundidade_alvo_inicial=0.0,
        profundidade_alvo_atual=0.0,
        profundidade_atual=0.0,
        profundidade_maxima_atingida=0.0,
        inclinacao_planeada_inicial=0.0,
        azimute_planeado_inicial=0.0,
    )
    return furo, True


def parse_magcruiser_file(uploaded_file):
    if not uploaded_file:
        raise ValidationError("Selecione um ficheiro para importar.")

    filename = (uploaded_file.name or "").lower()
    texto = _decode_uploaded(uploaded_file)

    if filename.endswith(".las"):
        rows = _parse_las_text(texto)
        formato = "las"
    else:
        rows = _parse_csv_text(texto)
        formato = "csv"

    if not rows:
        raise ValidationError(
            "Não foi possível extrair linhas válidas. Confirme colunas de profundidade, inclinação e azimute."
        )

    preview = rows[:20]
    return {
        "formato": formato,
        "total_linhas": len(rows),
        "preview_rows": preview,
        "rows": rows,
        "filename": uploaded_file.name,
    }


@transaction.atomic
def gravar_importacao_magcruiser(*, sessao, rows, modo_aplicacao="all_existing"):
    if not sessao.furo_id:
        raise ValidationError("A sessão precisa estar associada a um furo para gravar medições.")
    if not rows:
        raise ValidationError("Não há linhas para gravar.")

    modo = (modo_aplicacao or "all_existing").strip()
    if modo not in {"all_existing", "latest_existing", "all_create_missing"}:
        raise ValidationError("Modo de aplicação inválido.")

    criar_em_falta = modo == "all_create_missing"
    if modo == "latest_existing":
        latest_map = {}
        for row in rows:
            chave = _normalizar_nome_furo(row.get("hole_name")) or "__sessao__"
            latest_map[chave] = row
        rows_processar = list(latest_map.values())
    else:
        rows_processar = rows

    criadas = 0
    furos_criados = 0
    furos_sem_match = set()
    resumo_por_furo = {}
    ignoradas = 0
    ultima_sequencia = (
        LeituraBrutaDispositivo.objects.filter(sessao=sessao).aggregate(max_seq=Max("sequencia")).get("max_seq") or 0
    )
    for row in rows_processar:
        nome_furo = row.get("hole_name")
        furo_destino = None
        criado_agora = False
        chave_resumo = str(nome_furo).strip() if nome_furo else (sessao.furo.nome if sessao.furo_id else "Sem furo")
        if chave_resumo not in resumo_por_furo:
            resumo_por_furo[chave_resumo] = {"gravadas": 0, "ignoradas": 0, "criado": False}
        if nome_furo:
            furo_destino, criado_agora = _obter_ou_criar_furo_por_nome(
                empresa=sessao.empresa,
                nome_furo=nome_furo,
                criar_em_falta=criar_em_falta,
            )
            if not furo_destino:
                furos_sem_match.add(str(nome_furo).strip())
                resumo_por_furo[chave_resumo]["ignoradas"] += 1
                ignoradas += 1
                continue
        else:
            furo_destino = sessao.furo

        raw_payload = _row_to_raw_payload(row)
        guardar_leitura_dispositivo(sessao=sessao, raw_payload=raw_payload, furo=furo_destino)
        criadas += 1
        resumo_por_furo[chave_resumo]["gravadas"] += 1
        if criado_agora:
            furos_criados += 1
            resumo_por_furo[chave_resumo]["criado"] = True
        ultima_sequencia += 1

    return {
        "total_gravadas": criadas,
        "total_ignoradas": ignoradas,
        "ultima_sequencia": ultima_sequencia,
        "furos_criados": furos_criados,
        "furos_sem_match": sorted(furos_sem_match),
        "resumo_por_furo": resumo_por_furo,
    }
