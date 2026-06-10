from django.test import TestCase
from django.urls import reverse

from projetos.models import EmpregadoFuro, Medicao

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_perfil,
    criar_projeto,
    criar_user,
)


def criar_medicao(*, empresa, furo, profundidade=10.0, tipo_rocha="Granito"):
    return Medicao.objects.create(
        empresa=empresa,
        furo=furo,
        profundidade_medida=profundidade,
        inclinacao_real_medida=-10.0,
        azimute_real_medido=120.0,
        magnetismo=0.5,
        tipo_rocha=tipo_rocha,
        cor="gray",
        dureza=4.0,
        observacoes=f"Medição {tipo_rocha}",
    )


class MedicoesPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Medições")
        self.empresa_externa = criar_empresa(nome="Empresa Medições Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Medições")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Medições")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Externo Medições")
        self.furo_externo = criar_furo(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Furo Externo Medições",
        )

    def test_admin_lista_apenas_medicoes_da_sua_empresa(self):
        medicao_empresa = criar_medicao(
            empresa=self.empresa,
            furo=self.furo,
            tipo_rocha="Granito Empresa",
        )
        medicao_externa = criar_medicao(
            empresa=self.empresa_externa,
            furo=self.furo_externo,
            tipo_rocha="Xisto Externo",
        )
        admin = criar_user(username="admin_medicoes")
        criar_perfil(user=admin, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:medicao_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, medicao_empresa.furo.nome)
        self.assertNotContains(response, medicao_externa.furo.nome)

    def test_admin_de_outra_empresa_nao_edita_ou_apaga_medicao_por_url_direto(self):
        medicao = criar_medicao(
            empresa=self.empresa,
            furo=self.furo,
            tipo_rocha="Medição Protegida",
        )
        admin_externo = criar_user(username="admin_medicoes_externo")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        update_response = self.client.post(
            reverse("projetos:medicao_update", args=[medicao.pk]),
            {
                "profundidade_medida": "50",
                "inclinacao_real_medida": "-15",
                "azimute_real_medido": "180",
                "magnetismo": "1",
                "latitude": "",
                "longitude": "",
                "altitude": "",
                "tipo_rocha": "Tentativa externa",
                "cor": "red",
                "dureza": "5",
                "observacoes": "Tentativa externa",
            },
        )
        delete_response = self.client.post(reverse("projetos:medicao_delete", args=[medicao.pk]))

        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        medicao.refresh_from_db()
        self.assertEqual(medicao.tipo_rocha, "Medição Protegida")

    def test_admin_nao_cria_medicao_em_furo_de_outra_empresa_por_url_direto(self):
        admin = criar_user(username="admin_medicoes_create")
        criar_perfil(user=admin, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("projetos:medicao_create", args=[self.furo_externo.pk]),
            {
                "profundidade_medida": "12",
                "inclinacao_real_medida": "-5",
                "azimute_real_medido": "100",
                "magnetismo": "0.3",
                "latitude": "",
                "longitude": "",
                "altitude": "",
                "tipo_rocha": "Medição indevida",
                "cor": "gray",
                "dureza": "3",
                "observacoes": "Não deve gravar",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Medicao.objects.filter(tipo_rocha="Medição indevida").exists())

    def test_empregado_lista_apenas_medicoes_de_furos_autorizados(self):
        user = criar_user(username="empregado_medicoes")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, user=user, nome="Operador Medições")
        EmpregadoFuro.objects.create(empresa=self.empresa, empregado=empregado, furo=self.furo)
        furo_sem_acesso = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Sem Acesso Medições",
        )
        medicao_autorizada = criar_medicao(
            empresa=self.empresa,
            furo=self.furo,
            tipo_rocha="Medição Autorizada",
        )
        medicao_sem_acesso = criar_medicao(
            empresa=self.empresa,
            furo=furo_sem_acesso,
            tipo_rocha="Medição Sem Acesso",
        )
        medicao_externa = criar_medicao(
            empresa=self.empresa_externa,
            furo=self.furo_externo,
            tipo_rocha="Medição Externa",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:medicao_list_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, medicao_autorizada.furo.nome)
        self.assertNotContains(response, medicao_sem_acesso.furo.nome)
        self.assertNotContains(response, medicao_externa.furo.nome)

    def test_empregado_nao_abre_detalhe_de_medicao_sem_acesso(self):
        user = criar_user(username="empregado_medicoes_sem_acesso")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, user=user, nome="Operador Sem Acesso")
        EmpregadoFuro.objects.create(empresa=self.empresa, empregado=empregado, furo=self.furo)
        furo_sem_acesso = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Bloqueado Medições",
        )
        medicao_sem_acesso = criar_medicao(
            empresa=self.empresa,
            furo=furo_sem_acesso,
            tipo_rocha="Medição Bloqueada",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("projetos:medicao_detail_empregado", args=[medicao_sem_acesso.pk])
        )

        self.assertRedirects(
            response,
            reverse("projetos:medicao_list_empregado"),
            fetch_redirect_response=False,
        )

    def test_empregado_nao_abre_detalhe_de_medicao_de_outra_empresa(self):
        user = criar_user(username="empregado_medicoes_empresa_externa")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, user=user, nome="Operador Empresa")
        EmpregadoFuro.objects.create(empresa=self.empresa, empregado=empregado, furo=self.furo)
        medicao_externa = criar_medicao(
            empresa=self.empresa_externa,
            furo=self.furo_externo,
            tipo_rocha="Medição Externa Bloqueada",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("projetos:medicao_detail_empregado", args=[medicao_externa.pk])
        )

        self.assertRedirects(
            response,
            reverse("projetos:medicao_list_empregado"),
            fetch_redirect_response=False,
        )

    def test_geologo_lista_todas_as_medicoes_da_empresa_mas_nao_de_outra_empresa(self):
        user = criar_user(username="geologo_medicoes")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        criar_empregado(
            empresa=self.empresa,
            user=user,
            nome="Geólogo Medições",
            funcao="geologo",
        )
        medicao_empresa = criar_medicao(
            empresa=self.empresa,
            furo=self.furo,
            tipo_rocha="Medição Geologia Empresa",
        )
        medicao_externa = criar_medicao(
            empresa=self.empresa_externa,
            furo=self.furo_externo,
            tipo_rocha="Medição Geologia Externa",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:medicao_list_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, medicao_empresa.furo.nome)
        self.assertNotContains(response, medicao_externa.furo.nome)
