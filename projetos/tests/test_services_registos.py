from datetime import date
from decimal import Decimal

from django.test import TestCase

from projetos.forms.registo import RegistoDiarioEmpregadoForm, RelatorioTurnoForm
from projetos.models import Furo
from projetos.services.registos import criar_registo_diario

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_ligacao_empregado_projeto,
    criar_planeamento_turno,
    criar_projeto,
)


class RegistosServicesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Registos")
        self.empregado = criar_empregado(empresa=self.empresa, nome="Operador Registo")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Registos")
        criar_ligacao_empregado_projeto(empregado=self.empregado, projeto=self.projeto)
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Registos",
            tipo="superficie",
        )

    def test_relatorio_turno_form_calcula_percentagem_recuperacao(self):
        form = RelatorioTurnoForm(
            data={
                "cliente": "Cliente X",
                "numero_relatorio": "REL-1",
                "avanco_turno": "2.30",
                "testemunho_recuperado": "2.00",
                "furacoes": "[]",
                "operacoes_ocorrencias": "[]",
                "polimeros": "[]",
                "equipa_turno": "[]",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["percentagem_recuperacao"], Decimal("86.96"))

    def test_criar_registo_diario_suporta_furo_com_inclinacoes_antigas_invalidas(self):
        Furo.objects.filter(pk=self.furo.pk).update(
            inclinacao_planeada_inicial=5.0,
            inclinacao_planeada_atual=3.0,
            inclinacao_real_atual=1.0,
        )
        self.furo.refresh_from_db()

        planeamento = criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado,
            furo=self.furo,
            nome="Turno Superfície",
            data_inicio=date(2026, 5, 9),
            turno="tarde",
        )
        form = RegistoDiarioEmpregadoForm(
            data={
                "planeamento_turno": str(planeamento.id),
                "projeto": str(self.projeto.id),
                "furo": str(self.furo.id),
                "data": "2026-05-09",
                "hora_inicio": "16:00",
                "hora_fim": "00:00",
                "horas_paragem": "0",
                "tipo_paragem": "",
                "metros_furados": "8.00",
                "observacoes": "",
            },
            empregado=self.empregado,
        )
        form.instance.empregado = self.empregado
        form.instance.empresa = self.empresa

        self.assertTrue(form.is_valid(), form.errors)

        registo = criar_registo_diario(form=form, empregado=self.empregado)

        self.assertIsNotNone(registo.pk)
        self.assertEqual(registo.empregado, self.empregado)
        self.assertEqual(registo.empresa, self.empresa)
        self.furo.refresh_from_db()
        self.assertEqual(self.furo.profundidade_atual, 8.0)
        self.assertEqual(self.furo.profundidade_maxima_atingida, 8.0)
