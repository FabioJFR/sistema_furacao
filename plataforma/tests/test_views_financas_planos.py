from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    Plano,
    SubscricaoEmpresa,
)


class PlataformaFinancasPlanosViewsTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome="Empresa Financeira",
            nome_comercial="Empresa Financeira",
            status="ativa",
            ativo=True,
        )
        self.plano = Plano.objects.create(
            nome="Plano Financeiro Base",
            tipo="empresa",
            preco_mensal=Decimal("49.90"),
            preco_anual=Decimal("499.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 12],
        )
        self.subscricao = SubscricaoEmpresa.objects.create(
            empresa=self.empresa,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("49.90"),
        )
        self.pagamento = PagamentoEmpresa.objects.create(
            empresa=self.empresa,
            subscricao=self.subscricao,
            descricao="Pagamento teste",
            valor=Decimal("0.00"),
            estado="pendente",
        )

    def _criar_user_com_perfil(self, *, username, tipo_acesso, is_superuser=False):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123",
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
        PerfilPlataforma.objects.create(
            user=user,
            tipo_acesso=tipo_acesso,
            empresa=self.empresa if tipo_acesso == "empresa_admin" else None,
            ativo=True,
        )
        return user

    def test_platform_admin_consegue_criar_e_alternar_plano(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_planos",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_create = self.client.post(
            reverse("plataforma:plano_create"),
            data={
                "nome": "Plano Novo Teste",
                "descricao": "Plano criado em teste",
                "tipo": "individual",
                "preco_mensal": "9.90",
                "preco_anual": "99.00",
                "limite_empregados": "10",
                "limite_projetos": "4",
                "limite_furos": "20",
                "limite_armazenamento_gb": "5",
                "acesso_painel_empregado": "on",
                "ativo": "on",
                "periodos_cobranca_disponiveis": ["1", "12"],
            },
        )
        plano_novo = Plano.objects.get(nome="Plano Novo Teste")
        response_toggle = self.client.post(reverse("plataforma:plano_toggle_ativo", args=[plano_novo.pk]))

        self.assertRedirects(response_create, reverse("plataforma:plano_list"))
        self.assertRedirects(response_toggle, reverse("plataforma:plano_list"))
        plano_novo.refresh_from_db()
        self.assertFalse(plano_novo.ativo)
        self.assertEqual(plano_novo.tipo, "individual")
        self.assertFalse(plano_novo.permite_multiplos_utilizadores)
        self.assertFalse(plano_novo.acesso_dashboard_empresa)

    def test_empresa_admin_nao_acede_a_planos_nem_financas(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_financas",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response_planos = self.client.get(reverse("plataforma:plano_list"))
        response_financas = self.client.get(reverse("plataforma:financas_saida_list"))

        self.assertRedirects(
            response_planos,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            response_financas,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

    def test_platform_admin_regista_saida_financeira_sem_aceder_paypal(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_financas",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_saida = self.client.post(
            reverse("plataforma:financas_saida_list"),
            data={
                "categoria": "despesa_servidor",
                "metodo_pagamento": "manual",
                "valor_bruto": "25.00",
                "valor_desconto": "0.00",
                "valor_imposto": "5.00",
                "moeda": "EUR",
                "descricao": "Servidor mensal",
                "numero_documento": "DOC-1",
                "entidade_nome": "",
                "referencia": "REF-1",
                "data_competencia": "2026-05-24",
                "data_vencimento": "2026-05-30",
                "estado": "pendente",
                "observacoes": "Registo de teste",
            },
        )
        response_paypal = self.client.get(reverse("plataforma:financas_paypal_config"))
        response_checkout = self.client.get(
            reverse("plataforma:financas_paypal_checkout_pagamento", args=[self.pagamento.pk])
        )

        self.assertRedirects(response_saida, reverse("plataforma:financas_saida_list"))
        movimento = MovimentoFinanceiroPlataforma.objects.get(descricao="Servidor mensal")
        self.assertEqual(movimento.natureza_fluxo, "saida")
        self.assertEqual(movimento.valor, Decimal("30.00"))
        self.assertEqual(movimento.entidade_nome, "Plataforma")
        self.assertRedirects(response_paypal, reverse("plataforma:financas_analytics"))
        self.assertRedirects(response_checkout, reverse("plataforma:subscricao_list"))
        self.pagamento.refresh_from_db()
        self.assertEqual(self.pagamento.estado, "pendente")

    def test_platform_admin_consulta_entrada_financeira_com_contexto_padronizado(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_financas_entrada",
            tipo_acesso="platform_admin",
        )
        MovimentoFinanceiroPlataforma.objects.create(
            empresa=self.empresa,
            plano=self.plano,
            subscricao=self.subscricao,
            tipo_movimento="cobranca",
            natureza_fluxo="entrada",
            categoria="subscricao",
            metodo_pagamento="manual",
            valor=Decimal("49.90"),
            valor_bruto=Decimal("49.90"),
            moeda="EUR",
            descricao="Cobrança mensal",
            estado="pendente",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:financas_entrada_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["tipo_pagina"], "entrada")
        self.assertEqual(response.context["total_movimentos"], 1)
        self.assertEqual(response.context["total_valor"], Decimal("49.90"))
        self.assertIn("form", response.context)

    def test_superuser_consegue_configurar_paypal_e_checkout_gratuito(self):
        user = self._criar_user_com_perfil(
            username="super_financas",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response_config = self.client.post(
            reverse("plataforma:financas_paypal_config"),
            data={
                "paypal_email": "paypal@example.com",
                "paypal_password": "segredo",
                "ativo": "on",
            },
        )
        response_checkout = self.client.get(
            reverse("plataforma:financas_paypal_checkout_pagamento", args=[self.pagamento.pk])
        )

        self.assertRedirects(response_config, reverse("plataforma:financas_paypal_config"))
        self.assertRedirects(response_checkout, reverse("plataforma:subscricao_list"))
        self.pagamento.refresh_from_db()
        self.subscricao.refresh_from_db()
        self.empresa.refresh_from_db()
        self.assertEqual(self.pagamento.estado, "pago")
        self.assertEqual(self.subscricao.estado, "ativa")
        self.assertEqual(self.empresa.status, "ativa")
