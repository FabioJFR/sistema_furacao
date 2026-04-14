from django.test import TestCase
from projetos.selectors.dashboard import obter_cards_dashboard
from projetos.models import Projeto, Furo, Empregados, Maquina, Material


class DashboardSelectorsTests(TestCase):
    def test_obter_cards_dashboard(self):
        Projeto.objects.create(nome="Projeto A")
        Furo.objects.create(nome="Furo A")
        Empregados.objects.create(nome="Empregado A")
        Maquina.objects.create(nome="Máquina A")
        Material.objects.create(nome="Material A", quantidade=10, stock_minimo=2)

        dados = obter_cards_dashboard()

        self.assertEqual(dados["total_projetos"], 1)
        self.assertEqual(dados["total_furos"], 1)
        self.assertEqual(dados["total_empregados"], 1)
        self.assertEqual(dados["total_maquinas"], 1)
        self.assertEqual(dados["total_materiais"], 1)