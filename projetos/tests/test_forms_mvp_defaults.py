from django.test import TestCase
from django.utils import timezone

from projetos.forms import (
    FuroCreateForm,
    MaquinaForm,
    MedicaoForm,
    ProjetoForm,
    RegistoDiarioEmpregadoAdminForm,
)
from projetos.models import Maquina

from .helpers import criar_empresa, criar_furo, criar_projeto


class MvpCriticalFormDefaultsTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa()
        self.projeto = criar_projeto(empresa=self.empresa)

    def test_projeto_form_destaca_minimo_necessario(self):
        form = ProjetoForm(empresa=self.empresa)

        self.assertIn("MVP", form.fields["nome"].help_text)
        self.assertFalse(form.fields["cliente"].required)
        self.assertFalse(form.fields["cidade"].required)
        self.assertFalse(form.fields["pais"].required)

    def test_furo_create_form_aceita_defaults_de_piloto(self):
        form = FuroCreateForm(empresa=self.empresa)

        self.assertEqual(form.fields["nome"].initial, "Furo")
        self.assertEqual(form.fields["tipo"].initial, "fundo")
        self.assertEqual(form.fields["estado"].initial, "ativo")
        self.assertFalse(form.fields["profundidade_alvo_inicial"].required)
        self.assertFalse(form.fields["inclinacao_planeada_inicial"].required)

        form = FuroCreateForm(data={"projeto": str(self.projeto.pk)}, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors.as_data())
        furo = form.save()

        self.assertEqual(furo.nome, "Furo")
        self.assertEqual(furo.tipo, "fundo")
        self.assertEqual(furo.estado, "ativo")
        self.assertEqual(furo.profundidade_inicial, 0)

    def test_maquina_form_vem_pronta_para_piloto(self):
        form = MaquinaForm(empresa=self.empresa)

        self.assertEqual(form.fields["tipo"].initial, "Sonda")
        self.assertEqual(form.fields["estado"].initial, "operacional")
        self.assertEqual(form.fields["data_registo"].initial, timezone.localdate())
        self.assertFalse(form.fields["projetos"].required)
        self.assertIn("Opcional", form.fields["projetos"].help_text)

        form = MaquinaForm(data={"nome": "Sonda MVP"}, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors.as_data())
        maquina = form.save()

        self.assertEqual(maquina.empresa, self.empresa)
        self.assertEqual(maquina.estado, Maquina.ESTADO_CHOICES[0][0])

    def test_registo_admin_form_preenche_data_e_zeros_operacionais(self):
        form = RegistoDiarioEmpregadoAdminForm(empresa=self.empresa)

        self.assertEqual(form.fields["data"].initial, timezone.localdate())
        self.assertEqual(form.fields["horas_paragem"].initial, 0)
        self.assertEqual(form.fields["metros_furados"].initial, 0)
        self.assertIn("turno anterior", form.fields["data"].help_text)

    def test_medicao_form_sugere_profundidade_atual_do_furo(self):
        furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            profundidade_inicial=0,
            profundidade_alvo_inicial=100,
        )
        furo.profundidade_atual = 42
        furo.save(update_fields=["profundidade_atual"])

        form = MedicaoForm(furo=furo, empresa=self.empresa)

        self.assertTrue(form.fields["profundidade_medida"].required)
        self.assertEqual(form.fields["profundidade_medida"].initial, 42)
        self.assertIn("Campo mínimo", form.fields["profundidade_medida"].help_text)
