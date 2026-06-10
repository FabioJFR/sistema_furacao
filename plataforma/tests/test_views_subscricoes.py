from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma, Plano, SubscricaoEmpresa


class PlataformaSubscricoesViewsTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            nome="Plano Subscrições",
            tipo="empresa",
            preco_mensal=Decimal("49.90"),
            preco_anual=Decimal("499.00"),
            ativo=True,
            periodos_cobranca_disponiveis=[1, 12],
        )
        self.empresa = Empresa.objects.create(
            nome="Empresa Subscrição",
            nome_comercial="Empresa Subscrição",
            plano=self.plano,
            status="teste",
            ativo=True,
        )
        self.subscricao = SubscricaoEmpresa.objects.create(
            empresa=self.empresa,
            plano=self.plano,
            estado="pendente",
            ciclo_cobranca="1",
            valor=Decimal("49.90"),
        )
        self.admin_cliente = User.objects.create_user(
            username="admin_cliente_pendente",
            email="admin-cliente@example.com",
            password="testpass123",
            is_active=False,
        )
        self.perfil_admin_cliente = PerfilPlataforma.objects.create(
            user=self.admin_cliente,
            tipo_acesso="empresa_admin",
            empresa=self.empresa,
            ativo=True,
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

    def test_platform_admin_ve_subscricoes_mas_nao_botao_reenvio(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_subscricoes",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:subscricao_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.empresa.nome)
        self.assertContains(response, self.admin_cliente.username)
        self.assertNotContains(response, "Reenviar ativação")

    def test_subscricoes_nao_falha_se_diagnostico_email_rebentar(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_subscricoes_email",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        with patch("plataforma.services.subscricoes.diagnosticar_email_transacional", side_effect=RuntimeError("smtp")):
            response = self.client.get(reverse("plataforma:subscricao_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.empresa.nome)

    def test_superuser_ve_botao_e_reenvia_ativacao(self):
        user = self._criar_user_com_perfil(
            username="super_subscricoes",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response_list = self.client.get(reverse("plataforma:subscricao_list"))
        with patch("plataforma.views.subscricoes.reenviar_confirmacao_utilizador", return_value=True) as mock_reenviar:
            response_post = self.client.post(
                reverse(
                    "plataforma:subscricao_reenviar_ativacao",
                    args=[self.perfil_admin_cliente.pk],
                )
            )

        self.assertContains(response_list, "Reenviar ativação")
        self.assertRedirects(response_post, reverse("plataforma:subscricao_list"))
        mock_reenviar.assert_called_once()
        self.assertEqual(mock_reenviar.call_args.kwargs["user"], self.admin_cliente)

    def test_reenvio_por_get_ou_platform_admin_nao_envia_email(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_reenvio_direto",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        with patch("plataforma.views.subscricoes.reenviar_confirmacao_utilizador") as mock_reenviar:
            response_get = self.client.get(
                reverse(
                    "plataforma:subscricao_reenviar_ativacao",
                    args=[self.perfil_admin_cliente.pk],
                )
            )
            response_post = self.client.post(
                reverse(
                    "plataforma:subscricao_reenviar_ativacao",
                    args=[self.perfil_admin_cliente.pk],
                )
            )

        self.assertRedirects(response_get, reverse("plataforma:subscricao_list"))
        self.assertRedirects(response_post, reverse("plataforma:subscricao_list"))
        mock_reenviar.assert_not_called()

    def test_empresa_admin_nao_acede_subscricoes(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_subscricoes",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:subscricao_list"))

        self.assertRedirects(
            response,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )
