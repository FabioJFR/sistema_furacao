from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import reverse


class DashboardPerfisTemplateTests(SimpleTestCase):
    def _contexto_base(self, *, tipo_acesso):
        user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            username="utilizador_teste",
        )
        return {
            "request": SimpleNamespace(user=user),
            "user": user,
            "is_platform_admin": False,
            "is_admin_user": False,
            "is_empregado_user": True,
            "perfil_plataforma": SimpleNamespace(tipo_acesso=tipo_acesso),
            "empregado_menu_funcao": "operador",
            "sf_mvp_operacional_focus": True,
        }

    def test_dashboard_individual_em_foco_mvp_prioriza_acoes_de_terreno(self):
        contexto = self._contexto_base(tipo_acesso="individual")
        contexto.update({
            "individual": SimpleNamespace(
                nome="Profissional Independente",
                especialidade="Perfuração",
                ativo=True,
            ),
            "horas_total": 14,
            "metros_total": 32,
            "total_registos": 3,
        })

        html = render_to_string("projetos/area_individual.html", contexto)

        self.assertIn("Acessos rápidos", html)
        self.assertIn(reverse("projetos:meus_furos_empregado"), html)
        self.assertIn(reverse("projetos:medicao_list_empregado"), html)
        self.assertIn(reverse("projetos:material_create_empregado"), html)
        self.assertIn(reverse("projetos:meus_dados_empregado"), html)
        self.assertNotIn(reverse("projetos:despesa_create_empregado"), html)
        self.assertNotIn(reverse("projetos:despesa_list_empregado"), html)

    def test_dashboard_individual_modo_completo_mantem_despesas(self):
        contexto = self._contexto_base(tipo_acesso="individual")
        contexto["sf_mvp_operacional_focus"] = False
        contexto.update({
            "individual": SimpleNamespace(
                nome="Profissional Independente",
                especialidade="Perfuração",
                ativo=True,
            ),
            "horas_total": 14,
            "metros_total": 32,
            "total_registos": 3,
        })

        html = render_to_string("projetos/area_individual.html", contexto)

        self.assertIn(reverse("projetos:despesa_create_empregado"), html)
        self.assertIn(reverse("projetos:despesa_list_empregado"), html)

    def test_dashboard_empregado_agrupa_fluxos_em_acessos_rapidos(self):
        contexto = self._contexto_base(tipo_acesso="empregado")
        contexto.update({
            "empregado": SimpleNamespace(
                nome="Operador",
                empresa=None,
                projetos_atuais=[],
            ),
            "horas_hoje": 0,
            "horas_mes": 0,
            "horas_total": 0,
            "metros_hoje": 0,
            "metros_total": 0,
            "total_furos": 0,
            "media_metros_hora": 0,
            "media_metros_dia": 0,
            "ultimos_registos": [],
            "furos_trabalhados": [],
            "turno_referencia": None,
            "ultimo_turno_furo_referencia": None,
            "grafico_labels": [],
            "grafico_metros": [],
            "grafico_horas": [],
            "grafico_produtividade": [],
        })

        html = render_to_string("projetos/area_empregado.html", contexto)

        self.assertIn("Rotina operacional", html)
        self.assertIn("Preparação do turno", html)
        self.assertIn(reverse("projetos:calendario_turnos_empregado"), html)
        self.assertIn(reverse("projetos:meus_projetos_empregado"), html)
        self.assertIn(reverse("projetos:meus_furos_empregado"), html)
        self.assertIn(reverse("projetos:materiais_disponiveis_empregado"), html)
        self.assertIn(reverse("projetos:medicao_list_empregado"), html)
        self.assertIn(reverse("projetos:avaria_maquina_create_empregado"), html)
        self.assertNotIn(reverse("projetos:configuracao_perfuracao_list_empregado"), html)
