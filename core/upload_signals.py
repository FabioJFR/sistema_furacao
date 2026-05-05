from django.apps import apps
from django.db.models.signals import pre_save

from core.upload_security import validate_and_secure_model_uploads


def _pre_save_secure_uploads(sender, instance, **kwargs):
    validate_and_secure_model_uploads(instance)


def connect_upload_security_signals():
    for model in apps.get_models():
        pre_save.connect(
            _pre_save_secure_uploads,
            sender=model,
            dispatch_uid=f"upload-security-pre-save:{model._meta.label}",
            weak=False,
        )
