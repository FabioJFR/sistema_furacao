from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class DashboardEmpresaTemplateTests(SimpleTestCase):
    def _contexto_base(self, *, sf_mvp_operacional_focus):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        return {
            "request": SimpleNamespace(user=user),
            "user": user,
            "is_platform_admin": False,
            "is_admin_user": True,
            "is_empregado_user": False,
            "sf_mvp_operacional_focus": sf_mvp_operacional_focus,
            "total_projetos": 1,
            "total_furos": 2,
            "total_empregados": 2,
            "total_empregados_pendentes": 0,
            "total_avarias_maquinas_abertas": 0,
            "total_maquinas": 1,
            "total_materiais": 3,
            "total_registos": 4,
            "projetos": [],
        }

    def test_dashboard_empresa_em_foco_mvp_mostra_centro_operacional(self):
        html = render_to_string(
            "projetos/dashboard.html",
            self._contexto_base(sf_mvp_operacional_focus=True),
        )

        self.assertIn("MVP operacional", html)
        self.assertIn("Painel de controlo do terreno", html)
        self.assertIn("Projetos e Furos", html)
        self.assertIn("Registos", html)
        self.assertIn("Planeamento", html)
        self.assertIn("Máquinas", html)
        self.assertIn("Materiais", html)
        self.assertIn("Medições", html)
        self.assertIn("Criar projeto", html)
        self.assertIn("Lançar registos", html)

    def test_dashboard_empresa_modo_completo_nao_mostra_centro_mvp(self):
        html = render_to_string(
            "projetos/dashboard.html",
            self._contexto_base(sf_mvp_operacional_focus=False),
        )

        self.assertNotIn("MVP operacional", html)
        self.assertNotIn("Painel de controlo do terreno", html)
