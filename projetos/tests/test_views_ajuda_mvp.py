from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from projetos.views.institucional import (
    _ajuda_por_perfil,
    _filtrar_ajuda_mvp,
    _guias_destaque_ajuda,
    obter_ajuda_contextual,
)


class AjudaMvpOperacionalTests(SimpleTestCase):
    @override_settings(SF_MVP_OPERACIONAL_FOCUS=True)
    def test_ajuda_mvp_oculta_artigos_pos_mvp(self):
        ajuda_por_perfil = _filtrar_ajuda_mvp(_ajuda_por_perfil())

        artigos_por_perfil = {
            perfil["chave"]: {artigo["titulo"] for artigo in perfil["artigos"]}
            for perfil in ajuda_por_perfil
        }

        self.assertIn("Projetos, Furos e Medições", artigos_por_perfil["empresa"])
        self.assertIn("Registos de Produção e Fichas Técnicas", artigos_por_perfil["empresa"])
        self.assertNotIn("Centro de Gestão", artigos_por_perfil["empresa"])
        self.assertNotIn("Finanças", artigos_por_perfil["empresa"])
        self.assertNotIn("Analytics, AI e 3D", artigos_por_perfil["empresa"])
        self.assertNotIn("Minhas Despesas", artigos_por_perfil["individual"])

    @override_settings(SF_MVP_OPERACIONAL_FOCUS=True)
    def test_guias_mvp_destacam_fluxo_de_terreno(self):
        titulos = {guia["titulo"] for guia in _guias_destaque_ajuda()}

        self.assertEqual(
            titulos,
            {"Arranque operacional", "Registos em detalhe", "Materiais e ocorrências"},
        )

    @override_settings(SF_MVP_OPERACIONAL_FOCUS=True)
    def test_ajuda_contextual_dashboard_aponta_para_operacao(self):
        contexto = obter_ajuda_contextual("projetos:dashboard")

        self.assertIsNotNone(contexto)
        self.assertEqual(contexto["titulo"], "Projetos, Furos e Medições")
        self.assertEqual(contexto["rota_origem"], "projetos:projeto_list")

    @override_settings(SF_MVP_OPERACIONAL_FOCUS=True)
    def test_template_ajuda_mvp_nao_promove_gestao(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        html = render_to_string(
            "projetos/ajuda.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_admin_user": True,
                "is_empregado_user": False,
                "sf_mvp_operacional_focus": True,
                "ajuda_por_perfil": _filtrar_ajuda_mvp(_ajuda_por_perfil()),
                "guias_destaque": _guias_destaque_ajuda(),
                "faq_ajuda": [],
            },
        )

        self.assertIn("Abrir Operação", html)
        self.assertIn("Arranque operacional", html)
        self.assertNotIn("Abrir Gestão", html)
        self.assertNotIn("Centro de Gestão", html)
        self.assertNotIn("Minhas Despesas", html)
