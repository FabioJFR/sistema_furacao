from core.domain import build_services
from dispositivos.selectors.catalog import DISPOSITIVOS_SELECTORS


DISPOSITIVOS_SERVICES = build_services(DISPOSITIVOS_SELECTORS)

