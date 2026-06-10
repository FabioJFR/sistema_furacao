from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projetos.models import Maquina, MaquinaAvaria

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_perfil,
    criar_projeto,
    criar_user,
)


def criar_maquina(*, empresa, nome="Sonda Teste", projeto_atual=None):
    return Maquina.objects.create(
        empresa=empresa,
        nome=nome,
        projeto_atual=projeto_atual,
    )


def criar_avaria(
    *,
    empresa,
    maquina,
    descricao,
    projeto=None,
    furo=None,
    responsavel_empregado=None,
    status="aberta",
):
    return MaquinaAvaria.objects.create(
        empresa=empresa,
        maquina=maquina,
        projeto=projeto,
        furo=furo,
        responsavel_empregado=responsavel_empregado,
        data_inicio=timezone.now(),
        status=status,
        descricao=descricao,
    )


class MaquinaAvariasPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Avarias")
        self.empresa_externa = criar_empresa(nome="Empresa Avarias Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Avarias")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Avarias")
        self.maquina = criar_maquina(
            empresa=self.empresa,
            nome="Sonda Empresa",
            projeto_atual=self.projeto,
        )
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Avarias Externo")
        self.maquina_externa = criar_maquina(
            empresa=self.empresa_externa,
            nome="Sonda Externa",
            projeto_atual=self.projeto_externo,
        )

    def test_admin_lista_apenas_avarias_da_sua_empresa(self):
        avaria_empresa = criar_avaria(
            empresa=self.empresa,
            maquina=self.maquina,
            projeto=self.projeto,
            descricao="Avaria Empresa Correta",
        )
        avaria_externa = criar_avaria(
            empresa=self.empresa_externa,
            maquina=self.maquina_externa,
            projeto=self.projeto_externo,
            descricao="Avaria Empresa Externa",
        )
        admin = criar_user(username="admin_avarias")
        criar_perfil(user=admin, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:avaria_maquina_list_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, avaria_empresa.descricao)
        self.assertNotContains(response, avaria_externa.descricao)

    def test_admin_de_outra_empresa_nao_edita_avaria_por_url_direto(self):
        avaria = criar_avaria(
            empresa=self.empresa,
            maquina=self.maquina,
            projeto=self.projeto,
            descricao="Avaria Protegida",
        )
        admin_externo = criar_user(username="admin_avarias_externo")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        get_response = self.client.get(reverse("projetos:avaria_maquina_update_admin", args=[avaria.pk]))
        post_response = self.client.post(
            reverse("projetos:avaria_maquina_update_admin", args=[avaria.pk]),
            {
                "responsavel_empregado": "",
                "status": "resolvida",
                "solucao": "Tentativa externa",
            },
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        avaria.refresh_from_db()
        self.assertEqual(avaria.status, "aberta")
        self.assertEqual(avaria.solucao, "")

    def test_empregado_lista_apenas_avarias_atribuidas_a_si(self):
        user = criar_user(username="empregado_avarias")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, user=user, nome="Responsável Avaria")
        outro_user = criar_user(username="empregado_avarias_outro")
        criar_perfil(user=outro_user, tipo_acesso="empregado", empresa=self.empresa)
        outro_empregado = criar_empregado(empresa=self.empresa, user=outro_user, nome="Outro Responsável")
        avaria_atribuida = criar_avaria(
            empresa=self.empresa,
            maquina=self.maquina,
            projeto=self.projeto,
            descricao="Avaria Atribuída",
            responsavel_empregado=empregado,
        )
        avaria_de_outro = criar_avaria(
            empresa=self.empresa,
            maquina=self.maquina,
            projeto=self.projeto,
            descricao="Avaria de Outro",
            responsavel_empregado=outro_empregado,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:avaria_maquina_minhas_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, avaria_atribuida.descricao)
        self.assertNotContains(response, avaria_de_outro.descricao)

    def test_empregado_nao_edita_avaria_nao_atribuida_por_url_direto(self):
        user = criar_user(username="empregado_avarias_sem_acesso")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        criar_empregado(empresa=self.empresa, user=user, nome="Sem Atribuição")
        responsavel = criar_empregado(empresa=self.empresa, nome="Responsável Real")
        avaria = criar_avaria(
            empresa=self.empresa,
            maquina=self.maquina,
            projeto=self.projeto,
            descricao="Avaria Não Atribuída",
            responsavel_empregado=responsavel,
        )
        self.client.force_login(user)

        get_response = self.client.get(reverse("projetos:avaria_maquina_update_empregado", args=[avaria.pk]))
        post_response = self.client.post(
            reverse("projetos:avaria_maquina_update_empregado", args=[avaria.pk]),
            {
                "status": "resolvida",
                "solucao": "Tentativa sem atribuição",
            },
        )

        self.assertEqual(get_response.status_code, 404)
        self.assertEqual(post_response.status_code, 404)
        avaria.refresh_from_db()
        self.assertEqual(avaria.status, "aberta")
        self.assertEqual(avaria.solucao, "")

    def test_empregado_nao_cria_avaria_com_maquina_de_outra_empresa_por_post_direto(self):
        user = criar_user(username="empregado_avarias_post")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        criar_empregado(empresa=self.empresa, user=user, nome="Operador Avarias")
        self.client.force_login(user)

        response = self.client.post(
            reverse("projetos:avaria_maquina_create_empregado"),
            {
                "maquina": str(self.maquina_externa.pk),
                "furo": "",
                "descricao": "Avaria externa indevida",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(MaquinaAvaria.objects.filter(descricao="Avaria externa indevida").exists())
