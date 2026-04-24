from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from .repository import ModelRepository


@dataclass(frozen=True)
class ModelService:
    repository: ModelRepository

    @property
    def model(self):
        return self.repository.model

    @transaction.atomic
    def create(self, **data):
        return self.model.objects.create(**data)

    @transaction.atomic
    def update(self, instance, **data):
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @transaction.atomic
    def delete(self, instance):
        instance.delete()
        return None

    @transaction.atomic
    def upsert(self, lookup: dict, defaults: dict):
        return self.model.objects.update_or_create(defaults=defaults, **lookup)


def build_services(repositories: dict[str, ModelRepository]) -> dict[str, ModelService]:
    return {
        name: ModelService(repository=repository)
        for name, repository in repositories.items()
    }

