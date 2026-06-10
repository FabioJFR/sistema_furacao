from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from projetos.models import PlaneamentoTurno

from .helpers import (
    criar_empregado,
    criar_empresa,
    criar_furo,
    criar_perfil,
    criar_planeamento_turno,
    criar_projeto,
    criar_user,
)


class PlaneamentoTurnosPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Planeamento")
        self.empresa_externa = criar_empresa(nome="Empresa Planeamento Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Planeamento")
        self.projeto_externo = criar_projeto(
            empresa=self.empresa_externa,
            nome="Projeto Externo Planeamento",
        )
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Planeamento")
        self.furo_externo = criar_furo(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Furo Externo Planeamento",
        )
        self.empregado = criar_empregado(
            empresa=self.empresa,
            nome="Empregado Planeamento",
            aprovado=True,
        )
        self.empregado_externo = criar_empregado(
            empresa=self.empresa_externa,
            nome="Empregado Externo Planeamento",
            aprovado=True,
        )

    def criar_admin(self, *, username, empresa):
        user = criar_user(username=username)
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        return user

    def test_admin_lista_apenas_planeamentos_da_sua_empresa(self):
        planeamento = criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado,
            furo=self.furo,
            nome="Turno Empresa Correta",
        )
        planeamento_externo = criar_planeamento_turno(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            empregado=self.empregado_externo,
            furo=self.furo_externo,
            nome="Turno Empresa Externa",
        )
        admin = self.criar_admin(username="admin_planeamento", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:planeamento_turno_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, planeamento.nome)
        self.assertNotContains(response, planeamento_externo.nome)

    def test_admin_externo_nao_edita_apaga_ou_resolve_planeamento_por_url_direto(self):
        planeamento_a = criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado,
            furo=self.furo,
            nome="Turno Protegido A",
            data_inicio=date(2026, 5, 5),
            hora_inicio=time(8, 0),
            hora_fim=time(16, 0),
            estado="confirmado",
        )
        planeamento_b = criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado,
            furo=self.furo,
            nome="Turno Protegido B",
            data_inicio=date(2026, 5, 5),
            hora_inicio=time(10, 0),
            hora_fim=time(18, 0),
            estado="planeado",
        )
        admin_externo = self.criar_admin(
            username="admin_planeamento_externo",
            empresa=self.empresa_externa,
        )
        self.client.force_login(admin_externo)

        get_update_response = self.client.get(reverse("projetos:planeamento_turno_update", args=[planeamento_a.pk]))
        post_update_response = self.client.post(
            reverse("projetos:planeamento_turno_update", args=[planeamento_a.pk]),
            {
                "nome": "Tentativa externa",
                "projeto": str(self.projeto.pk),
                "furo": str(self.furo.pk),
                "empregado": str(self.empregado.pk),
                "maquina": "",
                "data_inicio": "2026-05-05",
                "data_fim": "",
                "hora_inicio": "08:00",
                "hora_fim": "16:00",
                "turno": "manha",
                "estado": "cancelado",
                "prioridade": "2",
                "objetivo": "",
                "notas": "",
            },
        )
        delete_response = self.client.post(reverse("projetos:planeamento_turno_delete", args=[planeamento_a.pk]))
        conflito_response = self.client.post(
            reverse("projetos:planeamento_turno_resolver_conflito", args=[planeamento_a.pk, planeamento_b.pk]),
            {"alvo": "a", "estado": "cancelado"},
        )

        self.assertEqual(get_update_response.status_code, 404)
        self.assertEqual(post_update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(conflito_response.status_code, 404)
        planeamento_a.refresh_from_db()
        self.assertEqual(planeamento_a.nome, "Turno Protegido A")
        self.assertEqual(planeamento_a.estado, "confirmado")

    def test_admin_nao_cria_planeamento_com_contexto_externo_por_post_direto(self):
        admin = self.criar_admin(username="admin_planeamento_post", empresa=self.empresa)
        self.client.force_login(admin)

        response_projeto_externo = self.client.post(
            reverse("projetos:planeamento_turno_create"),
            {
                "nome": "Planeamento projeto externo",
                "projeto": str(self.projeto_externo.pk),
                "furo": "",
                "empregado": "",
                "maquina": "",
                "data_inicio": "2026-05-05",
                "data_fim": "",
                "hora_inicio": "08:00",
                "hora_fim": "16:00",
                "turno": "manha",
                "estado": "planeado",
                "prioridade": "2",
                "objetivo": "",
                "notas": "",
            },
        )
        response_furo_empregado_externos = self.client.post(
            reverse("projetos:planeamento_turno_create"),
            {
                "nome": "Planeamento furo empregado externos",
                "projeto": str(self.projeto.pk),
                "furo": str(self.furo_externo.pk),
                "empregado": str(self.empregado_externo.pk),
                "maquina": "",
                "data_inicio": "2026-05-05",
                "data_fim": "",
                "hora_inicio": "08:00",
                "hora_fim": "16:00",
                "turno": "manha",
                "estado": "planeado",
                "prioridade": "2",
                "objetivo": "",
                "notas": "",
            },
        )

        self.assertEqual(response_projeto_externo.status_code, 200)
        self.assertEqual(response_furo_empregado_externos.status_code, 200)
        self.assertFalse(PlaneamentoTurno.objects.filter(nome__startswith="Planeamento").exists())
