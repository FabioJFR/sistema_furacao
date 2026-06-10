from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    PerfilPlataforma,
    Plano,
    SubscricaoEmpresa,
)
from projetos.models import Individual
from projetos.tests.helpers import criar_empresa, criar_empregado, criar_perfil, criar_user
from website.forms import LoginConsentForm
from website.services import executar_registo


class LoginConsentFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="utilizador_login",
            password="segredo-forte-123",
            email="login@example.com",
        )

    def test_login_exige_confirmacao_dos_termos(self):
        form = LoginConsentForm(
            data={
                "username": self.user.username,
                "password": "segredo-forte-123",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("confirmar_termos", form.errors)

    def test_login_com_credenciais_validas_e_termos_confirmados(self):
        form = LoginConsentForm(
            data={
                "username": self.user.username,
                "password": "segredo-forte-123",
                "confirmar_termos": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.get_user(), self.user)


class RedirectAfterLoginTests(TestCase):
    def test_utilizador_nao_autenticado_volta_para_login(self):
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(response, reverse("login"))

    def test_superuser_vai_para_dashboard_plataforma(self):
        user = User.objects.create_superuser(
            username="superuser",
            email="superuser@example.com",
            password="segredo-forte-123",
        )

        self.client.force_login(user)
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(response, reverse("plataforma:dashboard"), fetch_redirect_response=False)

    def test_empresa_admin_vai_para_dashboard_projetos(self):
        empresa = criar_empresa(nome="Empresa Login")
        user = criar_user(username="admin_login")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)

        self.client.force_login(user)
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(response, reverse("projetos:dashboard"), fetch_redirect_response=False)

    def test_conta_individual_vai_para_minha_area(self):
        user = criar_user(username="individual_login")
        criar_perfil(user=user, tipo_acesso="individual")

        self.client.force_login(user)
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(response, reverse("projetos:area_empregado"), fetch_redirect_response=False)

    def test_empregado_generico_vai_para_minha_area(self):
        empresa = criar_empresa(nome="Empresa Empregado")
        user = criar_user(username="empregado_login")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=empresa)
        criar_empregado(empresa=empresa, user=user, aprovado=True, funcao="outro")

        self.client.force_login(user)
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(response, reverse("projetos:area_empregado"), fetch_redirect_response=False)

    def test_geologo_vai_para_dashboard_geologia(self):
        empresa = criar_empresa(nome="Empresa Geologia")
        user = criar_user(username="geologo_login")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=empresa)
        criar_empregado(empresa=empresa, user=user, aprovado=True, funcao="geologo")

        self.client.force_login(user)
        response = self.client.get(reverse("projetos:redirect_after_login"))

        self.assertRedirects(
            response,
            reverse("geologia:empregado_geologo_dashboard"),
            fetch_redirect_response=False,
        )


class ConfirmarContaTests(TestCase):
    def _url_confirmacao(self, user, token=None):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        return reverse(
            "website:confirmar_conta",
            kwargs={"uidb64": uidb64, "token": token or default_token_generator.make_token(user)},
        )

    def test_confirmar_conta_com_token_valido_ativa_utilizador(self):
        user = User.objects.create_user(
            username="pendente",
            email="pendente@example.com",
            password="segredo-forte-123",
            is_active=False,
        )

        response = self.client.get(self._url_confirmacao(user))

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertRedirects(response, reverse("login"))

    def test_confirmar_conta_com_token_invalido_mantem_utilizador_inativo(self):
        user = User.objects.create_user(
            username="pendente_invalido",
            email="pendente-invalido@example.com",
            password="segredo-forte-123",
            is_active=False,
        )

        response = self.client.get(self._url_confirmacao(user, token="token-invalido"))

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertRedirects(response, reverse("login"))


class RegistoPublicoServiceTests(TestCase):
    def criar_plano(self, *, nome, tipo, mensal="10.00", anual="100.00"):
        return Plano.objects.create(
            nome=nome,
            tipo=tipo,
            preco_mensal=Decimal(mensal),
            preco_anual=Decimal(anual),
            periodos_cobranca_disponiveis=[1, 12],
            ativo=True,
        )

    def payload_base(self, *, plano, username, tipo_conta, nome_empresa=""):
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password1": "segredo-forte-123",
            "password2": "segredo-forte-123",
            "nome_empresa": nome_empresa,
            "nome_responsavel": f"Responsavel {username}",
            "plano": str(plano.pk),
            "tipo_conta": tipo_conta,
            "ciclo_subscricao": "12",
            "aceitar_termos": "on",
        }

    @patch("website.services.enviar_email_confirmacao_conta")
    def test_registo_empresa_cria_conta_inativa_empresa_subscricao_pagamento_e_movimento(self, mock_email):
        plano = self.criar_plano(nome="Plano Empresa", tipo="empresa", anual="120.00")

        resultado = executar_registo(
            self.payload_base(
                plano=plano,
                username="empresa_publica",
                tipo_conta="empresa",
                nome_empresa="Empresa Pública",
            )
        )

        self.assertTrue(resultado.sucesso, resultado.erros)
        user = User.objects.get(username="empresa_publica")
        empresa = Empresa.objects.get(nome="Empresa Pública")
        perfil = PerfilPlataforma.objects.get(user=user)
        subscricao = SubscricaoEmpresa.objects.get(empresa=empresa)
        pagamento = PagamentoEmpresa.objects.get(empresa=empresa)
        movimento = MovimentoFinanceiroPlataforma.objects.get(empresa=empresa)

        self.assertFalse(user.is_active)
        self.assertEqual(perfil.tipo_acesso, "empresa_admin")
        self.assertEqual(perfil.empresa, empresa)
        self.assertEqual(empresa.plano, plano)
        self.assertEqual(subscricao.plano, plano)
        self.assertEqual(subscricao.estado, "pendente")
        self.assertEqual(subscricao.ciclo_cobranca, "12")
        self.assertEqual(subscricao.valor, Decimal("120.00"))
        self.assertEqual(pagamento.valor, Decimal("120.00"))
        self.assertEqual(pagamento.estado, "pendente")
        self.assertEqual(movimento.valor, Decimal("120.00"))
        self.assertEqual(movimento.categoria, "subscricao")
        mock_email.assert_called_once()

    @patch("website.services.enviar_email_confirmacao_conta")
    def test_registo_individual_cria_perfil_individual_e_movimento_sem_empresa(self, mock_email):
        plano = self.criar_plano(nome="Plano Individual", tipo="individual", mensal="7.50", anual="75.00")

        resultado = executar_registo(
            self.payload_base(
                plano=plano,
                username="individual_publico",
                tipo_conta="individual",
            )
        )

        self.assertTrue(resultado.sucesso, resultado.erros)
        user = User.objects.get(username="individual_publico")
        perfil = PerfilPlataforma.objects.get(user=user)
        individual = Individual.objects.get(user=user)
        movimento = MovimentoFinanceiroPlataforma.objects.get(perfil_plataforma=perfil)

        self.assertFalse(user.is_active)
        self.assertEqual(perfil.tipo_acesso, "individual")
        self.assertIsNone(perfil.empresa)
        self.assertEqual(individual.email, user.email)
        self.assertFalse(Empresa.objects.filter(email=user.email).exists())
        self.assertEqual(SubscricaoEmpresa.objects.count(), 0)
        self.assertEqual(PagamentoEmpresa.objects.count(), 0)
        self.assertEqual(movimento.valor, Decimal("75.00"))
        self.assertEqual(movimento.categoria, "subscricao")
        mock_email.assert_called_once()

    def test_registo_com_plano_incompativel_nao_cria_utilizador(self):
        plano = self.criar_plano(nome="Plano Empresa Incompativel", tipo="empresa")

        resultado = executar_registo(
            self.payload_base(
                plano=plano,
                username="individual_em_plano_empresa",
                tipo_conta="individual",
            )
        )

        self.assertFalse(resultado.sucesso)
        self.assertIn("O plano escolhido exige conta do tipo empresa.", resultado.erros)
        self.assertFalse(User.objects.filter(username="individual_em_plano_empresa").exists())
        self.assertEqual(MovimentoFinanceiroPlataforma.objects.count(), 0)

    @patch("website.services.enviar_email_confirmacao_conta", side_effect=RuntimeError("SMTP indisponivel"))
    def test_falha_no_email_de_confirmacao_faz_rollback_do_registo(self, _mock_email):
        plano = self.criar_plano(nome="Plano Empresa Rollback", tipo="empresa")

        resultado = executar_registo(
            self.payload_base(
                plano=plano,
                username="empresa_rollback",
                tipo_conta="empresa",
                nome_empresa="Empresa Rollback",
            )
        )

        self.assertFalse(resultado.sucesso)
        self.assertFalse(User.objects.filter(username="empresa_rollback").exists())
        self.assertFalse(Empresa.objects.filter(nome="Empresa Rollback").exists())
        self.assertEqual(SubscricaoEmpresa.objects.count(), 0)
        self.assertEqual(PagamentoEmpresa.objects.count(), 0)
        self.assertEqual(MovimentoFinanceiroPlataforma.objects.count(), 0)


class RegistoPublicoViewTests(TestCase):
    def setUp(self):
        self.plano_empresa = Plano.objects.create(
            nome="Plano Web Empresa",
            tipo="empresa",
            preco_mensal=Decimal("15.00"),
            preco_anual=Decimal("150.00"),
            periodos_cobranca_disponiveis=[1, 12],
            ativo=True,
        )
        self.plano_individual = Plano.objects.create(
            nome="Plano Web Individual",
            tipo="individual",
            preco_mensal=Decimal("5.00"),
            preco_anual=Decimal("50.00"),
            periodos_cobranca_disponiveis=[1, 12],
            ativo=True,
        )

    def payload_empresa(self, **alteracoes):
        payload = {
            "username": "nova_empresa_web",
            "email": "nova-empresa-web@example.com",
            "password1": "segredo-forte-123",
            "password2": "segredo-forte-123",
            "nome_empresa": "Nova Empresa Web",
            "nome_responsavel": "Responsavel Web",
            "plano": str(self.plano_empresa.pk),
            "tipo_conta": "empresa",
            "ciclo_subscricao": "12",
            "aceitar_termos": "on",
        }
        payload.update(alteracoes)
        return payload

    def test_get_apresenta_planos_e_inicia_sessao_antibot(self):
        response = self.client.get(reverse("website:registo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.plano_empresa.nome)
        self.assertContains(response, self.plano_individual.nome)
        self.assertIn("planos_contexto", response.context)
        self.assertIn("website_registo_started_at", self.client.session)

    @override_settings(REGISTO_MIN_SUBMISSION_SECONDS=0)
    @patch("website.services.enviar_email_confirmacao_conta")
    def test_post_valido_cria_conta_mostra_sucesso_e_limpa_inicio_antibot(self, mock_email):
        self.client.get(reverse("website:registo"))

        response = self.client.post(
            reverse("website:registo"),
            self.payload_empresa(),
            follow=True,
        )

        self.assertRedirects(response, reverse("login"))
        self.assertContains(
            response,
            "Conta criada com sucesso. Enviámos um email para confirmares a conta antes do primeiro login.",
        )
        self.assertTrue(User.objects.filter(username="nova_empresa_web", is_active=False).exists())
        self.assertNotIn("website_registo_started_at", self.client.session)
        mock_email.assert_called_once()

    @override_settings(REGISTO_MIN_SUBMISSION_SECONDS=0)
    def test_post_invalido_mostra_erro_e_preserva_dados_submetidos(self):
        response = self.client.post(
            reverse("website:registo"),
            self.payload_empresa(aceitar_termos=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Tens de aceitar os Termos &amp; Condições e a Política de Privacidade para criar conta.",
        )
        self.assertContains(response, "Nova Empresa Web")
        self.assertFalse(User.objects.filter(username="nova_empresa_web").exists())

    @override_settings(REGISTO_MIN_SUBMISSION_SECONDS=60)
    def test_post_imediato_apos_get_e_bloqueado_pelo_antibot(self):
        self.client.get(reverse("website:registo"))

        response = self.client.post(reverse("website:registo"), self.payload_empresa())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A submissão foi demasiado rápida. Aguarda alguns segundos e tenta novamente.")
        self.assertFalse(User.objects.filter(username="nova_empresa_web").exists())


class ReenviarConfirmacaoTests(TestCase):
    def test_get_redireciona_para_login(self):
        response = self.client.get(reverse("website:reenviar_confirmacao"))

        self.assertRedirects(response, reverse("login"))

    def test_post_sem_email_mostra_erro_no_login(self):
        response = self.client.post(reverse("website:reenviar_confirmacao"), {"email": ""}, follow=True)

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Indica o email para reenviar a confirmação.")

    @patch("website.services.enviar_email_confirmacao_conta")
    def test_post_reenvia_apenas_confirmacao_de_conta_inativa(self, mock_email):
        user_inativo = User.objects.create_user(
            username="conta_por_confirmar",
            email="estado-conta@example.com",
            password="segredo-forte-123",
            is_active=False,
        )
        User.objects.create_user(
            username="conta_ja_ativa",
            email="estado-conta@example.com",
            password="segredo-forte-123",
            is_active=True,
        )

        response = self.client.post(
            reverse("website:reenviar_confirmacao"),
            {"email": "estado-conta@example.com"},
            follow=True,
        )

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Se existir uma conta pendente com esse email, enviámos um novo link de confirmação.")
        mock_email.assert_called_once()
        self.assertEqual(mock_email.call_args.kwargs["user"], user_inativo)

    @patch("website.services.reenviar_confirmacao_por_email", side_effect=RuntimeError("SMTP indisponivel"))
    def test_falha_no_reenvio_mostra_mensagem_controlada(self, _mock_reenvio):
        response = self.client.post(
            reverse("website:reenviar_confirmacao"),
            {"email": "pendente@example.com"},
            follow=True,
        )

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "Não foi possível reenviar o email de confirmação neste momento.")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetPublicoTests(TestCase):
    def test_pedido_de_recuperacao_envia_email_a_utilizador_ativo(self):
        User.objects.create_user(
            username="utilizador_password",
            email="password@example.com",
            password="segredo-forte-123",
            is_active=True,
        )

        response = self.client.post(reverse("password_reset"), {"email": "password@example.com"})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password@example.com", mail.outbox[0].to)
        self.assertIn("/reset/", mail.outbox[0].body)

    def test_pedido_de_recuperacao_nao_revela_email_inexistente(self):
        response = self.client.post(reverse("password_reset"), {"email": "desconhecido@example.com"})

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_valido_altera_password_e_fica_invalido_depois_de_usado(self):
        user = User.objects.create_user(
            username="utilizador_reset",
            email="reset@example.com",
            password="password-antiga-123",
            is_active=True,
        )
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url_token = reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})

        response_token = self.client.get(url_token)
        self.assertEqual(response_token.status_code, 302)

        response_update = self.client.post(
            response_token.url,
            {
                "new_password1": "password-nova-456",
                "new_password2": "password-nova-456",
            },
        )

        user.refresh_from_db()
        self.assertRedirects(response_update, reverse("password_reset_complete"))
        self.assertTrue(user.check_password("password-nova-456"))

        response_reuso = self.client.get(url_token)
        self.assertEqual(response_reuso.status_code, 200)
        self.assertFalse(response_reuso.context["validlink"])
