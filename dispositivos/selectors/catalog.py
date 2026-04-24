from core.domain import build_repositories
from dispositivos.domain_registry import DISPOSITIVOS_MODEL_MAP


DISPOSITIVOS_SELECTORS = build_repositories(DISPOSITIVOS_MODEL_MAP)

