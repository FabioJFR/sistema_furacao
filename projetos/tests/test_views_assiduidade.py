from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import AssiduidadeRegisto

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_projeto, criar_user


def criar_assiduidade(*, empresa, empregado, tipo="ferias", estado="pendente", motivo="Pedido"):
    return AssiduidadeRegisto.objects.create(
        empresa=empresa,
        empregado=empregado,
        tipo=tipo,
        estado=estado,
        data_inicio=date(2026, 5, 20),
        data_fim=date(2026, 5, 20),
        horas=0.0,
        motivo=motivo,
    )


class AssiduidadePermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Assiduidade")
        self.empresa_externa = criar_empresa(nome="Empresa Assiduidade Externa")
        self.empregado = criar_empregado(
            empresa=self.empresa,
            nome="Empregado Assiduidade",
            aprovado=True,
        )
        self.empregado_externo = criar_empregado(
            empresa=self.empresa_externa,
            nome="Empregado Externo Assiduidade",
            aprovado=True,
        )
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Assiduidade")
        self.projeto_externo = criar_projeto(
            empresa=self.empresa_externa,
            nome="Projeto Externo Assiduidade",
        )

    def criar_admin(self, *, username, empresa):
        user = criar_user(username=username)
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        return user

    def test_admin_lista_e_exporta_apenas_assiduidade_da_sua_empresa(self):
        item_empresa = criar_assiduidade(
            empresa=self.empresa,
            empregado=self.empregado,
            motivo="Férias Empresa Correta",
        )
        item_externo = criar_assiduidade(
            empresa=self.empresa_externa,
            empregado=self.empregado_externo,
            motivo="Férias Empresa Externa",
        )
        admin = self.criar_admin(username="admin_assiduidade", empresa=self.empresa)
        self.client.force_login(admin)

        filtros_periodo = {"mes": "5", "ano": "2026"}
        list_response = self.client.get(
            reverse("projetos:assiduidade_list"),
            filtros_periodo,
        )
        export_response = self.client.get(
            reverse("projetos:assiduidade_export_csv"),
            filtros_periodo,
        )
        export_text = export_response.content.decode("utf-8")

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, item_empresa.motivo)
        self.assertNotContains(list_response, item_externo.motivo)
        self.assertEqual(export_response.status_code, 200)
        self.assertIn(item_empresa.motivo, export_text)
        self.assertNotIn(item_externo.motivo, export_text)

    def test_admin_externo_nao_edita_apaga_aprova_ou_rejeita_assiduidade_por_url_direto(self):
        item = criar_assiduidade(
            empresa=self.empresa,
            empregado=self.empregado,
            motivo="Assiduidade Protegida",
        )
        admin_externo = self.criar_admin(
            username="admin_assiduidade_externo",
            empresa=self.empresa_externa,
        )
        self.client.force_login(admin_externo)

        get_update_response = self.client.get(reverse("projetos:assiduidade_update", args=[item.pk]))
        post_update_response = self.client.post(
            reverse("projetos:assiduidade_update", args=[item.pk]),
            {
                "empregado": str(self.empregado.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "aprovado",
                "data_inicio": "2026-05-20",
                "data_fim": "2026-05-20",
                "horas": "0",
                "motivo": "Tentativa externa",
                "notas": "",
            },
        )
        delete_response = self.client.post(reverse("projetos:assiduidade_delete", args=[item.pk]))
        aprovar_response = self.client.post(reverse("projetos:assiduidade_aprovar", args=[item.pk]))
        rejeitar_response = self.client.post(reverse("projetos:assiduidade_rejeitar", args=[item.pk]))

        self.assertEqual(get_update_response.status_code, 404)
        self.assertEqual(post_update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(aprovar_response.status_code, 404)
        self.assertEqual(rejeitar_response.status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.estado, "pendente")
        self.assertEqual(item.motivo, "Assiduidade Protegida")

    def test_admin_nao_cria_assiduidade_para_empregado_ou_projeto_de_outra_empresa_por_post_direto(self):
        admin = self.criar_admin(username="admin_assiduidade_post", empresa=self.empresa)
        self.client.force_login(admin)

        response_empregado_externo = self.client.post(
            reverse("projetos:assiduidade_create"),
            {
                "empregado": str(self.empregado_externo.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "pendente",
                "data_inicio": "2026-05-20",
                "data_fim": "2026-05-20",
                "horas": "0",
                "motivo": "Pedido indevido empregado",
                "notas": "",
            },
        )
        response_projeto_externo = self.client.post(
            reverse("projetos:assiduidade_create"),
            {
                "empregado": str(self.empregado.pk),
                "projeto": str(self.projeto_externo.pk),
                "tipo": "presenca",
                "estado": "aprovado",
                "data_inicio": "2026-05-20",
                "data_fim": "2026-05-20",
                "horas": "8",
                "motivo": "Pedido indevido projeto",
                "notas": "",
            },
        )

        self.assertEqual(response_empregado_externo.status_code, 200)
        self.assertEqual(response_projeto_externo.status_code, 200)
        self.assertFalse(AssiduidadeRegisto.objects.filter(motivo__startswith="Pedido indevido").exists())
