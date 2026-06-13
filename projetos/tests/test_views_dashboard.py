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
            "mvp_piloto": {
                "percentagem": 60,
                "concluidos": 6,
                "total": 10,
                "itens": [
                    {
                        "titulo": "1 projeto criado",
                        "descricao": "Primeira frente de trabalho aberta.",
                        "atual": 1,
                        "meta": 1,
                        "concluido": True,
                        "url_name": "projetos:projeto_list",
                    },
                    {
                        "titulo": "Relatório técnico exportável",
                        "descricao": "Registos técnicos prontos para consulta/exportação.",
                        "atual": 0,
                        "meta": 1,
                        "concluido": False,
                        "url_name": "projetos:relatorio_turno_admin_list",
                    },
                ],
            },
            "mvp_roteiro_piloto": {
                "fases": [
                    {
                        "numero": 1,
                        "titulo": "Preparar base real",
                        "descricao": "Criar empresa, projeto, furos, empregados e máquina.",
                        "resultado": "Equipa pronta para iniciar piloto.",
                    },
                    {
                        "numero": 2,
                        "titulo": "Simular um turno completo",
                        "descricao": "Registar produção, materiais, medição e ocorrência.",
                        "resultado": "Turno rastreável.",
                    },
                ],
                "criterios_go": ["Checklist do piloto com pelo menos 80% concluído."],
                "criterios_no_go": ["Relatório técnico não explica claramente o turno."],
            },
            "projetos": [],
        }

    def test_dashboard_empresa_em_foco_mvp_mostra_centro_operacional(self):
        html = render_to_string(
            "projetos/dashboard.html",
            self._contexto_base(sf_mvp_operacional_focus=True),
        )

        self.assertIn("MVP operacional", html)
        self.assertIn("Painel de controlo do terreno", html)
        self.assertIn("Validação mínima do MVP de terreno", html)
        self.assertIn("60%", html)
        self.assertIn("Projetos e Furos", html)
        self.assertIn("Registos", html)
        self.assertIn("Planeamento", html)
        self.assertIn("Máquinas", html)
        self.assertIn("Materiais", html)
        self.assertIn("Medições", html)
        self.assertIn("1 projeto criado", html)
        self.assertIn("Relatório técnico exportável", html)
        self.assertIn("Como validar o MVP em dados reais", html)
        self.assertIn("Preparar base real", html)
        self.assertIn("Go: avançar piloto", html)
        self.assertIn("No-go: corrigir antes", html)

    def test_dashboard_empresa_modo_completo_nao_mostra_centro_mvp(self):
        html = render_to_string(
            "projetos/dashboard.html",
            self._contexto_base(sf_mvp_operacional_focus=False),
        )

        self.assertNotIn("MVP operacional", html)
        self.assertNotIn("Painel de controlo do terreno", html)
        self.assertNotIn("Como validar o MVP em dados reais", html)
