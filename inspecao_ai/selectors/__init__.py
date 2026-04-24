from core.domain import build_repositories
from inspecao_ai.domain_registry import INSPECAO_AI_MODEL_MAP


INSPECAO_AI_SELECTORS = build_repositories(INSPECAO_AI_MODEL_MAP)

