# projetos/urls/registos.py
from django.urls import path
from projetos import views


urlpatterns = [
    # ---------------- REGISTOS DIÁRIOS EMPREGADO ----------------
    path("meus/", views.registo_diario_list, name="registo_diario_list"),
    path("meus/relatorios/", views.relatorio_turno_list, name="relatorio_turno_list"),
    path("meus/relatorios/exportar/csv/", views.relatorio_turno_export_csv, name="relatorio_turno_export_csv"),
    path("meus/relatorios/exportar/xlsx/", views.relatorio_turno_export_xlsx, name="relatorio_turno_export_xlsx"),
    path("meus/relatorios/exportar/pdf/", views.relatorio_turno_export_pdf_consolidado, name="relatorio_turno_export_pdf_consolidado"),
    path("meus/relatorios/exportar/zip/", views.relatorio_turno_export_zip, name="relatorio_turno_export_zip"),
    path("meus/novo/", views.registo_diario_create, name="registo_diario_create"),
    path("meus/<uuid:pk>/editar/", views.registo_diario_update, name="registo_diario_update"),
    path("meus/relatorios/<uuid:pk>/", views.relatorio_turno_detail, name="relatorio_turno_detail"),
    path("meus/relatorios/<uuid:pk>/editar/", views.relatorio_turno_update, name="relatorio_turno_update"),
    path("meus/relatorios/<uuid:pk>/pdf/", views.relatorio_turno_pdf, name="relatorio_turno_pdf"),

    # ---------------- REGISTOS DIÁRIOS ADMIN ----------------
    path("admin/", views.registos_admin_list, name="registos_admin_list"),
    path("admin/relatorios/", views.relatorio_turno_admin_list, name="relatorio_turno_admin_list"),
    path("admin/relatorios/exportar/csv/", views.relatorio_turno_admin_export_csv, name="relatorio_turno_admin_export_csv"),
    path("admin/relatorios/exportar/xlsx/", views.relatorio_turno_admin_export_xlsx, name="relatorio_turno_admin_export_xlsx"),
    path("admin/relatorios/exportar/pdf/", views.relatorio_turno_admin_export_pdf_consolidado, name="relatorio_turno_admin_export_pdf_consolidado"),
    path("admin/relatorios/exportar/zip/", views.relatorio_turno_admin_export_zip, name="relatorio_turno_admin_export_zip"),
    path("admin/novo/", views.registo_diario_create, name="registo_admin_create"),
    path("admin/<uuid:pk>/editar/", views.registo_admin_update, name="registo_admin_update"),
    path("admin/relatorios/<uuid:pk>/", views.relatorio_turno_admin_detail, name="relatorio_turno_admin_detail"),
    path("admin/relatorios/<uuid:pk>/editar/", views.relatorio_turno_admin_update, name="relatorio_turno_admin_update"),
    path("admin/relatorios/<uuid:pk>/pdf/", views.relatorio_turno_admin_pdf, name="relatorio_turno_admin_pdf"),
]
