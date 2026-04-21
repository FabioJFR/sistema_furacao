from django.contrib import admin

from geologia.models import AnexoLogGeologico, LogGeologicoFuro, MissaoDroneFuro


@admin.register(MissaoDroneFuro)
class MissaoDroneFuroAdmin(admin.ModelAdmin):
    list_display = ("titulo", "furo", "empresa", "status", "data_voo", "piloto_nome", "numero_fotos")
    search_fields = ("titulo", "furo__nome", "empresa__nome", "piloto_nome", "firmware", "app_origem")
    list_filter = ("status", "data_voo", "empresa")


@admin.register(LogGeologicoFuro)
class LogGeologicoFuroAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "furo",
        "empresa",
        "intervalo_de",
        "intervalo_ate",
        "litologia_principal",
        "data_registo",
    )
    search_fields = ("titulo", "furo__nome", "litologia_principal", "litologia_secundaria")
    list_filter = ("data_registo", "empresa", "litologia_principal")


@admin.register(AnexoLogGeologico)
class AnexoLogGeologicoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "log", "tipo", "empresa", "criado_em")
    search_fields = ("titulo", "log__titulo", "log__furo__nome")
    list_filter = ("tipo", "empresa", "criado_em")
