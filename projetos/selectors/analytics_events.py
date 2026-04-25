def obter_instancia_original(sender, pk):
    if sender is None or pk is None:
        return None
    return sender.objects.filter(pk=pk).first()
