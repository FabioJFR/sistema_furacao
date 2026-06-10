from django.test import TestCase
from django.urls import reverse

from projetos.models import Maquina, MaquinaTurno

from .helpers import criar_empresa, criar_furo, criar_perfil, criar_projeto, criar_user


def criar_maquina(*, empresa, nome, projeto_atual=None):
    maquina = Maquina.objects.create(
        empresa=empresa,
        nome=nome,
        projeto_atual=projeto_atual,
        estado="operacional",
        ativo=True,
    )
    if projeto_atual:
        maquina.projetos.add(projeto_atual)
    return maquina


def criar_turno_maquina(*, maquina, turno="manha"):
    return MaquinaTurno.objects.create(
        maquina=maquina,
        turno=turno,
        hora_inicio="08:00",
        hora_fim="16:00",
        ativo=True,
    )


class MaquinasPermissoesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Máquinas")
        self.empresa_externa = criar_empresa(nome="Empresa Máquinas Externa")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Máquinas")
        self.projeto_externo = criar_projeto(
            empresa=self.empresa_externa,
            nome="Projeto Externo Máquinas",
        )
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo Máquinas")
        self.furo_externo = criar_furo(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome="Furo Externo Máquinas",
        )
        self.maquina = criar_maquina(
            empresa=self.empresa,
            nome="Sonda Empresa",
            projeto_atual=self.projeto,
        )
        self.maquina.furos.add(self.furo)
        self.maquina_externa = criar_maquina(
            empresa=self.empresa_externa,
            nome="Sonda Externa",
            projeto_atual=self.projeto_externo,
        )

    def criar_admin(self, *, username, empresa):
        user = criar_user(username=username)
        criar_perfil(user=user, tipo_acesso="empresa_admin", empresa=empresa)
        return user

    def payload_maquina(self, **alteracoes):
        payload = {
            "projetos": [str(self.projeto.pk)],
            "projeto_atual": str(self.projeto.pk),
            "furos": [str(self.furo.pk)],
            "nome": "Sonda Atualizada",
            "tipo": "Perfuração",
            "marca": "",
            "modelo": "",
            "numero_serie": "",
            "data_compra": "",
            "data_registo": "",
            "data_revisao": "",
            "matricula": "",
            "seguro": "",
            "data_seguro": "",
            "data_iuc": "",
            "km": "0",
            "horimetro": "0",
            "ano_registo": "",
            "valor": "0",
            "localizacao_atual": "",
            "observacoes": "",
            "estado": "operacional",
            "ativo": "on",
        }
        payload.update(alteracoes)
        return payload

    def test_admin_lista_apenas_maquinas_da_sua_empresa(self):
        admin = self.criar_admin(username="admin_maquinas", empresa=self.empresa)
        self.client.force_login(admin)

        response = self.client.get(reverse("projetos:maquina_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.maquina.nome)
        self.assertNotContains(response, self.maquina_externa.nome)

    def test_admin_externo_nao_abre_edita_apaga_ou_gerencia_turnos_por_url_direto(self):
        turno = criar_turno_maquina(maquina=self.maquina)
        admin_externo = self.criar_admin(username="admin_maquinas_externo", empresa=self.empresa_externa)
        self.client.force_login(admin_externo)

        detail_response = self.client.get(reverse("projetos:maquina_detail", args=[self.maquina.pk]))
        update_response = self.client.post(
            reverse("projetos:maquina_update", args=[self.maquina.pk]),
            self.payload_maquina(nome="Tentativa Externa"),
        )
        delete_response = self.client.post(reverse("projetos:maquina_delete", args=[self.maquina.pk]))
        turno_create_response = self.client.post(
            reverse("projetos:maquina_turno_create", args=[self.maquina.pk]),
            {"turno": "tarde", "hora_inicio": "16:00", "hora_fim": "00:00", "ativo": "on"},
        )
        turno_update_response = self.client.post(
            reverse("projetos:maquina_turno_update", args=[self.maquina.pk, turno.pk]),
            {"turno": "manha", "hora_inicio": "09:00", "hora_fim": "17:00", "ativo": "on"},
        )
        turno_delete_response = self.client.post(
            reverse("projetos:maquina_turno_delete", args=[self.maquina.pk, turno.pk])
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(turno_create_response.status_code, 404)
        self.assertEqual(turno_update_response.status_code, 404)
        self.assertEqual(turno_delete_response.status_code, 404)
        self.maquina.refresh_from_db()
        turno.refresh_from_db()
        self.assertEqual(self.maquina.nome, "Sonda Empresa")
        self.assertEqual(turno.hora_inicio.strftime("%H:%M"), "08:00")

    def test_admin_nao_cria_maquina_com_projeto_ou_furo_externo_por_post_direto(self):
        admin = self.criar_admin(username="admin_maquinas_post", empresa=self.empresa)
        self.client.force_login(admin)

        response_projeto_externo = self.client.post(
            reverse("projetos:maquina_create"),
            self.payload_maquina(
                nome="Máquina Projeto Externo",
                projetos=[str(self.projeto_externo.pk)],
                projeto_atual=str(self.projeto_externo.pk),
                furos=[],
            ),
        )
        response_furo_externo = self.client.post(
            reverse("projetos:maquina_create"),
            self.payload_maquina(
                nome="Máquina Furo Externo",
                projetos=[str(self.projeto.pk)],
                projeto_atual=str(self.projeto.pk),
                furos=[str(self.furo_externo.pk)],
            ),
        )

        self.assertEqual(response_projeto_externo.status_code, 200)
        self.assertEqual(response_furo_externo.status_code, 200)
        self.assertFalse(Maquina.objects.filter(nome__startswith="Máquina").exists())
