from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from projetos.models import Despesa, Maquina
from projetos.tests.helpers import criar_empresa, criar_furo, criar_projeto


class DespesaModelTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa()
        self.projeto = criar_projeto(empresa=self.empresa)
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto)
        self.maquina = Maquina.objects.create(
            empresa=self.empresa,
            nome="Sonda 01",
        )

    def test_despesa_tipo_servicos_sem_associacao_e_valida(self):
        despesa = Despesa(
            empresa=self.empresa,
            categoria="outros",
            tipo="servicos",
            descricao="Serviço externo",
            valor=150.0,
            data=date(2026, 5, 10),
        )

        despesa.full_clean()

    def test_despesa_tipo_maquina_exige_maquina(self):
        despesa = Despesa(
            empresa=self.empresa,
            categoria="manutencao",
            tipo="maquina",
            descricao="Despesa de máquina sem ligação",
            valor=75.0,
            data=date(2026, 5, 10),
        )

        with self.assertRaises(ValidationError) as ctx:
            despesa.full_clean()

        self.assertIn("maquina", ctx.exception.message_dict)

    def test_despesa_tipo_maquina_com_maquina_e_valida(self):
        despesa = Despesa(
            empresa=self.empresa,
            categoria="manutencao",
            tipo="maquina",
            descricao="Mudança de peça",
            valor=220.0,
            data=date(2026, 5, 10),
            maquina=self.maquina,
        )

        despesa.full_clean()
