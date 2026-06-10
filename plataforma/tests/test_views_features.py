from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.feature_flags import feature_ativa_para_contexto
from plataforma.models import ConfiguracaoFeatureAcesso, Empresa, PerfilPlataforma, Plano


class PlataformaFeaturesViewsTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            nome="Plano Features",
            tipo="empresa",
            preco_mensal=Decimal("79.90"),
            preco_anual=Decimal("799.00"),
            ativo=True,
            acesso_dashboard_empresa=True,
            acesso_painel_empregado=False,
            permite_multiplos_utilizadores=False,
            periodos_cobranca_disponiveis=[1, 12],
        )
        self.empresa = Empresa.objects.create(
            nome="Empresa Features",
            email="features@example.com",
            plano=self.plano,
            status="ativa",
            ativo=True,
        )
        self.superuser = User.objects.create_user(
            username="super_features_mutacao",
            email="super-features@example.com",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )
        PerfilPlataforma.objects.create(
            user=self.superuser,
            tipo_acesso="platform_owner",
            ativo=True,
        )
        self.user_individual = User.objects.create_user(
            username="individual_features",
            email="individual-features@example.com",
            password="testpass123",
        )
        self.perfil_individual = PerfilPlataforma.objects.create(
            user=self.user_individual,
            tipo_acesso="individual",
            ativo=True,
        )
        self.user_individual_inativo = User.objects.create_user(
            username="individual_features_inativo",
            email="individual-features-inativo@example.com",
            password="testpass123",
            is_active=False,
        )
        self.perfil_individual_inativo = PerfilPlataforma.objects.create(
            user=self.user_individual_inativo,
            tipo_acesso="individual",
            ativo=True,
        )

    def test_post_empresa_cria_e_remove_overrides_conforme_base_do_plano(self):
        self.client.force_login(self.superuser)

        response_desativar_dashboard = self.client.post(
            reverse("plataforma:features_dashboard"),
            {
                "tipo": "empresa",
                "alvo": str(self.empresa.pk),
                "features": ["geologia"],
            },
        )

        self.assertRedirects(
            response_desativar_dashboard,
            f"{reverse('plataforma:features_dashboard')}?tipo=empresa&alvo={self.empresa.pk}",
        )
        override_dashboard = ConfiguracaoFeatureAcesso.objects.get(
            empresa=self.empresa,
            chave_feature="dashboard_empresa",
        )
        self.assertFalse(override_dashboard.ativa)
        self.assertFalse(
            ConfiguracaoFeatureAcesso.objects.filter(
                empresa=self.empresa,
                chave_feature="geologia",
            ).exists()
        )
        self.assertFalse(feature_ativa_para_contexto(chave_feature="dashboard_empresa", empresa=self.empresa))

        response_repor_dashboard = self.client.post(
            reverse("plataforma:features_dashboard"),
            {
                "tipo": "empresa",
                "alvo": str(self.empresa.pk),
                "features": ["dashboard_empresa"],
            },
        )

        self.assertRedirects(
            response_repor_dashboard,
            f"{reverse('plataforma:features_dashboard')}?tipo=empresa&alvo={self.empresa.pk}",
        )
        self.assertFalse(
            ConfiguracaoFeatureAcesso.objects.filter(
                empresa=self.empresa,
                chave_feature="dashboard_empresa",
            ).exists()
        )
        self.assertTrue(feature_ativa_para_contexto(chave_feature="dashboard_empresa", empresa=self.empresa))

    def test_post_individual_cria_override_apenas_no_perfil_individual(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("plataforma:features_dashboard"),
            {
                "tipo": "individual",
                "alvo": str(self.perfil_individual.pk),
                "features": ["painel_empregado", "geologia"],
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('plataforma:features_dashboard')}?tipo=individual&alvo={self.perfil_individual.pk}",
        )
        override = ConfiguracaoFeatureAcesso.objects.get(
            perfil_plataforma=self.perfil_individual,
            chave_feature="painel_empregado",
        )
        self.assertTrue(override.ativa)
        self.assertIsNone(override.empresa_id)
        self.assertFalse(
            ConfiguracaoFeatureAcesso.objects.filter(
                empresa=self.empresa,
                chave_feature="painel_empregado",
            ).exists()
        )
        self.assertTrue(
            feature_ativa_para_contexto(
                chave_feature="painel_empregado",
                perfil_plataforma=self.perfil_individual,
            )
        )

    def test_post_sem_alvo_valido_nao_cria_configuracoes_soltas(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("plataforma:features_dashboard"),
            {
                "tipo": "individual",
                "alvo": "999999",
                "features": ["painel_empregado"],
            },
        )

        self.assertRedirects(response, reverse("plataforma:features_dashboard"))
        self.assertFalse(ConfiguracaoFeatureAcesso.objects.exists())

    def test_features_mostra_apenas_contas_individuais_ativadas(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("plataforma:features_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user_individual.username)
        self.assertNotContains(response, self.user_individual_inativo.username)
