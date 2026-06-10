from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import Despesa, EmpregadoProjeto, Individual

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_perfil,
    criar_projeto,
    criar_user,
)


def criar_despesa(*, empresa, descricao, projeto=None, furo=None, tipo="geral", valor=100.0):
    return Despesa.objects.create(
        empresa=empresa,
        categoria="outros",
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        data=date(2026, 5, 20),
        projeto=projeto,
        furo=furo,
    )


class DespesasPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Despesas")
        self.empresa_externa = criar_empresa(nome="Empresa Despesas Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Despesas")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Despesas")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Externo")

    def test_admin_lista_apenas_despesas_da_sua_empresa(self):
        despesa_empresa = criar_despesa(
            empresa=self.empresa,
            descricao="Despesa Empresa Correta",
            projeto=self.projeto,
            tipo="projeto",
        )
        despesa_externa = criar_despesa(
            empresa=self.empresa_externa,
            descricao="Despesa Empresa Externa",
            projeto=self.projeto_externo,
            tipo="projeto",
        )
        admin = criar_user(username="admin_despesas")
        criar_perfil(user=admin, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:despesa_list_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, despesa_empresa.descricao)
        self.assertNotContains(response, despesa_externa.descricao)

    def test_admin_de_outra_empresa_nao_abre_edita_ou_apaga_despesa_por_url_direto(self):
        despesa = criar_despesa(
            empresa=self.empresa,
            descricao="Despesa Protegida",
            projeto=self.projeto,
            tipo="projeto",
        )
        admin_externo = criar_user(username="admin_despesas_externo")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        detail_response = self.client.get(reverse("projetos:despesa_detail_admin", args=[despesa.pk]))
        update_response = self.client.post(
            reverse("projetos:despesa_update_admin", args=[despesa.pk]),
            {
                "categoria": "outros",
                "tipo": "projeto",
                "descricao": "Tentativa externa",
                "valor": "999",
                "data": "2026-05-21",
                "projeto": str(self.projeto.pk),
                "furo": "",
                "maquina": "",
                "observacoes": "",
            },
        )
        delete_response = self.client.post(reverse("projetos:despesa_delete_admin", args=[despesa.pk]))

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        despesa.refresh_from_db()
        self.assertEqual(despesa.descricao, "Despesa Protegida")

    def test_conta_individual_lista_despesas_da_empresa_por_projetos_autorizados_e_gerais(self):
        user = criar_user(username="individual_despesas")
        criar_perfil(user=user, tipo_acesso="individual")
        Individual.objects.create(user=user, nome="Individual Despesas", email=user.email, ativo=True)
        empregado = criar_empregado(
            empresa=self.empresa,
            user=user,
            nome="Operador Individual Despesas",
            aprovado=True,
        )
        EmpregadoProjeto.objects.create(empregado=empregado, projeto=self.projeto, ativo=True)
        projeto_sem_acesso = criar_projeto(empresa=self.empresa, nome="Projeto Sem Acesso")
        despesa_projeto = criar_despesa(
            empresa=self.empresa,
            descricao="Despesa Projeto Autorizado",
            projeto=self.projeto,
            tipo="projeto",
        )
        despesa_furo = criar_despesa(
            empresa=self.empresa,
            descricao="Despesa Furo Autorizado",
            furo=self.furo,
            tipo="furo",
        )
        despesa_geral = criar_despesa(empresa=self.empresa, descricao="Despesa Geral")
        despesa_sem_acesso = criar_despesa(
            empresa=self.empresa,
            descricao="Despesa Projeto Sem Acesso",
            projeto=projeto_sem_acesso,
            tipo="projeto",
        )
        despesa_externa = criar_despesa(
            empresa=self.empresa_externa,
            descricao="Despesa Externa Invisível",
            projeto=self.projeto_externo,
            tipo="projeto",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:despesa_list_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, despesa_projeto.descricao)
        self.assertContains(response, despesa_furo.descricao)
        self.assertContains(response, despesa_geral.descricao)
        self.assertNotContains(response, despesa_sem_acesso.descricao)
        self.assertNotContains(response, despesa_externa.descricao)

    def test_conta_individual_nao_cria_despesa_em_projeto_sem_acesso_por_post_direto(self):
        user = criar_user(username="individual_despesas_post")
        criar_perfil(user=user, tipo_acesso="individual")
        Individual.objects.create(user=user, nome="Individual Post Despesas", email=user.email, ativo=True)
        empregado = criar_empregado(
            empresa=self.empresa,
            user=user,
            nome="Operador Individual Post",
            aprovado=True,
        )
        EmpregadoProjeto.objects.create(empregado=empregado, projeto=self.projeto, ativo=True)
        projeto_sem_acesso = criar_projeto(empresa=self.empresa, nome="Projeto Bloqueado")
        self.client.force_login(user)

        response = self.client.post(
            reverse("projetos:despesa_create_empregado"),
            {
                "categoria": "outros",
                "tipo": "projeto",
                "descricao": "Despesa indevida",
                "valor": "250",
                "data": "2026-05-21",
                "projeto": str(projeto_sem_acesso.pk),
                "furo": "",
                "maquina": "",
                "observacoes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Despesa.objects.filter(descricao="Despesa indevida").exists())
