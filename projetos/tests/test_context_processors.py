from datetime import date
from types import SimpleNamespace

from django.test import RequestFactory, TestCase

from projetos.context_processors import menu_context
from projetos.models import AssiduidadeRegisto, NotificacaoGestao

from .helpers import criar_empresa, criar_empregado, criar_perfil, criar_user


class MenuContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = criar_empresa()

    def test_menu_context_mostra_pedidos_ferias_pendentes_para_empresa_admin(self):
        user = criar_user(username="admin_empresa")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, nome="Operador RH")
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 1),
            horas=0.0,
        )

        request = self.factory.get("/")
        request.user = user

        contexto = menu_context(request)

        self.assertTrue(contexto["is_admin_user"])
        self.assertEqual(contexto["total_pedidos_ferias_pendentes_menu"], 1)

    def test_menu_context_mostra_notificacoes_abertas_para_empregado(self):
        user = criar_user(username="empregado_menu")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(
            empresa=self.empresa,
            user=user,
            nome="Operador Menu",
            aprovado=True,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=empregado,
            titulo="Pedido de férias aprovado · 01/07/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
        )

        request = self.factory.get("/")
        request.user = user

        contexto = menu_context(request)

        self.assertTrue(contexto["is_empregado_user"])
        self.assertEqual(contexto["total_notificacoes_empregado_abertas_menu"], 1)

    def test_menu_context_expoe_ajuda_contextual_para_rota_principal(self):
        user = criar_user(username="admin_contextual")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=self.empresa)

        request = self.factory.get("/app/gestao/")
        request.user = user
        request.resolver_match = SimpleNamespace(view_name="projetos:gestao_hub")

        contexto = menu_context(request)

        self.assertIsNotNone(contexto["ajuda_contextual_atual"])
        self.assertEqual(contexto["ajuda_contextual_atual"]["titulo"], "Centro de Gestão")
        self.assertIn("#gestao-centro-de-gestao", contexto["ajuda_contextual_atual"]["url"])

    def test_menu_context_ajusta_ajuda_contextual_para_rota_edicao(self):
        user = criar_user(username="admin_contextual_edicao")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=self.empresa)

        request = self.factory.get("/app/gestao/clientes-contratos/abc/editar/")
        request.user = user
        request.resolver_match = SimpleNamespace(view_name="projetos:cliente_contrato_update")

        contexto = menu_context(request)

        self.assertEqual(contexto["ajuda_contextual_atual"]["titulo"], "Clientes & Contratos")
        self.assertEqual(contexto["ajuda_contextual_atual"]["contexto_tipo"], "editar")
        self.assertEqual(contexto["ajuda_contextual_atual"]["contexto_label"], "Tutorial da edição")
