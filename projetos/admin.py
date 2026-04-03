from django.contrib import admin
from .models import Projeto, Furo, Empregados, Maquina, Material

# Register your models here.

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cliente', 'status', 'data_inicio')

@admin.register(Furo)
class FuroAdmin(admin.ModelAdmin):
    list_display = ('id', 'projeto', 'profundidade_alvo', 'profundidade_atual', 'estado')

@admin.register(Empregados)
class EmpregadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'projeto', 'funcao')

@admin.register(Maquina)
class MaquinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'modelo', 'estado')

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nome', 'projeto', 'quantidade', 'estado')
