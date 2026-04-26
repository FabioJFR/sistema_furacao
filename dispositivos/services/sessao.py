from django.core.exceptions import ValidationError
from django.utils import timezone

from dispositivos.models import SessaoDispositivo
from dispositivos.services.conexao import construir_driver
from dispositivos.services.ingestao import guardar_leitura_dispositivo


def _validar_empregado_empresa(empregado):
    if not empregado or not empregado.empresa_id:
        raise ValidationError(
            "O utilizador autenticado não está associado a um empregado com empresa válida."
        )


def _validar_dispositivo_empresa(dispositivo, empregado):
    if dispositivo.empresa_id != empregado.empresa_id:
        raise ValidationError("O dispositivo não pertence à empresa do empregado autenticado.")


def _validar_furo_empresa(furo, empregado):
    if furo and furo.empresa_id != empregado.empresa_id:
        raise ValidationError("O furo não pertence à empresa do empregado autenticado.")


def criar_sessao_dispositivo(*, dispositivo, furo, empregado):
    _validar_empregado_empresa(empregado)
    _validar_dispositivo_empresa(dispositivo, empregado)
    _validar_furo_empresa(furo, empregado)

    return SessaoDispositivo.objects.create(
        empresa=empregado.empresa,
        empregado=empregado,
        dispositivo=dispositivo,
        furo=furo,
        status="criada",
    )


def ler_dispositivo_uma_vez(*, sessao):
    driver = construir_driver(sessao.dispositivo)

    try:
        sessao.status = "ligando"
        sessao.mensagem_erro = ""
        sessao.save(update_fields=["status", "mensagem_erro"])

        driver.connect()

        sessao.status = "ligado"
        sessao.save(update_fields=["status"])

        raw = driver.read_once()
        resultado = guardar_leitura_dispositivo(sessao=sessao, raw_payload=raw)

        return {
            "raw_payload": raw,
            "dados": resultado["dados"],
            "medicao_id": str(resultado["medicao"].id),
            "shot_id": str(resultado["shot"].id),
        }
    except Exception as exc:
        sessao.status = "erro"
        sessao.mensagem_erro = str(exc)
        sessao.save(update_fields=["status", "mensagem_erro"])
        raise ValidationError(str(exc)) from exc
    finally:
        try:
            driver.disconnect()
        except Exception:
            pass

        if sessao.status != "erro":
            sessao.status = "encerrada"
            sessao.terminado_em = timezone.now()
            sessao.save(update_fields=["status", "terminado_em"])
