from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma, Plano, SubscricaoEmpresa


class PlataformaDashboardViewsTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            nome="Plano Dashboard",
            tipo="empresa",
            preco_mensal=Decimal("59.90"),
            preco_anual=Decimal("599.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 12],
        )
        self.empresa_ativa = Empresa.objects.create(
            nome="Empresa Dashboard Ativa",
            email="ativa-dashboard@example.com",
            plano=self.plano,
            status="ativa",
            ativo=True,
        )
        SubscricaoEmpresa.objects.create(
            empresa=self.empresa_ativa,
            plano=self.plano,
            estado="ativa",
            ciclo_cobranca="1",
            valor=Decimal("59.90"),
        )
        self.empresa_teste = Empresa.objects.create(
            nome="Empresa Dashboard Teste",
            email="teste-dashboard@example.com",
            plano=self.plano,
            status="ativa",
            ativo=True,
        )
        SubscricaoEmpresa.objects.create(
            empresa=self.empresa_teste,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("59.90"),
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
            empresa=self.empresa_ativa if tipo_acesso == "empresa_admin" else None,
            ativo=True,
        )
        return user

    def test_platform_admin_acede_dashboard_com_metricas_e_sem_atalhos_superuser(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_dashboard",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard da Plataforma")
        self.assertContains(response, self.empresa_ativa.nome)
        self.assertContains(response, self.empresa_teste.nome)
        self.assertEqual(response.context["total_empresas"], 2)
        self.assertEqual(response.context["empresas_ativas"], 1)
        self.assertEqual(response.context["empresas_teste"], 1)
        self.assertNotContains(response, "TO DO")
        self.assertNotContains(response, "Riscos de deploy")
        self.assertNotContains(response, "Gestão de features")
        self.assertNotContains(response, "Furos arquivados (base plataforma)")

    def test_superuser_acede_dashboard_com_atalhos_reservados(self):
        user = self._criar_user_com_perfil(
            username="super_dashboard",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TO DO")
        self.assertContains(response, "Riscos de deploy")
        self.assertContains(response, "Gestão de features")
        self.assertContains(response, "Furos arquivados (base plataforma)")

    def test_empresa_admin_nao_acede_dashboard_plataforma(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_dashboard",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:dashboard"))

        self.assertRedirects(
            response,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

    def test_anonymous_redirect_para_login_com_next(self):
        response = self.client.get(reverse("plataforma:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('plataforma:dashboard')}",
            fetch_redirect_response=False,
        )
