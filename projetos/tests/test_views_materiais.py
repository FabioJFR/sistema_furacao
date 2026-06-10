from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import DevolucaoMaterial, LevantamentoMaterial, Material

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_user


def criar_material(*, empresa, nome, quantidade=10):
    return Material.objects.create(
        empresa=empresa,
        nome=nome,
        quantidade=quantidade,
        stock_minimo=1,
        ativo=True,
    )


def criar_levantamento(*, empregado, material, quantidade=1):
    return LevantamentoMaterial.objects.create(
        empregado=empregado,
        empresa=empregado.empresa,
        material=material,
        quantidade=quantidade,
        data=date(2026, 5, 20),
    )


def criar_devolucao(*, empregado, material, quantidade=1):
    return DevolucaoMaterial.objects.create(
        empregado=empregado,
        empresa=empregado.empresa,
        material=material,
        quantidade=quantidade,
        data=date(2026, 5, 21),
    )


class MateriaisPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Materiais")
        self.empresa_externa = criar_empresa(nome="Empresa Materiais Externa")
        self.material = criar_material(empresa=self.empresa, nome="Material Empresa", quantidade=10)
        self.material_externo = criar_material(
            empresa=self.empresa_externa,
            nome="Material Externo",
            quantidade=10,
        )

    def criar_admin(self, *, username, empresa):
        user = criar_user(username=username)
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        return user

    def criar_operador(self, *, username, empresa):
        user = criar_user(username=username)
        criar_perfil(user=user, tipo_acesso="empregado", empresa=empresa)
        empregado = criar_empregado(
            empresa=empresa,
            user=user,
            nome=f"Operador {username}",
            aprovado=True,
        )
        return user, empregado

    def test_admin_lista_apenas_materiais_da_sua_empresa(self):
        admin = self.criar_admin(username="admin_materiais", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:material_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.material.nome)
        self.assertNotContains(response, self.material_externo.nome)

    def test_admin_externo_nao_abre_edita_apaga_nem_movimenta_material_por_url_direto(self):
        admin_externo = self.criar_admin(username="admin_materiais_externo", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        detail_response = self.client.get(reverse("projetos:material_detail", args=[self.material.pk]))
        update_response = self.client.get(reverse("projetos:material_update", args=[self.material.pk]))
        delete_response = self.client.post(reverse("projetos:material_delete", args=[self.material.pk]))
        entrada_response = self.client.post(reverse("projetos:entrada_material", args=[self.material.pk]), {"quantidade": 4})
        saida_response = self.client.post(reverse("projetos:saida_material", args=[self.material.pk]), {"quantidade": 4})

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(entrada_response.status_code, 404)
        self.assertEqual(saida_response.status_code, 404)
        self.material.refresh_from_db()
        self.assertEqual(self.material.quantidade, 10)

    def test_admin_lista_apenas_levantamentos_e_devolucoes_da_sua_empresa(self):
        _, empregado = self.criar_operador(username="operador_movimentos", empresa=self.empresa)
        _, empregado_externo = self.criar_operador(
            username="operador_movimentos_externo",
            empresa=self.empresa_externa,
        )
        levantamento = criar_levantamento(empregado=empregado, material=self.material)
        levantamento_externo = criar_levantamento(empregado=empregado_externo, material=self.material_externo)
        devolucao = criar_devolucao(empregado=empregado, material=self.material)
        devolucao_externa = criar_devolucao(empregado=empregado_externo, material=self.material_externo)
        admin = self.criar_admin(username="admin_movimentos", empresa=self.empresa)
        self.client.force_login(admin)

        response_levantamentos = self.client.get(reverse("projetos:levantamento_material_admin_list"))
        response_devolucoes = self.client.get(reverse("projetos:devolucao_material_admin_list"))

        self.assertEqual(response_levantamentos.status_code, 200)
        self.assertContains(response_levantamentos, levantamento.material.nome)
        self.assertNotContains(response_levantamentos, levantamento_externo.material.nome)
        self.assertEqual(response_devolucoes.status_code, 200)
        self.assertContains(response_devolucoes, devolucao.material.nome)
        self.assertNotContains(response_devolucoes, devolucao_externa.material.nome)

    def test_empregado_lista_apenas_os_seus_movimentos(self):
        user, empregado = self.criar_operador(username="operador_pessoal", empresa=self.empresa)
        _, outro_empregado = self.criar_operador(username="operador_outro", empresa=self.empresa)
        material_outro = criar_material(empresa=self.empresa, nome="Material Apenas do Outro")
        criar_levantamento(empregado=empregado, material=self.material, quantidade=1)
        criar_levantamento(empregado=outro_empregado, material=material_outro, quantidade=9)
        criar_devolucao(empregado=empregado, material=self.material, quantidade=2)
        criar_devolucao(empregado=outro_empregado, material=material_outro, quantidade=8)
        self.client.force_login(user)

        response_levantamentos = self.client.get(reverse("projetos:levantamento_list"))
        response_devolucoes = self.client.get(reverse("projetos:devolucao_material_list"))

        self.assertEqual(response_levantamentos.status_code, 200)
        self.assertContains(response_levantamentos, self.material.nome)
        self.assertNotContains(response_levantamentos, material_outro.nome)
        self.assertEqual(response_devolucoes.status_code, 200)
        self.assertContains(response_devolucoes, self.material.nome)
        self.assertNotContains(response_devolucoes, material_outro.nome)

    def test_empregado_nao_levanta_nem_devolve_material_de_outra_empresa_por_post_direto(self):
        user, _ = self.criar_operador(username="operador_post_externo", empresa=self.empresa)
        self.client.force_login(user)
        payload = {
            "material": str(self.material_externo.pk),
            "projeto": "",
            "furo": "",
            "quantidade": "2",
            "data": "2026-05-22",
            "observacoes": "Tentativa externa",
        }

        response_levantamento = self.client.post(reverse("projetos:levantamento_create"), payload)
        response_devolucao = self.client.post(reverse("projetos:devolucao_material_create"), payload)

        self.assertEqual(response_levantamento.status_code, 200)
        self.assertEqual(response_devolucao.status_code, 200)
        self.assertEqual(LevantamentoMaterial.objects.count(), 0)
        self.assertEqual(DevolucaoMaterial.objects.count(), 0)
        self.material_externo.refresh_from_db()
        self.assertEqual(self.material_externo.quantidade, 10)
