from io import StringIO
from datetime import date

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from projetos.models import Material, Medicao, RegistoDiarioEmpregado
from projetos.tests.helpers import criar_empregado, criar_empresa, criar_furo, criar_perfil, criar_projeto, criar_user


@override_settings(ALLOWED_HOSTS=["testserver"])
class ReleaseSmokeCommandTests(TestCase):
    def test_smoke_publico_valida_rotas_criticas(self):
        stdout = StringIO()

        call_command("release_smoke_check", "--public-only", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("[OK] homepage", output)
        self.assertIn("[OK] login", output)
        self.assertIn("Resumo smoke:", output)
        self.assertIn("Checklist copiável", output)
        self.assertIn("python manage.py release_smoke_check --host testserver --public-only", output)
        self.assertIn("- Modo: public-only", output)
        self.assertIn("- Rotas OK: homepage", output)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_smoke_publico_usa_https_interno_e_nao_falha_com_redirect_ssl(self):
        stdout = StringIO()

        call_command("release_smoke_check", "--public-only", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("[OK] homepage", output)
        self.assertNotIn("respondeu 301", output)

    def test_smoke_autenticado_valida_login_e_rotas_base(self):
        User.objects.create_superuser(
            username="smoke_super",
            email="smoke@example.com",
            password="testpass123",
        )
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_super",
            "--password",
            "testpass123",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] auth-login", output)
        self.assertIn("[OK] redirect-pos-login", output)
        self.assertIn(
            "python manage.py release_smoke_check --host testserver --profile base "
            "--username smoke_super --password <password>",
            output,
        )
        self.assertIn("- Modo: autenticado", output)
        self.assertIn("- Perfil: base", output)
        self.assertNotIn("testpass123", output)

    def test_smoke_superuser_valida_rotas_de_plataforma(self):
        criar_empresa(nome="Empresa Smoke")
        User.objects.create_superuser(
            username="smoke_owner",
            email="owner@example.com",
            password="testpass123",
        )
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_owner",
            "--password",
            "testpass123",
            "--profile",
            "superuser",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] superuser-plataforma", output)
        self.assertIn("[OK] superuser-todo", output)

    def test_smoke_empresa_valida_rotas_operacionais_base(self):
        empresa = criar_empresa(nome="Empresa Smoke")
        user = criar_user(username="smoke_empresa")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_empresa",
            "--password",
            "testpass123",
            "--profile",
            "empresa",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] empresa-dashboard", output)
        self.assertIn("[OK] empresa-projetos", output)
        self.assertIn("[OK] empresa-materiais", output)

    def test_smoke_empresa_valida_rotas_de_detalhe_com_ids_reais(self):
        empresa = criar_empresa(nome="Empresa Smoke")
        user = criar_user(username="smoke_empresa_detail")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        empregado = criar_empregado(empresa=empresa, nome="Operador Smoke")
        projeto = criar_projeto(empresa=empresa, nome="Projeto Smoke")
        furo = criar_furo(empresa=empresa, projeto=projeto, nome="Furo Smoke")
        material = Material.objects.create(
            empresa=empresa,
            projeto=projeto,
            furo=furo,
            nome="Material Smoke",
            quantidade=10,
        )
        medicao = Medicao.objects.create(
            furo=furo,
            profundidade_medida=1.0,
            inclinacao_real_medida=0,
            azimute_real_medido=0,
        )
        registo = RegistoDiarioEmpregado.objects.create(
            empregado=empregado,
            empresa=empresa,
            projeto=projeto,
            furo=furo,
            data=date(2026, 7, 3),
            metros_furados=1,
            cliente="Cliente Smoke",
            sonda="Sonda Smoke",
            numero_relatorio="SMK-001",
        )
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_empresa_detail",
            "--password",
            "testpass123",
            "--profile",
            "empresa",
            "--project-id",
            str(projeto.pk),
            "--furo-id",
            str(furo.pk),
            "--registo-id",
            str(registo.pk),
            "--material-id",
            str(material.pk),
            "--medicao-id",
            str(medicao.pk),
            "--include-report-pdf",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] detail-projeto", output)
        self.assertIn("[OK] detail-furo", output)
        self.assertIn("[OK] detail-registo", output)
        self.assertIn("[OK] detail-relatorio-pdf", output)
        self.assertIn("application/pdf", output)
        self.assertIn("--include-report-pdf", output)
        self.assertIn("[OK] detail-material", output)
        self.assertIn("[OK] detail-medicao", output)

    def test_smoke_empregado_valida_rotas_da_minha_area(self):
        empresa = criar_empresa(nome="Empresa Smoke")
        user = criar_user(username="smoke_empregado")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=empresa)
        criar_empregado(empresa=empresa, user=user, aprovado=True)
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_empregado",
            "--password",
            "testpass123",
            "--profile",
            "empregado",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] empregado-minha-area", output)
        self.assertIn("[OK] empregado-meus-furos", output)

    def test_smoke_individual_valida_rotas_operacionais_base(self):
        user = criar_user(username="smoke_individual")
        criar_perfil(user=user, tipo_acesso="individual")
        stdout = StringIO()

        call_command(
            "release_smoke_check",
            "--username",
            "smoke_individual",
            "--password",
            "testpass123",
            "--profile",
            "individual",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] individual-minha-area", output)
        self.assertIn("[OK] individual-projetos", output)

    def test_smoke_autenticado_exige_username_e_password(self):
        with self.assertRaises(CommandError):
            call_command("release_smoke_check", "--username", "sem_password", stdout=StringIO())
