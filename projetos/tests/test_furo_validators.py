from django.core.exceptions import ValidationError
from django.test import TestCase

from projetos.forms.furo import FuroCreateForm
from projetos.models import Furo

from .helpers import criar_empresa, criar_projeto


class FuroValidatorsTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Validação Furo")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Validação")

    def test_modelo_rejeita_inclinacao_positiva_em_furo_superficie(self):
        furo = Furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Superfície Inválido",
            tipo="superficie",
            profundidade_inicial=0,
            profundidade_alvo_inicial=10,
            profundidade_alvo_atual=10,
            profundidade_atual=0,
            inclinacao_planeada_inicial=5,
            inclinacao_planeada_atual=5,
            inclinacao_real_atual=5,
        )

        with self.assertRaises(ValidationError) as contexto:
            furo.full_clean()

        erros = contexto.exception.message_dict
        self.assertIn("inclinacao_planeada_inicial", erros)
        self.assertIn("inclinacao_planeada_atual", erros)
        self.assertIn("inclinacao_real_atual", erros)

    def test_formulario_usa_mesma_regra_de_inclinacao_para_furo_superficie(self):
        form = FuroCreateForm(
            data={
                "projeto": str(self.projeto.pk),
                "tipo": "superficie",
                "nome": "Furo Superfície Form",
                "estado": "ativo",
                "profundidade_inicial": "0",
                "profundidade_alvo_inicial": "10",
                "inclinacao_planeada_inicial": "4",
                "azimute_planeado_inicial": "120",
                "magnetismo": "0",
                "latitude": "",
                "longitude": "",
                "altitude": "",
                "origem_este": "0",
                "origem_norte": "0",
                "origem_tvd": "0",
                "sistema_coordenadas": "local",
                "localizacao": "",
                "local_sondagem": "",
                "detalhes": "",
            },
            empresa=self.empresa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("inclinacao_planeada_inicial", form.errors)
