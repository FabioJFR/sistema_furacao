from datetime import date, time
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from projetos.models import (
    AgendamentoRelatorioExecutivo,
    Despesa,
    HistoricoEnvioRelatorioExecutivo,
)
from projetos.services.gestao_relatorios import EnvioRelatorioResultado

from .helpers import criar_empresa, criar_perfil, criar_projeto, criar_user


class RelatoriosExecutivosMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Relatórios 1")
        self.empresa.email = "relatorios1@example.com"
        self.empresa.responsavel_email = "gestor1@example.com"
        self.empresa.save(update_fields=["email", "responsavel_email"])
        self.empresa_externa = criar_empresa(nome="Empresa Relatórios 2")
        self.empresa_externa.email = "relatorios2@example.com"
        self.empresa_externa.responsavel_email = "gestor2@example.com"
        self.empresa_externa.save(update_fields=["email", "responsavel_email"])
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Relatório Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Relatório Externo")
        Despesa.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            tipo="projeto",
            categoria="outros",
            descricao="Despesa relatório interna",
            valor=150,
            data=date(2026, 5, 10),
        )
        Despesa.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            tipo="projeto",
            categoria="outros",
            descricao="Despesa relatório externa",
            valor=999,
            data=date(2026, 5, 10),
        )
        self.agendamento_externo = AgendamentoRelatorioExecutivo.objects.create(
            empresa=self.empresa_externa,
            ativo=True,
            frequencia="semanal",
            hora_execucao=time(8, 0),
            destinos="externo@example.com",
        )
        HistoricoEnvioRelatorioExecutivo.objects.create(
            empresa=self.empresa,
            origem="manual",
            status="sucesso",
            assunto="Histórico Interno",
            destinos="gestor1@example.com",
            enviados=1,
        )
        HistoricoEnvioRelatorioExecutivo.objects.create(
            empresa=self.empresa_externa,
            agendamento=self.agendamento_externo,
            origem="manual",
            status="sucesso",
            assunto="Histórico Externo",
            destinos="gestor2@example.com",
            enviados=1,
        )
        self.user = criar_user(username="admin_relatorios")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def test_dashboard_e_export_csv_usam_apenas_dados_da_empresa(self):
        params = {"data_inicio": "2026-05-01", "data_fim": "2026-05-31"}

        response = self.client.get(reverse("projetos:gestao_relatorios_executivos"), params)
        response_csv = self.client.get(reverse("projetos:gestao_relatorios_export_csv"), params)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.projeto.nome)
        self.assertContains(response, "Histórico Interno")
        self.assertNotContains(response, self.projeto_externo.nome)
        self.assertNotContains(response, "Histórico Externo")
        self.assertEqual(response_csv.status_code, 200)
        self.assertContains(response_csv, self.projeto.nome)
        self.assertNotContains(response_csv, self.projeto_externo.nome)
        self.assertContains(response_csv, "150.00")
        self.assertNotContains(response_csv, "999.00")

    def test_agendamento_e_criado_e_atualizado_apenas_para_empresa_atual(self):
        response = self.client.post(
            reverse("projetos:gestao_relatorios_agendamento"),
            data={
                "ativo": "on",
                "frequencia": "semanal",
                "hora_execucao": "09:30",
                "dia_semana": "2",
                "dia_mes": "10",
                "destinos": "interno@example.com",
                "incluir_csv": "on",
                "incluir_xlsx": "",
                "incluir_pdf": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        agendamento = AgendamentoRelatorioExecutivo.objects.get(empresa=self.empresa)
        self.assertTrue(agendamento.ativo)
        self.assertEqual(agendamento.destinos, "interno@example.com")
        self.agendamento_externo.refresh_from_db()
        self.assertEqual(self.agendamento_externo.destinos, "externo@example.com")

    def test_agendamento_recusa_sem_anexos_sem_alterar_estado(self):
        AgendamentoRelatorioExecutivo.objects.create(
            empresa=self.empresa,
            ativo=False,
            frequencia="mensal",
            destinos="interno-original@example.com",
        )

        response = self.client.post(
            reverse("projetos:gestao_relatorios_agendamento"),
            data={
                "ativo": "on",
                "frequencia": "mensal",
                "hora_execucao": "08:00",
                "dia_semana": "1",
                "dia_mes": "5",
                "destinos": "novo@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        agendamento = AgendamentoRelatorioExecutivo.objects.get(empresa=self.empresa)
        self.assertFalse(agendamento.ativo)
        self.assertEqual(agendamento.destinos, "interno-original@example.com")

    @patch("projetos.views.gestao_empresa.enviar_relatorio_executivo_email")
    def test_envio_email_regista_historico_apenas_na_empresa_atual(self, mock_send):
        mock_send.return_value = EnvioRelatorioResultado(enviados=1, destinos=["destino@example.com"])

        response = self.client.post(
            reverse("projetos:gestao_relatorios_enviar_email"),
            data={
                "assunto": "Relatório Manual Interno",
                "destinos": "destino@example.com",
                "incluir_csv": "on",
                "data_inicio": "2026-05-01",
                "data_fim": "2026-05-31",
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["empresa"], self.empresa)
        self.assertEqual(kwargs["destinos"], ["destino@example.com"])
        self.assertEqual(kwargs["relatorio"]["financeiro"]["despesas_total"], 150)
        self.assertTrue(
            HistoricoEnvioRelatorioExecutivo.objects.filter(
                empresa=self.empresa,
                assunto="Relatório Manual Interno",
                status="sucesso",
            ).exists()
        )
        self.assertFalse(
            HistoricoEnvioRelatorioExecutivo.objects.filter(
                empresa=self.empresa_externa,
                assunto="Relatório Manual Interno",
            ).exists()
        )

    def test_envio_email_recusa_formulario_sem_anexos_sem_criar_historico(self):
        response = self.client.post(
            reverse("projetos:gestao_relatorios_enviar_email"),
            data={
                "assunto": "Relatório Sem Anexo",
                "destinos": "destino@example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            HistoricoEnvioRelatorioExecutivo.objects.filter(
                empresa=self.empresa,
                assunto="Relatório Sem Anexo",
            ).exists()
        )
