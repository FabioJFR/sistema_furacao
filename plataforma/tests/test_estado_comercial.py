from decimal import Decimal

from django.test import TestCase

from plataforma.models import Empresa, PagamentoEmpresa, Plano, SubscricaoEmpresa
from plataforma.selectors.dashboard import obter_empresas_dashboard_qs, obter_metricas_empresas_dashboard
from plataforma.services.financas import marcar_pagamento_como_pago
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

    def test_registo_publico_cria_empresa_em_teste_e_subscricao_pendente(self):
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

        self.assertTrue(resultado.sucesso)
        empresa = Empresa.objects.get(nome="Empresa Demo")
        subscricao = SubscricaoEmpresa.objects.get(empresa=empresa)

        self.assertEqual(empresa.status, "teste")
        self.assertEqual(subscricao.estado, "pendente")

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
