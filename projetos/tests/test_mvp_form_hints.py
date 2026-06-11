from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from projetos.forms.projeto import ProjetoForm


class MvpFormHintsTemplateTests(SimpleTestCase):
    def test_partial_mostra_texto_certo_por_contexto_mvp(self):
        casos = {
            "projeto": "Cria primeiro a frente de trabalho",
            "furo": "Regista o furo com o mínimo técnico útil",
            "empregado": "Cria a equipa mínima do piloto",
            "maquina": "Liga a máquina à operação real",
            "registo": "O registo diário alimenta o relatório técnico",
            "medicao": "A medição valida a leitura técnica do furo",
        }

        for contexto, texto in casos.items():
            with self.subTest(contexto=contexto):
                html = render_to_string(
                    "projetos/partials/mvp_form_hint.html",
                    {
                        "sf_mvp_operacional_focus": True,
                        "mvp_form_context": contexto,
                    },
                )

                self.assertIn("Primeiro uso do MVP", html)
                self.assertIn(texto, html)

    def test_partial_nao_aparece_em_modo_completo(self):
        html = render_to_string(
            "projetos/partials/mvp_form_hint.html",
            {
                "sf_mvp_operacional_focus": False,
                "mvp_form_context": "projeto",
            },
        )

        self.assertEqual(html.strip(), "")

    def test_formulario_projeto_inclui_orientacao_mvp(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        html = render_to_string(
            "projetos/projeto_form.html",
            {
                "request": SimpleNamespace(user=user),
                "user": user,
                "is_admin_user": True,
                "is_empregado_user": False,
                "sf_mvp_operacional_focus": True,
                "form": ProjetoForm(),
            },
        )

        self.assertIn("Primeiro uso do MVP", html)
        self.assertIn("Cria primeiro a frente de trabalho", html)
