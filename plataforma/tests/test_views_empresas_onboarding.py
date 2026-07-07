from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma, Plano, SubscricaoEmpresa
from projetos.tests.helpers import criar_empregado, criar_furo, criar_projeto


class PlataformaEmpresasOnboardingViewsTests(TestCase):
    def setUp(self):
        self.plano_base = Plano.objects.create(
            nome="Plano Empresa Base",
            tipo="empresa",
            preco_mensal=Decimal("50.00"),
            preco_anual=Decimal("500.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 12],
        )
        self.plano_novo = Plano.objects.create(
            nome="Plano Empresa Novo",
            tipo="empresa",
            preco_mensal=Decimal("80.00"),
            preco_anual=Decimal("800.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 3, 12],
        )
        self.empresa = Empresa.objects.create(
            nome="Empresa Gestão Comercial",
            nome_comercial="Empresa Gestão Comercial",
            plano=self.plano_base,
            status="teste",
            ativo=True,
        )
        self.subscricao = SubscricaoEmpresa.objects.create(
            empresa=self.empresa,
            plano=self.plano_base,
            estado="ativa",
            ciclo_cobranca="1",
            valor=Decimal("50.00"),
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 6, 1),
            proxima_renovacao=date(2026, 6, 1),
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

    def test_platform_admin_altera_plano_renovacao_e_estado_da_empresa(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_empresas",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_detail = self.client.get(reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        response_plano = self.client.post(
            reverse("plataforma:empresa_alterar_plano", args=[self.empresa.pk]),
            data={
                "plano": str(self.plano_novo.pk),
                "ciclo_subscricao": "3",
                "estado_empresa": "ativa",
            },
        )
        response_renovacao = self.client.post(
            reverse("plataforma:empresa_atualizar_renovacao", args=[self.empresa.pk]),
            data={"proxima_renovacao": "2026-09-15"},
        )
        response_toggle = self.client.post(reverse("plataforma:empresa_toggle_ativa", args=[self.empresa.pk]))

        self.assertEqual(response_detail.status_code, 200)
        self.assertContains(response_detail, self.empresa.nome)
        self.assertRedirects(response_plano, reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        self.assertRedirects(response_renovacao, reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        self.assertRedirects(response_toggle, reverse("plataforma:empresa_detail", args=[self.empresa.pk]))

        self.empresa.refresh_from_db()
        self.subscricao.refresh_from_db()
        self.assertEqual(self.empresa.plano, self.plano_novo)
        self.assertFalse(self.empresa.ativo)
        self.assertEqual(self.empresa.status, "suspensa")
        self.assertEqual(self.subscricao.plano, self.plano_novo)
        self.assertEqual(self.subscricao.ciclo_cobranca, "3")
        self.assertEqual(self.subscricao.valor, Decimal("240.00"))
        self.assertEqual(self.subscricao.proxima_renovacao, date(2026, 9, 15))
        self.assertTrue(self.subscricao.renovacao_definida_manualmente)

    def test_empresa_detail_mostra_metricas_operacionais_reais(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_empresas_metricas",
            tipo_acesso="platform_admin",
        )
        projeto = criar_projeto(empresa=self.empresa, nome="Projeto Métricas")
        criar_furo(empresa=self.empresa, projeto=projeto, nome="Furo Métricas")
        criar_empregado(empresa=self.empresa, nome="Empregado Métricas")
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:empresa_detail", args=[self.empresa.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_projetos"], 1)
        self.assertEqual(response.context["total_furos"], 1)
        self.assertEqual(response.context["total_empregados"], 1)

    def test_get_em_acoes_criticas_nao_altera_empresa(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_empresas_get",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_toggle = self.client.get(reverse("plataforma:empresa_toggle_ativa", args=[self.empresa.pk]))
        response_renovacao = self.client.get(reverse("plataforma:empresa_atualizar_renovacao", args=[self.empresa.pk]))

        self.assertRedirects(response_toggle, reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        self.assertRedirects(response_renovacao, reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        self.empresa.refresh_from_db()
        self.subscricao.refresh_from_db()
        self.assertTrue(self.empresa.ativo)
        self.assertEqual(self.empresa.status, "teste")
        self.assertEqual(self.subscricao.proxima_renovacao, date(2026, 6, 1))

    def test_empresa_admin_nao_acede_a_gestao_de_empresas(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_empresas",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response_detail = self.client.get(reverse("plataforma:empresa_detail", args=[self.empresa.pk]))
        response_alterar = self.client.post(
            reverse("plataforma:empresa_alterar_plano", args=[self.empresa.pk]),
            data={"plano": str(self.plano_novo.pk), "ciclo_subscricao": "1", "estado_empresa": "ativa"},
        )

        self.assertRedirects(
            response_detail,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            response_alterar,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.plano, self.plano_base)

    def test_platform_admin_cria_empresa_no_onboarding(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_onboarding",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("plataforma:onboarding_empresa"),
            data={
                "nome_empresa": "Empresa Criada Onboarding",
                "nome_admin": "Admin Criado",
                "username_admin": "admin_criado_onboarding",
                "email_admin": "admin-criado@example.com",
                "password_admin": "SenhaSegura123",
                "plano": str(self.plano_base.pk),
                "ciclo_subscricao": "12",
                "tipo_acesso": "empresa_admin",
                "estado_empresa": "teste",
                "criar_subscricao_inicial": "on",
            },
        )

        self.assertRedirects(response, reverse("plataforma:onboarding_empresa"))
        empresa = Empresa.objects.get(nome="Empresa Criada Onboarding")
        user_admin = User.objects.get(username="admin_criado_onboarding")
        subscricao = SubscricaoEmpresa.objects.get(empresa=empresa)
        self.assertEqual(user_admin.email, "admin-criado@example.com")
        self.assertTrue(user_admin.is_active)
        self.assertEqual(user_admin.perfil_plataforma.tipo_acesso, "empresa_admin")
        self.assertEqual(subscricao.plano, self.plano_base)
        self.assertEqual(subscricao.ciclo_cobranca, "12")
        self.assertEqual(subscricao.valor, Decimal("500.00"))
