from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Model
from django.shortcuts import get_object_or_404


@dataclass(frozen=True)
class ModelRepository:
    model: type[Model]

    def queryset(self):
        return self.model.objects.all()

    def filter(self, **filters):
        return self.queryset().filter(**filters)

    def get(self, **filters):
        return self.queryset().get(**filters)

    def get_or_404(self, **filters):
        return get_object_or_404(self.queryset(), **filters)

    def exists(self, **filters):
        return self.filter(**filters).exists()

    def first(self, **filters):
        return self.filter(**filters).first()


def build_repositories(model_map: dict[str, type[Model]]) -> dict[str, ModelRepository]:
    return {name: ModelRepository(model=model_cls) for name, model_cls in model_map.items()}

