from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Furo

@receiver(pre_save, sender=Furo)
def verificar_alteracoes(sender, instance, **kwargs):

    if not instance.pk:
        return  # novo furo, ignora

    try:
        antigo = Furo.objects.get(pk=instance.pk)
    except Furo.DoesNotExist:
        return

    if antigo.profundidade_atual != instance.profundidade_atual:
        print("🔔 Profundidade alterada!")

    if antigo.medicoes_json != instance.medicoes_json:
        print("🔔 Medições alteradas!")