from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase
from django.utils import timezone

from plataforma.models import Empresa, PagamentoEmpresa, PerfilPlataforma, Plano, SubscricaoEmpresa
from plataforma.selectors.dashboard import (
    listar_ultimos_logins,
    listar_utilizadores_online,
    obter_empresas_dashboard_qs,
    obter_metricas_contas_dashboard,
    obter_metricas_empresas_dashboard,
)
from plataforma.services.financas import marcar_pagamento_como_pago
from plataforma.services.subscricoes import construir_contexto_subscricao_list
from website.services import executar_registo


class EstadoComercialEmpresaTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            nome="Plano Empresa Teste",
            tipo="empresa",
            preco_mensal=Decimal("49.90"),
            preco_anual=Decimal("499.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 12],
        )

    @patch("website.services.enviar_email_confirmacao_conta")
    def test_registo_publico_cria_empresa_em_teste_e_subscricao_pendente(self, enviar_email_mock):
        resultado = executar_registo(
            {
                "username": "empresa_demo",
                "email": "empresa-demo@example.com",
                "password1": "SenhaSegura123!",
                "password2": "SenhaSegura123!",
                "nome_empresa": "Empresa Demo",
                "nome_responsavel": "Responsável Demo",
                "tipo_conta": "empresa",
                "plano": str(self.plano.pk),
                "ciclo_subscricao": "1",
                "aceitar_termos": "on",
            }
        )

        self.assertTrue(resultado.sucesso, resultado.erros)
        empresa = Empresa.objects.get(nome="Empresa Demo")
        subscricao = SubscricaoEmpresa.objects.get(empresa=empresa)

        self.assertEqual(empresa.status, "teste")
        self.assertEqual(subscricao.estado, "pendente")
        enviar_email_mock.assert_called_once()

    def test_pagamento_confirmado_promove_empresa_e_subscricao_para_ativo(self):
        empresa = Empresa.objects.create(
            nome="Empresa Pendente",
            email="pendente@example.com",
            plano=self.plano,
            status="teste",
            ativo=True,
        )
        subscricao = SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("49.90"),
        )
        pagamento = PagamentoEmpresa.objects.create(
            empresa=empresa,
            subscricao=subscricao,
            descricao="Pagamento inicial",
            valor=Decimal("49.90"),
            estado="pendente",
        )

        marcar_pagamento_como_pago(pagamento, referencia_externa="PAYPAL-OK")

        empresa.refresh_from_db()
        subscricao.refresh_from_db()
        pagamento.refresh_from_db()

        self.assertEqual(pagamento.estado, "pago")
        self.assertEqual(subscricao.estado, "ativa")
        self.assertEqual(empresa.status, "ativa")
        self.assertTrue(empresa.ativo)

    def test_dashboard_trata_subscricao_pendente_como_empresa_em_teste(self):
        empresa = Empresa.objects.create(
            nome="Empresa Inconsistente",
            email="inconsistente@example.com",
            plano=self.plano,
            status="ativa",
            ativo=True,
        )
        SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("49.90"),
        )

        metricas = obter_metricas_empresas_dashboard(obter_empresas_dashboard_qs())

        self.assertEqual(metricas["total_empresas"], 1)
        self.assertEqual(metricas["empresas_ativas"], 0)
        self.assertEqual(metricas["empresas_teste"], 1)

    def test_subscricao_list_expoe_estado_ativacao_da_conta_admin(self):
        empresa = Empresa.objects.create(
            nome="Empresa Ativacao",
            email="ativacao@example.com",
            plano=self.plano,
            status="teste",
            ativo=True,
        )
        subscricao = SubscricaoEmpresa.objects.create(
            empresa=empresa,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("49.90"),
        )
        user = User.objects.create_user(
            username="admin_ativacao",
            email="admin-ativacao@example.com",
            password="SenhaSegura123!",
            is_active=False,
        )
        PerfilPlataforma.objects.create(
            user=user,
            tipo_acesso="empresa_admin",
            empresa=empresa,
            ativo=True,
        )

        context = construir_contexto_subscricao_list(perfil=None)

        self.assertEqual(len(context["subscricoes"]), 1)
        item = context["subscricoes"][0]
        self.assertEqual(item.pk, subscricao.pk)
        self.assertIsNotNone(item.conta_admin)
        self.assertFalse(item.conta_admin.user.is_active)
        self.assertEqual(context["contas_admin_ativadas"], 0)
        self.assertEqual(context["contas_admin_por_ativar"], 1)

    def test_dashboard_metricas_contas_e_online(self):
        empresa = Empresa.objects.create(
            nome="Empresa Online",
            email="online@example.com",
            plano=self.plano,
            status="ativa",
            ativo=True,
        )
        user = User.objects.create_user(
            username="user_online",
            email="online-user@example.com",
            password="SenhaSegura123!",
            is_active=True,
        )
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        PerfilPlataforma.objects.create(
            user=user,
            tipo_acesso="empresa_admin",
            empresa=empresa,
            ativo=True,
        )

        session = SessionStore()
        session["_auth_user_id"] = str(user.pk)
        session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        session["_auth_user_hash"] = user.get_session_auth_hash()
        session.save()

        metricas = obter_metricas_contas_dashboard()
        online = listar_utilizadores_online()
        ultimos = listar_ultimos_logins()

        self.assertEqual(metricas["contas_ativadas"], 1)
        self.assertEqual(metricas["contas_por_ativar"], 0)
        self.assertEqual(metricas["utilizadores_online_total"], 1)
        self.assertEqual(len(online), 1)
        self.assertEqual(online[0].username, "user_online")
        self.assertEqual(len(ultimos), 1)
        self.assertEqual(ultimos[0].username, "user_online")
