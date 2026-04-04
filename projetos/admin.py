from django.contrib import admin
from .models import Projeto, Furo, Empregados, EmpregadoProjeto, EmpregadoFicheiro, Maquina, Material

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cliente', 'status', 'data_inicio')
    search_fields = ('nome', 'cliente', 'cidade', 'pais')
    list_filter = ('status', 'pais')


@admin.register(Furo)
class FuroAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'projeto', 'profundidade_alvo', 'profundidade_atual', 'estado')
    search_fields = ('nome', 'projeto__nome', 'localizacao', 'local_sondagem')
    list_filter = ('estado', 'tipo', 'projeto')


@admin.register(Empregados)
class EmpregadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'funcao', 'email', 'mostrar_projetos_atuais')
    search_fields = ('nome', 'funcao', 'email', 'nif', 'telefone')

    def mostrar_projetos_atuais(self, obj):
        projetos = obj.projetos_atuais
        return ", ".join([p.nome for p in projetos]) if projetos else "-"
    mostrar_projetos_atuais.short_description = "Projetos atuais"


@admin.register(EmpregadoProjeto)
class EmpregadoProjetoAdmin(admin.ModelAdmin):
    list_display = ('empregado', 'projeto', 'data_inicio', 'data_fim', 'ativo')
    list_filter = ('ativo', 'projeto')
    search_fields = ('empregado__nome', 'projeto__nome')

@admin.register(EmpregadoFicheiro)
class EmpregadoFicheiroAdmin(admin.ModelAdmin):
    list_display = ('empregado', 'tipo', 'titulo', 'data_upload')
    list_filter = ('tipo',)
    search_fields = ('empregado__nome', 'titulo')


@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modelo', 'estado')
    search_fields = ('nome', 'modelo', 'numero_serie', 'matricula')
    list_filter = ('estado',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nome', 'projeto', 'quantidade', 'estado')
    search_fields = ('nome', 'projeto__nome', 'tipo', 'numero_serie')
    list_filter = ('estado', 'projeto')
