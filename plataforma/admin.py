from django.contrib import admin
from django.utils.html import format_html

from plataforma.models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "status", "ativo", "logo_preview_admin")
    list_filter = ("status", "ativo", "pais", "cidade")
    search_fields = ("nome", "nome_comercial", "email", "nif")
    readonly_fields = ("logo_preview_admin", "criado_em", "atualizado_em")
    fieldsets = (
        ("Dados principais", {
            "fields": (
                "nome",
                "nome_comercial",
                "logo",
                "logo_preview_admin",
                "status",
                "ativo",
                "plano",
            ),
        }),
        ("Contactos", {
            "fields": ("email", "telefone", "nif", "pais", "cidade", "morada"),
        }),
        ("Responsável", {
            "fields": ("responsavel_nome", "responsavel_email", "responsavel_telefone"),
        }),
        ("Datas", {
            "fields": ("data_inicio", "data_fim", "criado_em", "atualizado_em"),
        }),
    )

    @admin.display(description="Logo")
    def logo_preview_admin(self, obj):
        if not obj.logo:
            return "—"
        return format_html(
            '<img src="{}" style="height:40px;width:auto;border-radius:6px;border:1px solid #ddd;" />',
            obj.logo.url,
        )
