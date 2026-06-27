import json

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from projetos.models import Modelo3DBlock, Modelo3DImplicit, Modelo3DWireframe
from projetos.tests.helpers import criar_empregado, criar_empresa, criar_perfil, criar_projeto, criar_user


class Modelos3DMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa 3D A")
        self.empresa_externa = criar_empresa(nome="Empresa 3D B")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto 3D A")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto 3D B")

        self.geologo_user = criar_user(username="geologo_3d")
        criar_perfil(user=self.geologo_user, tipo_acesso="empregado", empresa=self.empresa)
        criar_empregado(
            empresa=self.empresa,
            user=self.geologo_user,
            nome="Geólogo 3D",
            funcao="geologo",
        )

        self.wireframe_empresa = Modelo3DWireframe.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            criado_por=self.geologo_user,
            nome="Wireframe Empresa A",
            formato="obj",
            conteudo_texto="v 0 0 0\nv 1 0 0\nf 1 2 2",
            tamanho_bytes=32,
        )
        self.wireframe_externo = Modelo3DWireframe.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Wireframe Empresa B",
            formato="obj",
            conteudo_texto="v 9 9 9",
            tamanho_bytes=8,
        )
        self.wireframe_legado = Modelo3DWireframe.objects.create(
            nome="Wireframe Legado Global",
            formato="obj",
            conteudo_texto="v 5 5 5",
            tamanho_bytes=8,
        )
        self.block_empresa = Modelo3DBlock.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            criado_por=self.geologo_user,
            nome="Block Empresa A",
            formato="csv",
            conteudo_texto="x,y,z\n1,2,3",
            tamanho_bytes=12,
        )
        self.block_externo = Modelo3DBlock.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Block Empresa B",
            formato="csv",
            conteudo_texto="x,y,z\n9,9,9",
            tamanho_bytes=12,
        )
        self.implicit_empresa = Modelo3DImplicit.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            criado_por=self.geologo_user,
            nome="Implicit Empresa A",
            formato="csv",
            dominio="minério",
            conteudo_texto="x,y,z,dominio\n1,2,3,minério",
            tamanho_bytes=26,
        )
        self.implicit_externo = Modelo3DImplicit.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Implicit Empresa B",
            formato="csv",
            dominio="estéril",
            conteudo_texto="x,y,z,dominio\n9,9,9,estéril",
            tamanho_bytes=26,
        )

    def test_geologo_ve_apenas_modelos_3d_da_sua_empresa(self):
        self.client.force_login(self.geologo_user)

        response_wireframe = self.client.get(reverse("projetos:modelo_3d_wireframe"))
        response_block = self.client.get(reverse("projetos:modelo_3d_block_model"))
        response_implicit = self.client.get(reverse("projetos:modelo_3d_implicit"))

        self.assertContains(response_wireframe, self.wireframe_empresa.nome)
        self.assertNotContains(response_wireframe, self.wireframe_externo.nome)
        self.assertNotContains(response_wireframe, self.wireframe_legado.nome)
        self.assertContains(response_block, self.block_empresa.nome)
        self.assertNotContains(response_block, self.block_externo.nome)
        self.assertContains(response_implicit, self.implicit_empresa.nome)
        self.assertNotContains(response_implicit, self.implicit_externo.nome)

    def test_geologo_nao_acede_modelos_3d_de_outra_empresa_por_url_direto(self):
        self.client.force_login(self.geologo_user)

        urls = [
            reverse("projetos:modelo_3d_wireframe_conteudo", args=[self.wireframe_externo.pk]),
            reverse("projetos:modelo_3d_wireframe_download", args=[self.wireframe_externo.pk]),
            reverse("projetos:modelo_3d_block_conteudo", args=[self.block_externo.pk]),
            reverse("projetos:modelo_3d_block_download", args=[self.block_externo.pk]),
            reverse("projetos:modelo_3d_block_config", args=[self.block_externo.pk]),
            reverse("projetos:modelo_3d_implicit_conteudo", args=[self.implicit_externo.pk]),
            reverse("projetos:modelo_3d_implicit_download", args=[self.implicit_externo.pk]),
            reverse("projetos:modelo_3d_implicit_config", args=[self.implicit_externo.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_geologo_nao_apaga_modelo_3d_de_outra_empresa(self):
        self.client.force_login(self.geologo_user)

        response = self.client.post(
            reverse("projetos:modelo_3d_wireframe_apagar", args=[self.wireframe_externo.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Modelo3DWireframe.objects.filter(pk=self.wireframe_externo.pk).exists())

    def test_upload_wireframe_geologo_fica_associado_a_empresa(self):
        self.client.force_login(self.geologo_user)
        ficheiro = SimpleUploadedFile(
            "novo-wireframe.obj",
            b"v 0 0 0\nv 1 0 0\nf 1 2 2\n",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("projetos:modelo_3d_wireframe"),
            {"action": "validate_and_save", "wireframe_file": ficheiro},
        )

        self.assertEqual(response.status_code, 200)
        modelo = Modelo3DWireframe.objects.get(nome="novo-wireframe.obj")
        self.assertEqual(modelo.empresa, self.empresa)

    def test_superuser_ve_modelos_3d_de_todas_as_empresas_e_legados(self):
        superuser = User.objects.create_superuser(
            username="super_3d",
            email="super3d@example.com",
            password="testpass123",
        )
        self.client.force_login(superuser)

        response = self.client.get(reverse("projetos:modelo_3d_wireframe"))

        self.assertContains(response, self.wireframe_empresa.nome)
        self.assertContains(response, self.wireframe_externo.nome)
        self.assertContains(response, self.wireframe_legado.nome)

    def test_config_modelo_3d_da_empresa_continua_disponivel(self):
        self.client.force_login(self.geologo_user)

        response = self.client.post(
            reverse("projetos:modelo_3d_block_config", args=[self.block_empresa.pk]),
            data=json.dumps({"ui_config": {"mostrar_como_voxels": False}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
        self.block_empresa.refresh_from_db()
        self.assertEqual(self.block_empresa.resumo_json["ui_config"]["mostrar_como_voxels"], False)
