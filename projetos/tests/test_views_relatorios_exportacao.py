import io
import json
import zipfile
from datetime import date

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from projetos.models import Despesa

from .helpers import criar_empresa, criar_furo, criar_perfil, criar_projeto, criar_user


class RelatoriosExportacaoMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Exportação 1")
        self.empresa_externa = criar_empresa(nome="Empresa Exportação 2")
        self.projeto = criar_projeto(
            empresa=self.empresa,
            nome="Projeto Exportação Interno",
            cliente="Cliente Interno",
        )
        self.projeto_externo = criar_projeto(
            empresa=self.empresa_externa,
            nome="Projeto Exportação Externo",
            cliente="Cliente Externo",
        )
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Exportação Interno",
        )
        self.furo_externo = criar_furo(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Furo Exportação Externo",
        )
        Despesa.objects.create(
            empresa=self.empresa,
            furo=self.furo,
            tipo="furo",
            categoria="outros",
            descricao="Despesa exportação interna",
            valor=125,
            data=date(2026, 5, 12),
        )
        Despesa.objects.create(
            empresa=self.empresa_externa,
            furo=self.furo_externo,
            tipo="furo",
            categoria="outros",
            descricao="Despesa exportação externa",
            valor=999,
            data=date(2026, 5, 12),
        )
        self.user = criar_user(username="admin_exportacoes")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def test_dashboard_mostra_apenas_filtros_e_contagens_da_empresa_atual(self):
        response = self.client.get(reverse("projetos:relatorios_exportacao"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.projeto.nome)
        self.assertContains(response, self.furo.nome)
        self.assertContains(response, "1 registos")
        self.assertNotContains(response, self.projeto_externo.nome)
        self.assertNotContains(response, self.furo_externo.nome)

    @override_settings(SF_MVP_OPERACIONAL_FOCUS=True)
    def test_dashboard_em_mvp_separa_exportacoes_tecnicas_de_pos_mvp(self):
        response = self.client.get(reverse("projetos:relatorios_exportacao"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relatório técnico do turno em primeiro lugar")
        self.assertContains(response, "Exportações de terreno")
        self.assertContains(response, "Exportações complementares")
        self.assertContains(response, "Filtro pós-MVP")

        html = response.content.decode("utf-8")
        self.assertLess(html.index("Exportações de terreno"), html.index("Exportações complementares"))
        self.assertLess(html.index("Registos"), html.index("Despesas"))

    def test_download_csv_de_projetos_nao_exporta_projetos_de_outra_empresa(self):
        response = self.client.get(reverse("projetos:relatorios_download", args=["projetos", "csv"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertContains(response, self.projeto.nome)
        self.assertContains(response, "Cliente Interno")
        self.assertNotContains(response, self.projeto_externo.nome)
        self.assertNotContains(response, "Cliente Externo")

    def test_download_json_de_despesas_nao_exporta_despesas_de_outra_empresa(self):
        response = self.client.get(reverse("projetos:relatorios_download", args=["despesas", "json"]))

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        descricoes = {row["descricao"] for row in payload["rows"]}
        self.assertEqual(payload["empresa"]["nome"], self.empresa.nome)
        self.assertIn("Despesa exportação interna", descricoes)
        self.assertNotIn("Despesa exportação externa", descricoes)

    def test_download_tudo_json_zip_inclui_apenas_dados_da_empresa_atual(self):
        response = self.client.get(reverse("projetos:relatorios_download_tudo", args=["json"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
            nomes = zip_file.namelist()
            projetos_file = next(nome for nome in nomes if "projetos" in nome)
            despesas_file = next(nome for nome in nomes if "despesas" in nome)
            projetos_payload = json.loads(zip_file.read(projetos_file).decode("utf-8"))
            despesas_payload = json.loads(zip_file.read(despesas_file).decode("utf-8"))

        nomes_projetos = {row["nome"] for row in projetos_payload["rows"]}
        descricoes_despesas = {row["descricao"] for row in despesas_payload["rows"]}
        self.assertIn(self.projeto.nome, nomes_projetos)
        self.assertNotIn(self.projeto_externo.nome, nomes_projetos)
        self.assertIn("Despesa exportação interna", descricoes_despesas)
        self.assertNotIn("Despesa exportação externa", descricoes_despesas)

    def test_filtro_com_projeto_externo_nao_vaza_dados_nem_nome_no_ficheiro(self):
        response = self.client.get(
            reverse("projetos:relatorios_download", args=["projetos", "csv"]),
            {"projeto": str(self.projeto_externo.pk)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.projeto.nome)
        self.assertNotContains(response, self.projeto_externo.nome)
        self.assertNotIn(
            "projeto-exportacao-externo",
            response["Content-Disposition"],
        )

    def test_dataset_ou_formato_invalidos_devolvem_404(self):
        response_dataset = self.client.get(reverse("projetos:relatorios_download", args=["invalido", "csv"]))
        response_formato = self.client.get(reverse("projetos:relatorios_download", args=["projetos", "xml"]))
        response_zip_formato = self.client.get(reverse("projetos:relatorios_download_tudo", args=["xml"]))

        self.assertEqual(response_dataset.status_code, 404)
        self.assertEqual(response_formato.status_code, 404)
        self.assertEqual(response_zip_formato.status_code, 404)
