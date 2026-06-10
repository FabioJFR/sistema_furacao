from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from projetos.models import RegistoDiarioEmpregado

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_perfil,
    criar_projeto,
    criar_user,
)


def criar_registo(
    *,
    empresa,
    empregado,
    projeto,
    furo,
    data_registo=date(2026, 5, 20),
    observacoes="Registo teste",
):
    return RegistoDiarioEmpregado.objects.create(
        empresa=empresa,
        empregado=empregado,
        projeto=projeto,
        furo=furo,
        data=data_registo,
        hora_inicio=time(8, 0),
        hora_inicio_pausa=time(12, 0),
        hora_fim_pausa=time(13, 0),
        hora_fim=time(17, 0),
        horas_trabalhadas=8.0,
        horas_paragem=0.0,
        metros_furados=5.0,
        observacoes=observacoes,
    )


class RegistosPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Registos View")
        self.empresa_externa = criar_empresa(nome="Empresa Registos Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Registos View")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Registos View")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Registos Externo")
        self.furo_externo = criar_furo(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Furo Registos Externo",
        )

    def test_admin_lista_apenas_registos_da_sua_empresa(self):
        empregado = criar_empregado(empresa=self.empresa, nome="Empregado Registo Empresa")
        empregado_externo = criar_empregado(empresa=self.empresa_externa, nome="Empregado Registo Externo")
        registo_empresa = criar_registo(
            empresa=self.empresa,
            empregado=empregado,
            projeto=self.projeto,
            furo=self.furo,
            observacoes="Registo Empresa Correta",
        )
        registo_externo = criar_registo(
            empresa=self.empresa_externa,
            empregado=empregado_externo,
            projeto=self.projeto_externo,
            furo=self.furo_externo,
            observacoes="Registo Empresa Externa",
        )
        admin = criar_user(username="admin_registos")
        criar_perfil(user=admin, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:registos_admin_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, registo_empresa.furo.nome)
        self.assertNotContains(response, registo_externo.furo.nome)

    def test_admin_de_outra_empresa_nao_edita_registo_por_url_direto(self):
        empregado = criar_empregado(empresa=self.empresa, nome="Empregado Protegido")
        registo = criar_registo(
            empresa=self.empresa,
            empregado=empregado,
            projeto=self.projeto,
            furo=self.furo,
            observacoes="Registo Protegido",
        )
        admin_externo = criar_user(username="admin_registos_externo")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        response = self.client.post(
            reverse("projetos:registo_admin_update", args=[registo.pk]),
            {
                "empregado": str(empregado.pk),
                "planeamento_turno": "",
                "projeto": str(self.projeto.pk),
                "furo": str(self.furo.pk),
                "data": "2026-05-21",
                "hora_inicio": "08:00",
                "hora_inicio_pausa": "12:00",
                "hora_fim_pausa": "13:00",
                "hora_fim": "17:00",
                "horas_paragem": "0",
                "tipo_paragem": "",
                "metros_furados": "9",
                "observacoes": "Tentativa externa",
            },
        )

        self.assertEqual(response.status_code, 404)
        registo.refresh_from_db()
        self.assertEqual(registo.observacoes, "Registo Protegido")
        self.assertEqual(registo.metros_furados, 5.0)

    def test_empregado_lista_apenas_os_seus_registos(self):
        user = criar_user(username="empregado_registos")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        empregado = criar_empregado(empresa=self.empresa, user=user, nome="Empregado Próprio")
        outro_empregado = criar_empregado(empresa=self.empresa, nome="Outro Empregado")
        registo_proprio = criar_registo(
            empresa=self.empresa,
            empregado=empregado,
            projeto=self.projeto,
            furo=self.furo,
            observacoes="Registo Próprio",
        )
        registo_outro = criar_registo(
            empresa=self.empresa,
            empregado=outro_empregado,
            projeto=self.projeto,
            furo=self.furo,
            observacoes="Registo Outro",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("projetos:registo_diario_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(registo_proprio.pk))
        self.assertNotContains(response, str(registo_outro.pk))

    def test_empregado_nao_edita_registo_de_outro_empregado_por_url_direto(self):
        user = criar_user(username="empregado_registos_sem_acesso")
        criar_perfil(user=user, tipo_acesso="empregado", empresa=self.empresa)
        criar_empregado(empresa=self.empresa, user=user, nome="Empregado Sem Acesso")
        outro_empregado = criar_empregado(empresa=self.empresa, nome="Dono do Registo")
        registo = criar_registo(
            empresa=self.empresa,
            empregado=outro_empregado,
            projeto=self.projeto,
            furo=self.furo,
            observacoes="Registo de Outro Empregado",
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("projetos:registo_diario_update", args=[registo.pk]),
            {
                "planeamento_turno": "",
                "projeto": str(self.projeto.pk),
                "furo": str(self.furo.pk),
                "data": "2026-05-21",
                "hora_inicio": "08:00",
                "hora_inicio_pausa": "12:00",
                "hora_fim_pausa": "13:00",
                "hora_fim": "17:00",
                "horas_paragem": "0",
                "tipo_paragem": "",
                "metros_furados": "10",
                "observacoes": "Tentativa indevida",
            },
        )

        self.assertEqual(response.status_code, 404)
        registo.refresh_from_db()
        self.assertEqual(registo.observacoes, "Registo de Outro Empregado")
        self.assertEqual(registo.metros_furados, 5.0)
