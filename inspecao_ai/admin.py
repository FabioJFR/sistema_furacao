from django.contrib import admin

from .models import AnaliseImagemAI, ChatMensagemAI, ChatSessaoAI, DeteccaoImagemAI


@admin.register(AnaliseImagemAI)
class AnaliseImagemAIAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "empresa",
        "tipo_documento",
        "estado",
        "marcador_predominante",
        "texto_detectado",
        "criado_em",
    )
    list_filter = ("tipo_documento", "estado", "marcador_predominante", "empresa")
    search_fields = ("nome", "texto_extraido_bruto", "texto_normalizado")


@admin.register(DeteccaoImagemAI)
class DeteccaoImagemAIAdmin(admin.ModelAdmin):
    list_display = ("analise", "ordem", "tipo_deteccao", "marcador_cor", "confianca", "criado_em")
    list_filter = ("tipo_deteccao", "marcador_cor")
    search_fields = ("analise__nome", "texto_sugerido")


@admin.register(ChatSessaoAI)
class ChatSessaoAIAdmin(admin.ModelAdmin):
    list_display = ("titulo", "empresa", "utilizador", "ativa", "atualizado_em")
    list_filter = ("ativa", "empresa")
    search_fields = ("titulo", "utilizador__username")


@admin.register(ChatMensagemAI)
class ChatMensagemAIAdmin(admin.ModelAdmin):
    list_display = ("sessao", "papel", "criado_em")
    list_filter = ("papel",)
    search_fields = ("sessao__titulo", "conteudo")
