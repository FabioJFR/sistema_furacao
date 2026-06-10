from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PlatformAdminNavigationTests(SimpleTestCase):
    def _render_menu(self, *, is_superuser, sf_mvp_operacional_focus=False):
        user = SimpleNamespace(is_authenticated=True, is_superuser=is_superuser)
        return render_to_string(
            "projetos/base.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_platform_admin": True,
                "is_admin_user": False,
                "is_empregado_user": False,
                "sf_mvp_operacional_focus": sf_mvp_operacional_focus,
            },
        )

    def test_superuser_nao_ve_atalhos_operacionais_no_menu_principal(self):
        html = self._render_menu(is_superuser=True)

        self.assertNotIn('aria-label="Abrir menu Operação"', html)
        self.assertNotIn('aria-label="Abrir menu Registos"', html)
        self.assertNotIn('aria-label="Abrir menu Finanças"', html)
        self.assertNotIn('aria-label="Abrir menu Analytics"', html)
        self.assertNotIn('aria-label="Abrir menu Gestão"', html)
        self.assertIn('aria-label="Abrir menu Plataforma"', html)

    def test_platform_admin_nao_superuser_mantem_atalhos_operacionais(self):
        html = self._render_menu(is_superuser=False)

        self.assertIn('aria-label="Abrir menu Operação"', html)
        self.assertIn('aria-label="Abrir menu Registos"', html)
        self.assertIn('aria-label="Abrir menu Finanças"', html)
        self.assertIn('aria-label="Abrir menu Analytics"', html)
        self.assertIn('aria-label="Abrir menu Gestão"', html)

    def test_empregado_nao_ve_configuracoes_no_submenu_operacao(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        html = render_to_string(
            "projetos/base.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_platform_admin": False,
                "is_admin_user": False,
                "is_empregado_user": True,
                "perfil_plataforma": SimpleNamespace(tipo_acesso="empregado"),
                "empregado_menu_funcao": "operador",
                "sf_mvp_operacional_focus": True,
            },
        )

        self.assertIn("Meus Furos", html)
        self.assertNotIn("Minhas Configurações", html)
        self.assertNotIn("Histórico Configurações", html)

    def test_empresa_admin_em_foco_mvp_ve_menu_operacional_enxuto(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        html = render_to_string(
            "projetos/base.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_platform_admin": False,
                "is_admin_user": True,
                "is_empregado_user": False,
                "sf_mvp_operacional_focus": True,
            },
        )

        self.assertIn('aria-label="Abrir menu Operação"', html)
        self.assertIn('aria-label="Abrir menu Registos"', html)
        self.assertIn("Planeamento", html)
        self.assertNotIn('aria-label="Abrir menu Gestão"', html)
        self.assertNotIn('aria-label="Abrir menu Finanças"', html)
        self.assertNotIn('aria-label="Abrir menu Analytics"', html)
        self.assertNotIn("Clientes &amp; Contratos", html)
        self.assertNotIn("Compras &amp; Fornecedores", html)

    def test_conta_individual_em_foco_mvp_nao_ve_despesas_no_menu_operacao(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        html = render_to_string(
            "projetos/base.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_platform_admin": False,
                "is_admin_user": False,
                "is_empregado_user": True,
                "perfil_plataforma": SimpleNamespace(tipo_acesso="individual"),
                "empregado_menu_funcao": "operador",
                "sf_mvp_operacional_focus": True,
            },
        )

        self.assertIn("Meus Furos", html)
        self.assertNotIn("Minhas Despesas", html)
