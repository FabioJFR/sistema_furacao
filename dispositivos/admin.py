
from django.contrib import admin
from dispositivos.models import (
    Dispositivo,
    LeituraBrutaDispositivo,
    LeituraDispositivo,
    LeituraDispositivoMedicaoLink,
    SessaoDispositivo,
    SurveyShot,
)


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "tipo",
        "canal",
        "empresa",
        "ativo",
        "porta",
        "mac_address",
        "atualizado_em",
    )
    list_filter = ("tipo", "canal", "ativo", "empresa")
    search_fields = ("nome", "numero_serie", "identificador_fisico", "porta", "mac_address")
    ordering = ("nome",)


@admin.register(SessaoDispositivo)
class SessaoDispositivoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dispositivo",
        "empresa",
        "empregado",
        "furo",
        "status",
        "iniciado_em",
        "terminado_em",
    )
    list_filter = ("status", "empresa", "dispositivo__tipo", "dispositivo__canal")
    search_fields = (
        "id",
        "dispositivo__nome",
        "empregado__nome",
        "furo__nome",
        "mensagem_erro",
    )
    ordering = ("-iniciado_em",)


@admin.register(LeituraBrutaDispositivo)
class LeituraBrutaDispositivoAdmin(admin.ModelAdmin):
    list_display = ("id", "sessao", "empresa", "sequencia", "recebido_em")
    list_filter = ("empresa", "recebido_em")
    search_fields = ("id", "sessao__id", "payload_texto", "payload_hex")
    ordering = ("-recebido_em",)


@admin.register(LeituraDispositivo)
class LeituraDispositivoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sessao",
        "empresa",
        "timestamp_device",
        "profundidade_m",
        "inclinacao_deg",
        "azimute_deg",
        "qualidade",
        "criado_em",
    )
    list_filter = ("empresa", "qualidade", "criado_em")
    search_fields = ("id", "sessao__id", "payload_texto")
    ordering = ("-timestamp_device", "-criado_em")


@admin.register(LeituraDispositivoMedicaoLink)
class LeituraDispositivoMedicaoLinkAdmin(admin.ModelAdmin):
    list_display = ("leitura", "medicao")
    search_fields = ("leitura__id", "medicao__id")


@admin.register(SurveyShot)
class SurveyShotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sessao",
        "empresa",
        "furo",
        "profundidade",
        "inclinacao",
        "azimute",
        "valido",
        "origem",
        "criado_em",
    )
    list_filter = ("empresa", "valido", "origem", "criado_em")
    search_fields = ("id", "sessao__id", "furo__nome")
    ordering = ("-criado_em",)
