from django.urls import path

from . import views


app_name = "inspecao_ai"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("chatbox/", views.chatbox, name="chatbox"),
    path("biblioteca-pdf/", views.biblioteca_pdf, name="biblioteca_pdf"),
    path("memoria-operacional/", views.memoria_operacional, name="memoria_operacional"),
    path("analises/", views.analise_list, name="analise_list"),
    path("analises/nova/", views.analise_create, name="analise_create"),
    path("analises/zonas/presets/guardar/", views.zona_preset_guardar, name="zona_preset_guardar"),
    path("analises/<uuid:pk>/", views.analise_detail, name="analise_detail"),
    path("analises/<uuid:pk>/corrigir-campos/", views.analise_corrigir_campos, name="analise_corrigir_campos"),
    path("analises/<uuid:pk>/guardar/", views.analise_guardar, name="analise_guardar"),
    path("analises/<uuid:pk>/reprocessar/", views.analise_reprocessar, name="analise_reprocessar"),
]
