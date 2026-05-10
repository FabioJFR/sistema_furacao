from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import AssiduidadeRegisto, NotificacaoGestao, RegistoDiarioEmpregado

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_ligacao_empregado_projeto,
    criar_perfil,
    criar_planeamento_turno,
    criar_projeto,
    criar_user,
)


class NotificacoesEmpregadoViewTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa()
        self.user = criar_user(username="empregado_notifs")
        criar_perfil(user=self.user, tipo_acesso="empregado", empresa=self.empresa)
        self.empregado = criar_empregado(
            empresa=self.empresa,
            user=self.user,
            nome="Operador Notificações",
            aprovado=True,
        )
        self.client.force_login(self.user)

    def test_lista_notificacoes_empregado_renderiza_alertas(self):
        notificacao = NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias aprovado · 10/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            detalhes="A empresa aprovou o teu pedido.",
        )

        response = self.client.get(reverse("projetos:notificacoes_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, notificacao.titulo)
        self.assertContains(response, "A empresa aprovou o teu pedido.")

    def test_get_nao_muda_estado_da_notificacao(self):
        notificacao = NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias rejeitado · 11/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
        )

        response = self.client.get(
            reverse("projetos:notificacao_empregado_estado", args=[notificacao.id, "resolvida"])
        )

        self.assertEqual(response.status_code, 302)
        notificacao.refresh_from_db()
        self.assertEqual(notificacao.estado, "aberta")

    def test_empregado_consegue_mudar_estado_da_notificacao_por_post(self):
        notificacao = NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias rejeitado · 11/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
        )

        response = self.client.post(
            reverse("projetos:notificacao_empregado_estado", args=[notificacao.id, "resolvida"])
        )

        self.assertEqual(response.status_code, 302)
        notificacao.refresh_from_db()
        self.assertEqual(notificacao.estado, "resolvida")


class AssiduidadeListViewTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa RH")
        self.admin_user = criar_user(username="admin_rh")
        criar_perfil(user=self.admin_user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.admin_user)

        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto RH")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo RH")
        self.empregado = criar_empregado(empresa=self.empresa, nome="Colaborador RH")
        criar_ligacao_empregado_projeto(empregado=self.empregado, projeto=self.projeto)

    def test_assiduidade_list_mostra_calendario_operacional_da_equipa(self):
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado,
            furo=self.furo,
            nome="Turno RH",
            data_inicio=date(2026, 5, 9),
            turno="tarde",
        )
        RegistoDiarioEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            projeto=self.projeto,
            furo=self.furo,
            data=date(2026, 5, 9),
            turno="Tarde",
            hora_inicio="14:00",
            hora_fim="22:00",
            metros_furados=4.5,
        )
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 5, 10),
            data_fim=date(2026, 5, 10),
            horas=0.0,
        )

        response = self.client.get(
            reverse("projetos:assiduidade_list"),
            {"mes": 5, "ano": 2026},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calendário operacional da equipa")
        self.assertContains(response, "Colaborador RH")
        self.assertContains(response, "Tarde")
        self.assertContains(response, "Registo criado")
        self.assertContains(response, "Férias")
