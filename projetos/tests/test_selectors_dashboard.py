from django.test import TestCase
from projetos.selectors.dashboard import obter_cards_dashboard, obter_roteiro_piloto_operacional
from projetos.models import Maquina, Material

from .helpers import criar_empresa, criar_empregado, criar_furo, criar_projeto


class DashboardSelectorsTests(TestCase):
    def test_obter_cards_dashboard(self):
        empresa = criar_empresa()
        projeto = criar_projeto(empresa=empresa, nome="Projeto A")
        criar_furo(empresa=empresa, projeto=projeto, nome="Furo A")
        criar_empregado(empresa=empresa, nome="Empregado A")
        Maquina.objects.create(empresa=empresa, nome="Máquina A")
        Material.objects.create(empresa=empresa, nome="Material A", quantidade=10, stock_minimo=2)

        dados = obter_cards_dashboard(empresa=empresa)

        self.assertEqual(dados["total_projetos"], 1)
        self.assertEqual(dados["total_furos"], 1)
        self.assertEqual(dados["total_empregados"], 1)
        self.assertEqual(dados["total_maquinas"], 1)
        self.assertEqual(dados["total_materiais"], 1)

    def test_obter_roteiro_piloto_operacional_define_fases_e_decisao(self):
        roteiro = obter_roteiro_piloto_operacional()

        self.assertEqual(len(roteiro["fases"]), 4)
        self.assertEqual(roteiro["fases"][0]["titulo"], "Preparar base real")
        self.assertIn("checklist", roteiro["criterios_go"][0].lower())
        self.assertIn("Relatório técnico", roteiro["criterios_no_go"][2])
