from core.domain import build_repositories
from projetos.domain_registry import PROJETOS_MODEL_MAP


PROJETOS_SELECTORS = build_repositories(PROJETOS_MODEL_MAP)

