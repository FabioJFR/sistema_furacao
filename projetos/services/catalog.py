from core.domain import build_services
from projetos.domain_registry import PROJETOS_MODEL_MAP
from projetos.selectors.catalog import PROJETOS_SELECTORS


PROJETOS_SERVICES = build_services(PROJETOS_SELECTORS)

