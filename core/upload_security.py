import mimetypes
import subprocess
import tempfile
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image


DEFAULT_BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".com",
    ".scr",
    ".msi",
    ".ps1",
    ".sh",
    ".php",
    ".phtml",
    ".js",
    ".jar",
    ".apk",
    ".bin",
}

DEFAULT_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
DEFAULT_ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".csv",
    ".json",
    ".geojson",
    ".las",
    ".obj",
    ".dxf",
    ".zip",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

ALLOWED_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff",  # jpeg
    b"\x89PNG\r\n\x1a\n",  # png
    b"GIF87a",
    b"GIF89a",
    b"RIFF",  # webp (RIFF + WEBP)
}


def _virus_scan_fail_closed() -> bool:
    return bool(getattr(settings, "UPLOAD_VIRUS_SCAN_FAIL_CLOSED", not settings.DEBUG))


def _as_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


def _settings_set(name: str, fallback: set[str]) -> set[str]:
    value = getattr(settings, name, None)
    if not value:
        return fallback
    return {str(item).lower() if str(item).startswith(".") else f".{str(item).lower()}" for item in value}


def _validate_extension(*, field_name: str, filename: str, is_image_field: bool) -> None:
    ext = _as_extension(filename)
    blocked = _settings_set("UPLOAD_BLOCKED_EXTENSIONS", DEFAULT_BLOCKED_EXTENSIONS)
    if ext in blocked:
        raise ValidationError({field_name: "Extensão de ficheiro não permitida por segurança."})

    if is_image_field:
        allowed = _settings_set("UPLOAD_ALLOWED_IMAGE_EXTENSIONS", DEFAULT_ALLOWED_IMAGE_EXTENSIONS)
    else:
        allowed = _settings_set("UPLOAD_ALLOWED_FILE_EXTENSIONS", DEFAULT_ALLOWED_FILE_EXTENSIONS)

    if ext and ext not in allowed:
        raise ValidationError({field_name: f"Extensão '{ext}' não permitida para upload."})


def _validate_size(*, field_name: str, size: int, is_image_field: bool) -> None:
    max_mb = getattr(settings, "UPLOAD_MAX_IMAGE_MB", 8) if is_image_field else getattr(settings, "UPLOAD_MAX_FILE_MB", 25)
    max_bytes = int(max_mb * 1024 * 1024)
    if size > max_bytes:
        raise ValidationError({field_name: f"Ficheiro excede o tamanho máximo de {max_mb} MB."})


def _validate_image_signature(*, field_name: str, upload_file, filename: str) -> None:
    upload_file.seek(0)
    head = upload_file.read(32)
    upload_file.seek(0)

    ext = _as_extension(filename)
    if ext == ".webp":
        if not (head.startswith(b"RIFF") and b"WEBP" in head):
            raise ValidationError({field_name: "Assinatura inválida para ficheiro WEBP."})
        return

    if not any(head.startswith(sig) for sig in ALLOWED_IMAGE_SIGNATURES):
        raise ValidationError({field_name: "Assinatura do ficheiro de imagem inválida."})

    # validação forte pelo Pillow (abre/decodifica de facto a imagem)


def _validate_generic_mime(*, field_name: str, upload_file, filename: str) -> None:
    expected_mime, _ = mimetypes.guess_type(filename)
    if not expected_mime:
        return
    # Não bloqueia mimetypes desconhecidos no browser; valida apenas tipos executáveis críticos.
    if expected_mime in {"application/x-msdownload", "application/x-sh"}:
        raise ValidationError({field_name: "Tipo MIME não permitido por segurança."})
    upload_file.seek(0)


def _scan_with_clamav(*, field_name: str, upload_file) -> None:
    if not getattr(settings, "UPLOAD_VIRUS_SCAN_ENABLED", False):
        return "disabled"

    command = getattr(settings, "UPLOAD_VIRUS_SCAN_COMMAND", "clamscan")
    timeout = int(getattr(settings, "UPLOAD_VIRUS_SCAN_TIMEOUT_SECONDS", 15))

    upload_file.seek(0)
    with tempfile.NamedTemporaryFile(delete=True) as temp:
        temp.write(upload_file.read())
        temp.flush()
        upload_file.seek(0)
        try:
            proc = subprocess.run(
                [command, "--no-summary", temp.name],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except Exception as exc:
            if _virus_scan_fail_closed():
                raise ValidationError(
                    {
                        field_name: (
                            "Não foi possível concluir a validação antivírus do ficheiro."
                        )
                    }
                ) from exc
            return "scanner_unavailable"

    output = f"{proc.stdout}\n{proc.stderr}".upper()
    if "FOUND" in output or proc.returncode == 1:
        raise ValidationError({field_name: "Ficheiro rejeitado na validação de segurança (antivírus)."})
    if proc.returncode != 0:
        if _virus_scan_fail_closed():
            raise ValidationError(
                {
                    field_name: (
                        "Não foi possível concluir a validação antivírus do ficheiro."
                    )
                }
            )
        return "scanner_unavailable"
    return "scanned"


def _sanitize_image_if_needed(*, field_name: str, upload_file):
    max_edge = int(getattr(settings, "UPLOAD_IMAGE_MAX_EDGE_PX", 2560))
    target_quality = int(getattr(settings, "UPLOAD_IMAGE_JPEG_QUALITY", 82))
    optimize = bool(getattr(settings, "UPLOAD_IMAGE_OPTIMIZE", True))

    upload_file.seek(0)
    try:
        image = Image.open(upload_file)
        image.load()
    except Exception as exc:
        raise ValidationError({field_name: f"Imagem inválida/corrompida: {exc}"}) from exc

    fmt = (image.format or "JPEG").upper()
    if image.mode in {"RGBA", "P"} and fmt in {"JPEG", "JPG"}:
        image = image.convert("RGB")

    width, height = image.size
    if max(width, height) > max_edge:
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    save_kwargs = {"optimize": optimize}
    if fmt in {"JPEG", "JPG"}:
        save_kwargs["quality"] = target_quality
        save_format = "JPEG"
    elif fmt == "PNG":
        save_format = "PNG"
    elif fmt == "WEBP":
        save_format = "WEBP"
        save_kwargs["quality"] = target_quality
    else:
        save_format = "PNG"

    image.save(buffer, format=save_format, **save_kwargs)
    buffer.seek(0)
    original_name = upload_file.name or "upload"
    base = original_name.rsplit(".", 1)[0]
    ext = save_format.lower().replace("jpeg", "jpg")
    return ContentFile(buffer.read(), name=f"{base}.{ext}")


def validate_and_secure_model_uploads(instance) -> None:
    for field in instance._meta.get_fields():
        if not hasattr(field, "attname"):
            continue
        model_field = getattr(instance.__class__, field.name, None)
        django_field = getattr(model_field, "field", None)
        if not isinstance(django_field, (models.FileField, models.ImageField)):
            continue

        bound = getattr(instance, field.name, None)
        if not bound:
            continue
        upload_file = getattr(bound, "file", None)
        if not upload_file:
            continue
        # Só valida uploads novos neste save para evitar reprocessar ficheiros antigos.
        if getattr(bound, "_committed", True):
            continue

        is_image = isinstance(django_field, models.ImageField)
        filename = getattr(bound, "name", "") or getattr(upload_file, "name", "")
        size = getattr(bound, "size", None) or getattr(upload_file, "size", 0)

        _validate_extension(field_name=field.name, filename=filename, is_image_field=is_image)
        _validate_size(field_name=field.name, size=int(size or 0), is_image_field=is_image)

        if is_image:
            _validate_image_signature(field_name=field.name, upload_file=upload_file, filename=filename)
        else:
            _validate_generic_mime(field_name=field.name, upload_file=upload_file, filename=filename)

        _scan_with_clamav(field_name=field.name, upload_file=upload_file)

        if is_image and getattr(settings, "UPLOAD_IMAGE_SANITIZE_ENABLED", True):
            sanitized = _sanitize_image_if_needed(field_name=field.name, upload_file=upload_file)
            setattr(instance, field.name, sanitized)


def diagnosticar_upload(upload_file, tipo_esperado: str = "auto") -> dict:
    filename = getattr(upload_file, "name", "") or "upload"
    ext = _as_extension(filename)
    size = int(getattr(upload_file, "size", 0) or 0)
    tipo = (tipo_esperado or "auto").strip().lower()
    is_image = tipo == "imagem" or (tipo == "auto" and ext in _settings_set("UPLOAD_ALLOWED_IMAGE_EXTENSIONS", DEFAULT_ALLOWED_IMAGE_EXTENSIONS))

    resultado = {
        "ok": False,
        "filename": filename,
        "ext": ext,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 3),
        "is_image": is_image,
        "steps": [],
        "erro": "",
        "sanitized_size_bytes": None,
        "sanitized_size_mb": None,
    }

    def step(label: str, ok: bool, detalhe: str = ""):
        resultado["steps"].append({"label": label, "ok": ok, "detalhe": detalhe})

    try:
        _validate_extension(field_name="upload", filename=filename, is_image_field=is_image)
        step("Extensão permitida", True, ext or "sem extensão")

        _validate_size(field_name="upload", size=size, is_image_field=is_image)
        step("Tamanho permitido", True, f"{resultado['size_mb']} MB")

        if is_image:
            _validate_image_signature(field_name="upload", upload_file=upload_file, filename=filename)
            step("Assinatura de imagem válida", True)
        else:
            _validate_generic_mime(field_name="upload", upload_file=upload_file, filename=filename)
            step("Tipo MIME aceitável", True)

        if getattr(settings, "UPLOAD_VIRUS_SCAN_ENABLED", False):
            scan_result = _scan_with_clamav(field_name="upload", upload_file=upload_file)
            if scan_result == "scanner_unavailable":
                step("Scan antivírus", True, "scanner indisponível; upload aceite por configuração")
            else:
                step("Scan antivírus", True, "clamscan OK")
        else:
            step("Scan antivírus", True, "desativado por configuração")

        if is_image and getattr(settings, "UPLOAD_IMAGE_SANITIZE_ENABLED", True):
            sanitized = _sanitize_image_if_needed(field_name="upload", upload_file=upload_file)
            s_size = int(getattr(sanitized, "size", 0) or 0)
            resultado["sanitized_size_bytes"] = s_size
            resultado["sanitized_size_mb"] = round(s_size / (1024 * 1024), 3)
            reducao = round((1 - (s_size / size)) * 100, 1) if size > 0 else 0.0
            step("Sanitização/compressão de imagem", True, f"redução estimada: {reducao}%")
        elif is_image:
            step("Sanitização/compressão de imagem", True, "desativada por configuração")

        resultado["ok"] = True
        return resultado
    except ValidationError as exc:
        erro = ""
        if hasattr(exc, "message_dict") and exc.message_dict:
            erros_flat = []
            for _, msgs in exc.message_dict.items():
                if isinstance(msgs, list):
                    erros_flat.extend([str(m) for m in msgs])
                else:
                    erros_flat.append(str(msgs))
            erro = " | ".join(erros_flat)
        else:
            erro = str(exc)
        step("Validação", False, erro)
        resultado["erro"] = erro
        return resultado
