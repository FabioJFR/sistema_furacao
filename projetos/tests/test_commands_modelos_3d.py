from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from projetos.models import Modelo3DBlock, Modelo3DImplicit, Modelo3DWireframe
from projetos.tests.helpers import criar_empresa, criar_perfil, criar_projeto, criar_user


class BackfillModelos3DEmpresaCommandTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Backfill 3D")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Backfill 3D")
        self.user = criar_user(username="admin_backfill_3d")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)

    def test_dry_run_nao_altera_modelo_legacy(self):
        modelo = Modelo3DWireframe.objects.create(
            criado_por=self.user,
            nome="Wireframe Legacy Dry",
            formato="obj",
        )
        stdout = StringIO()

        call_command("backfill_modelos_3d_empresa", "--modelo", "wireframe", stdout=stdout)

        modelo.refresh_from_db()
        self.assertIsNone(modelo.empresa)
        self.assertIn("DRY-RUN", stdout.getvalue())
        self.assertIn("1 proposta(s)", stdout.getvalue())

    def test_apply_associa_empresa_por_criador(self):
        modelo = Modelo3DImplicit.objects.create(
            criado_por=self.user,
            nome="Implicit Legacy Apply",
            formato="csv",
        )
        stdout = StringIO()

        call_command("backfill_modelos_3d_empresa", "--modelo", "implicit", "--apply", stdout=stdout)

        modelo.refresh_from_db()
        self.assertEqual(modelo.empresa, self.empresa)
        self.assertIsNone(modelo.projeto)
        self.assertIn("1 atualizado(s)", stdout.getvalue())

    def test_apply_com_projeto_unico_associa_empresa_e_projeto(self):
        modelo = Modelo3DBlock.objects.create(
            criado_por=self.user,
            nome="Block Legacy Projeto Unico",
            formato="csv",
        )
        stdout = StringIO()

        call_command(
            "backfill_modelos_3d_empresa",
            "--modelo",
            "block",
            "--apply",
            "--assign-single-project",
            stdout=stdout,
        )

        modelo.refresh_from_db()
        self.assertEqual(modelo.empresa, self.empresa)
        self.assertEqual(modelo.projeto, self.projeto)
        self.assertIn("projeto=Projeto Backfill 3D", stdout.getvalue())

    def test_modelo_sem_criador_e_sem_projeto_fica_sem_candidato(self):
        modelo = Modelo3DWireframe.objects.create(
            nome="Wireframe Sem Dono",
            formato="obj",
        )
        stdout = StringIO()

        call_command("backfill_modelos_3d_empresa", "--modelo", "wireframe", "--apply", stdout=stdout)

        modelo.refresh_from_db()
        self.assertIsNone(modelo.empresa)
        self.assertIn("1 sem candidato", stdout.getvalue())
