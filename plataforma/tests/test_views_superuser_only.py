from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma


class PlataformaSuperuserOnlyViewsTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome="Empresa Superuser Only",
            nome_comercial="Empresa Superuser Only",
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

    def test_superuser_acede_features_e_riscos_deploy(self):
        user = self._criar_user_com_perfil(
            username="super_features_riscos",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.client.force_login(user)

        response_features = self.client.get(reverse("plataforma:features_dashboard"))
        response_riscos = self.client.get(reverse("plataforma:riscos_deploy_dashboard"))

        self.assertEqual(response_features.status_code, 200)
        self.assertContains(response_features, "Gestão de Features")
        self.assertContains(response_features, self.empresa.nome)
        self.assertEqual(response_riscos.status_code, 200)
        self.assertContains(response_riscos, "Riscos de Deploy")
        self.assertContains(response_riscos, "Checklist pré-deploy")

    def test_platform_admin_nao_superuser_nao_acede_features_nem_riscos(self):
        user = self._criar_user_com_perfil(
            username="platform_admin_sem_superuser",
            tipo_acesso="platform_admin",
        )
        self.client.force_login(user)

        response_features = self.client.get(reverse("plataforma:features_dashboard"))
        response_riscos = self.client.get(reverse("plataforma:riscos_deploy_dashboard"))

        self.assertRedirects(response_features, reverse("plataforma:dashboard"))
        self.assertRedirects(response_riscos, reverse("plataforma:dashboard"))

    def test_empresa_admin_nao_acede_features_nem_riscos(self):
        user = self._criar_user_com_perfil(
            username="empresa_admin_sem_plataforma",
            tipo_acesso="empresa_admin",
        )
        self.client.force_login(user)

        response_features = self.client.get(reverse("plataforma:features_dashboard"))
        response_riscos = self.client.get(reverse("plataforma:riscos_deploy_dashboard"))

        self.assertRedirects(
            response_features,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )
        self.assertRedirects(
            response_riscos,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

    def test_anonimo_e_enviado_para_login_em_features_e_riscos(self):
        response_features = self.client.get(reverse("plataforma:features_dashboard"))
        response_riscos = self.client.get(reverse("plataforma:riscos_deploy_dashboard"))

        self.assertEqual(
            response_features["Location"],
            f"{reverse('login')}?next={reverse('plataforma:features_dashboard')}",
        )
        self.assertEqual(
            response_riscos["Location"],
            f"{reverse('login')}?next={reverse('plataforma:riscos_deploy_dashboard')}",
        )
