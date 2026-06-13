from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plataforma.models import Empresa, PerfilPlataforma
from plataforma.selectors.riscos_deploy import (
    listar_comandos_deploy_operacional,
    listar_comandos_logrotate,
    listar_smoke_test_piloto_mvp,
    listar_tickets_friccoes_piloto_mvp,
)


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
        self.assertContains(response_riscos, "Script operacional de deploy")
        self.assertContains(response_riscos, "DRY_RUN=1 bash deploy/deploy_operacional.sh")
        self.assertContains(response_riscos, "ROLLBACK_ON_ERROR=1")
        self.assertContains(response_riscos, "Rotação automática de logs")
        self.assertContains(response_riscos, "sudo logrotate -d /etc/logrotate.d/sistema_furacao")
        self.assertContains(response_riscos, "Smoke test do piloto após deploy")
        self.assertContains(response_riscos, "Criar furo")
        self.assertContains(response_riscos, "Gerar relatório técnico")
        self.assertContains(response_riscos, "Matriz de tickets por fricção do piloto")
        self.assertContains(response_riscos, "Simplificar formulário de registo diário")

    def test_smoke_test_piloto_mvp_define_fluxo_operacional_completo(self):
        passos = listar_smoke_test_piloto_mvp()

        self.assertEqual(len(passos), 8)
        self.assertEqual(passos[0]["passo"], "Criar projeto")
        self.assertIn("sem exigir campos técnicos completos", passos[1]["resultado"])
        self.assertEqual(passos[-1]["passo"], "Gerar relatório técnico")

    def test_tickets_friccoes_piloto_mvp_cobrem_fluxos_criticos(self):
        tickets = listar_tickets_friccoes_piloto_mvp()
        fluxos = {item["fluxo"] for item in tickets}

        self.assertEqual(len(tickets), 6)
        self.assertSetEqual(
            fluxos,
            {"Criação", "Turno", "Materiais", "Medições", "Relatório", "Permissões"},
        )
        self.assertIn("regressão de permissão", tickets[-1]["ticket"])

    def test_comandos_deploy_operacional_incluem_dry_run_e_execucao(self):
        comandos = listar_comandos_deploy_operacional()

        self.assertEqual(len(comandos), 3)
        self.assertIn("DRY_RUN=1", comandos[0]["comando"])
        self.assertIn("BASE_URL=https://sistemafuracao.pt", comandos[1]["comando"])
        self.assertIn("BACKUP_CMD", comandos[2]["comando"])
        self.assertIn("ROLLBACK_ON_ERROR=1", comandos[2]["comando"])

    def test_comandos_logrotate_incluem_instalacao_validacao_e_rotacao(self):
        comandos = listar_comandos_logrotate()

        self.assertEqual(len(comandos), 3)
        self.assertIn("cp deploy/logrotate/sistema_furacao", comandos[0]["comando"])
        self.assertIn("logrotate -d", comandos[1]["comando"])
        self.assertIn("logrotate -f", comandos[2]["comando"])

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
