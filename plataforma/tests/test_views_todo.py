from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma


class TodoViewsAccessTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome="Empresa TO DO",
            nome_comercial="Empresa TO DO",
            status="ativa",
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

    def test_superuser_acede_dashboard_e_detalhe_todo(self):
        user = self._criar_user_com_perfil(
            username="super_todo",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response_dashboard = self.client.get(reverse("plataforma:todo_dashboard"))
        response_detail = self.client.get(reverse("plataforma:todo_area_detail", args=["projetos"]))

        self.assertEqual(response_dashboard.status_code, 200)
        self.assertContains(response_dashboard, "TO DO")
        self.assertContains(response_dashboard, "Projetos")
        self.assertEqual(response_detail.status_code, 200)
        self.assertContains(response_detail, "TO DO · Projetos")

    def test_platform_admin_nao_superuser_e_redirecionado_do_todo(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_todo",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_dashboard = self.client.get(reverse("plataforma:todo_dashboard"))
        response_detail = self.client.get(reverse("plataforma:todo_area_detail", args=["projetos"]))

        self.assertRedirects(response_dashboard, reverse("plataforma:dashboard"))
        self.assertRedirects(response_detail, reverse("plataforma:dashboard"))

    def test_empresa_admin_nao_acede_todo(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_todo",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:todo_dashboard"))

        self.assertRedirects(
            response,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

    def test_utilizador_anonimo_e_enviado_para_login(self):
        response = self.client.get(reverse("plataforma:todo_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('login')}?next={reverse('plataforma:todo_dashboard')}")

    def test_area_inexistente_devolve_404_para_superuser(self):
        user = self._criar_user_com_perfil(
            username="super_todo_404",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("plataforma:todo_area_detail", args=["area-inexistente"]))

        self.assertEqual(response.status_code, 404)
