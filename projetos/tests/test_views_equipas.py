from django.test import TestCase
from django.urls import reverse

from projetos.models import Equipa

from .helpers import criar_empresa, criar_empregado, criar_perfil, criar_user


class EquipaAdminViewsTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Equipas")
        self.empresa_externa = criar_empresa(nome="Empresa Externa")
        self.user = criar_user(username="admin_equipas")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.empregado_a = criar_empregado(empresa=self.empresa, nome="Operador A")
        self.empregado_b = criar_empregado(empresa=self.empresa, nome="Operador B")
        self.empregado_pendente = criar_empregado(empresa=self.empresa, nome="Pendente", aprovado=False)
        self.empregado_externo = criar_empregado(empresa=self.empresa_externa, nome="Externo")
        self.client.force_login(self.user)

    def test_empresa_admin_ve_lista_e_cria_equipa_com_membros_da_empresa(self):
        response = self.client.get(reverse("projetos:equipa_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Equipas")
        self.assertContains(response, "Criar Equipa")

        response_form = self.client.get(reverse("projetos:equipa_create"))
        self.assertContains(response_form, "Operador A")
        self.assertContains(response_form, "Pendente")
        self.assertNotContains(response_form, "Externo")

        response = self.client.post(
            reverse("projetos:equipa_create"),
            {
                "nome": "Turno A",
                "membros": [str(self.empregado_a.pk), str(self.empregado_b.pk)],
                "ativo": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        equipa = Equipa.objects.get(nome="Turno A")
        self.assertEqual(equipa.empresa, self.empresa)
        self.assertSetEqual(
            set(equipa.membros.values_list("pk", flat=True)),
            {self.empregado_a.pk, self.empregado_b.pk},
        )
        self.assertContains(response, "Turno A")
        self.assertContains(response, "Operador A")

    def test_form_nao_permite_membro_de_outra_empresa(self):
        response = self.client.post(
            reverse("projetos:equipa_create"),
            {
                "nome": "Turno Externo",
                "membros": [str(self.empregado_externo.pk)],
                "ativo": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Equipa.objects.filter(nome="Turno Externo").exists())
        self.assertContains(response, "Selecione uma opção válida", status_code=200)

    def test_empresa_nao_edita_equipa_de_outra_empresa(self):
        equipa_externa = Equipa.objects.create(empresa=self.empresa_externa, nome="Outra")

        response = self.client.get(reverse("projetos:equipa_update", args=[equipa_externa.pk]))

        self.assertEqual(response.status_code, 404)
