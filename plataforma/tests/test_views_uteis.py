import io
import json
import uuid
import zipfile

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inspecao_ai.models import MemoriaTrabalhoAI
from plataforma.models import Empresa, FuroArquivadoPlataforma, PerfilPlataforma


class UteisSuperuserTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nome="Empresa Úteis",
            nome_comercial="Empresa Úteis",
            status="ativa",
            ativo=True,
        )
        self.superuser = self._criar_user_com_perfil(
            username="super_uteis",
            tipo_acesso="platform_owner",
            is_superuser=True,
        )
        self.memoria = MemoriaTrabalhoAI.objects.create(
            empresa=self.empresa,
            criado_por=self.superuser,
            titulo="Memória AI útil",
            area="plataforma",
            resumo="Resumo para exportação",
        )
        self.furo_arquivado = FuroArquivadoPlataforma.objects.create(
            empresa=self.empresa,
            furo_id_origem=uuid.uuid4(),
            projeto_id_origem=uuid.uuid4(),
            nome_furo="Furo Arquivado Útil",
            estado_no_arquivo="concluido",
            terminado_por=self.superuser,
            dados_snapshot={"profundidade": 42},
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

    def test_superuser_acede_dashboard_arquivo_e_detalhe(self):
        self.client.force_login(self.superuser)

        response_dashboard = self.client.get(reverse("plataforma:uteis_dashboard"))
        response_arquivo = self.client.get(reverse("plataforma:uteis_arquivo_furos"))
        response_detail = self.client.get(
            reverse("plataforma:uteis_arquivo_furo_detail", args=[self.furo_arquivado.pk])
        )

        self.assertEqual(response_dashboard.status_code, 200)
        self.assertContains(response_dashboard, "Memórias de trabalho AI")
        self.assertEqual(response_arquivo.status_code, 200)
        self.assertContains(response_arquivo, self.furo_arquivado.nome_furo)
        self.assertEqual(response_detail.status_code, 200)
        self.assertContains(response_detail, self.furo_arquivado.nome_furo)
        self.assertContains(response_detail, "profundidade")

    def test_export_presets_json_e_full_zip_estao_disponiveis_para_superuser(self):
        self.client.force_login(self.superuser)

        response_json = self.client.get(reverse("plataforma:uteis_export_ai_json", args=["presets"]))
        response_zip = self.client.get(reverse("plataforma:uteis_export_ai_json", args=["full"]))

        self.assertEqual(response_json.status_code, 200)
        self.assertEqual(response_json["Content-Type"], "application/json; charset=utf-8")
        payload = json.loads(response_json.content.decode("utf-8"))
        memorias = payload["datasets"]["memorias_trabalho_ai"]
        self.assertEqual(len(memorias), 1)
        self.assertEqual(memorias[0]["titulo"], self.memoria.titulo)

        self.assertEqual(response_zip.status_code, 200)
        self.assertEqual(response_zip["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(response_zip.content)) as archive:
            self.assertIn("manifest.json", archive.namelist())
            self.assertIn("memorias_trabalho_ai.json", archive.namelist())

    def test_export_scope_invalido_redireciona_sem_download(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("plataforma:uteis_export_ai_json", args=["invalido"]))

        self.assertRedirects(response, reverse("plataforma:uteis_dashboard"))

    def test_limpeza_exige_post_e_scope_reconhecido(self):
        self.client.force_login(self.superuser)

        response_get = self.client.get(reverse("plataforma:uteis_clear_scope", args=["presets"]))
        self.assertRedirects(response_get, reverse("plataforma:uteis_dashboard"))
        self.assertTrue(MemoriaTrabalhoAI.objects.filter(pk=self.memoria.pk).exists())

        response_invalid = self.client.post(reverse("plataforma:uteis_clear_scope", args=["invalido"]))
        self.assertRedirects(response_invalid, reverse("plataforma:uteis_dashboard"))
        self.assertTrue(MemoriaTrabalhoAI.objects.filter(pk=self.memoria.pk).exists())

        response_post = self.client.post(reverse("plataforma:uteis_clear_scope", args=["presets"]))
        self.assertRedirects(response_post, reverse("plataforma:uteis_dashboard"))
        self.assertFalse(MemoriaTrabalhoAI.objects.filter(pk=self.memoria.pk).exists())

    def test_platform_admin_empresa_admin_e_anonimo_nao_acedem_a_uteis(self):
        platform_admin = self._criar_user_com_perfil(
            username="platform_admin_uteis",
            tipo_acesso="platform_admin",
        )
        empresa_admin = self._criar_user_com_perfil(
            username="empresa_admin_uteis",
            tipo_acesso="empresa_admin",
        )

        self.client.force_login(platform_admin)
        response_platform = self.client.get(reverse("plataforma:uteis_dashboard"))
        self.assertRedirects(
            response_platform,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

        self.client.force_login(empresa_admin)
        response_empresa = self.client.get(reverse("plataforma:uteis_export_ai_json", args=["full"]))
        self.assertRedirects(
            response_empresa,
            reverse("projetos:redirect_after_login"),
            fetch_redirect_response=False,
        )

        self.client.logout()
        response_anonimo = self.client.get(reverse("plataforma:uteis_arquivo_furos"))
        self.assertEqual(
            response_anonimo["Location"],
            f"{reverse('login')}?next={reverse('plataforma:uteis_arquivo_furos')}",
        )
