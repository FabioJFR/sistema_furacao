from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Furo
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import RegistoDiarioEmpregado
from .utils import recalcular_resumo_empregado  # vamos criar já a seguir

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


@receiver(post_save, sender=RegistoDiarioEmpregado)
def atualizar_resumo_apos_save(sender, instance, **kwargs):
    recalcular_resumo_empregado(instance.empregado)


@receiver(post_delete, sender=RegistoDiarioEmpregado)
def atualizar_resumo_apos_delete(sender, instance, **kwargs):
    recalcular_resumo_empregado(instance.empregado)