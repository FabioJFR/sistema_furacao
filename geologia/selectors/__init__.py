from core.domain import build_repositories
from geologia.domain_registry import GEOLOGIA_MODEL_MAP


GEOLOGIA_SELECTORS = build_repositories(GEOLOGIA_MODEL_MAP)

