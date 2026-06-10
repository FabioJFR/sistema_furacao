from django.test import TestCase
from django.urls import reverse

from .helpers import criar_empresa, criar_perfil, criar_projeto, criar_user


class ProjetoListMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa_1 = criar_empresa(nome="Empresa 1")
        self.empresa_2 = criar_empresa(nome="Empresa 2")
        self.projeto_1 = criar_projeto(empresa=self.empresa_1, nome="Projeto Empresa 1")
        self.projeto_2 = criar_projeto(empresa=self.empresa_2, nome="Projeto Empresa 2")

    def test_superuser_ve_projetos_de_todas_as_empresas(self):
        user = criar_user(username="super_projetos")
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:projeto_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["visao_global"])
        self.assertContains(response, self.projeto_1.nome)
        self.assertContains(response, self.projeto_2.nome)
        self.assertContains(response, self.empresa_2.nome)

    def test_admin_empresa_continua_isolado_a_sua_empresa(self):
        user = criar_user(username="admin_empresa_1")
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=self.empresa_1)
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:projeto_list"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["visao_global"])
        self.assertContains(response, self.projeto_1.nome)
        self.assertNotContains(response, self.projeto_2.nome)

    def test_superuser_abre_projeto_empresa_2_mantendo_contexto(self):
        user = criar_user(username="super_detalhe")
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(user)
        url = reverse("projetos:projeto_detail_legacy", args=[self.projeto_2.pk])

        response = self.client.get(url, {"empresa_contexto": self.empresa_2.pk})

        self.assertRedirects(
            response,
            f"{self.projeto_2.get_absolute_url()}?empresa_contexto={self.empresa_2.pk}",
            fetch_redirect_response=False,
        )

    def test_superuser_nao_cria_projeto_sem_escolher_empresa(self):
        user = criar_user(username="super_criar")
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:projeto_create"))

        self.assertRedirects(response, reverse("projetos:projeto_list"), fetch_redirect_response=False)
