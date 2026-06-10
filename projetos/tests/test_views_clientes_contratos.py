from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projetos.models import ClienteComercial, ClienteContrato, ClienteContratoAdenda, ClienteContratoAnexo

from .helpers import criar_empresa, criar_perfil, criar_projeto, criar_user


def _criar_contrato(*, empresa, projeto=None, nome_cliente="Cliente Teste", numero_contrato="CT-001", **kwargs):
    defaults = {
        "empresa": empresa,
        "projeto": projeto,
        "nome_cliente": nome_cliente,
        "numero_contrato": numero_contrato,
        "valor_contratado": 1000,
        "data_inicio": date(2026, 1, 1),
        "data_fim": date(2026, 12, 31),
    }
    defaults.update(kwargs)
    return ClienteContrato.objects.create(**defaults)


class ClientesContratosAdminMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Clientes 1")
        self.empresa_externa = criar_empresa(nome="Empresa Clientes 2")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Cliente Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Cliente Externo")
        self.contrato = _criar_contrato(
            empresa=self.empresa,
            projeto=self.projeto,
            nome_cliente="Cliente Interno",
            numero_contrato="INT-001",
        )
        self.contrato_externo = _criar_contrato(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome_cliente="Cliente Externo",
            numero_contrato="EXT-001",
        )
        self.user = criar_user(username="admin_clientes")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def _post_contrato_payload(self, *, projeto):
        return {
            "nome_cliente": "Cliente Novo",
            "numero_contrato": "NOVO-001",
            "projeto": str(projeto.pk),
            "tipo_cobranca": "mensal",
            "valor_contratado": "500",
            "moeda": "EUR",
            "sla_resposta_horas": "24",
            "renovacao_automatica": "",
            "periodo_renovacao_meses": "12",
            "dias_alerta_vencimento": "30",
            "workflow_comercial": "estavel",
            "contacto_nome": "Contacto",
            "contacto_email": "contacto@example.com",
            "contacto_telefone": "910000000",
            "ultimo_contacto_em": "2026-01-02",
            "proximo_followup_em": "2026-01-15",
            "dias_alerta_sem_contacto": "30",
            "data_inicio": "2026-01-01",
            "data_fim": "2026-12-31",
            "status": "ativo",
            "notas": "Contrato de teste",
            "observacao_workflow": "",
        }

    def test_admin_lista_apenas_clientes_contratos_da_sua_empresa(self):
        response = self.client.get(reverse("projetos:cliente_contrato_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contrato.nome_cliente)
        self.assertNotContains(response, self.contrato_externo.nome_cliente)

    def test_admin_nao_acede_contrato_externo_por_url_direta(self):
        urls = [
            reverse("projetos:cliente_contrato_detail", args=[self.contrato_externo.pk]),
            reverse("projetos:cliente_contrato_update", args=[self.contrato_externo.pk]),
            reverse("projetos:cliente_contrato_delete", args=[self.contrato_externo.pk]),
            reverse("projetos:cliente_contrato_exportar_dossier", args=[self.contrato_externo.pk]),
            reverse("projetos:cliente_contrato_anexo_create", args=[self.contrato_externo.pk]),
            reverse("projetos:cliente_contrato_adenda_create", args=[self.contrato_externo.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_admin_nao_cria_contrato_com_projeto_de_outra_empresa(self):
        response = self.client.post(
            reverse("projetos:cliente_contrato_create"),
            data=self._post_contrato_payload(projeto=self.projeto_externo),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ClienteContrato.objects.filter(numero_contrato="NOVO-001").exists())
        form = response.context["form"]
        self.assertIn("projeto", form.errors)

    def test_admin_nao_atualiza_contrato_com_projeto_de_outra_empresa(self):
        response = self.client.post(
            reverse("projetos:cliente_contrato_update", args=[self.contrato.pk]),
            data=self._post_contrato_payload(projeto=self.projeto_externo),
        )

        self.assertEqual(response.status_code, 200)
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.projeto_id, self.projeto.pk)
        self.assertIn("projeto", response.context["form"].errors)

    def test_admin_nao_altera_workflow_de_contrato_externo(self):
        response = self.client.post(
            reverse("projetos:cliente_contrato_aplicar_sugestao_workflow", args=[self.contrato_externo.pk]),
            data={"workflow_novo": "renovacao_pendente"},
        )

        self.assertEqual(response.status_code, 404)
        self.contrato_externo.refresh_from_db()
        self.assertEqual(self.contrato_externo.workflow_comercial, "estavel")

    def test_admin_nao_edita_ficha_comercial_de_cliente_externo_sem_contrato_proprio(self):
        ClienteComercial.objects.create(
            empresa=self.empresa_externa,
            nome_cliente="Cliente Apenas Externo",
            notas_comerciais="Não deve ser tocado",
        )

        response = self.client.post(
            reverse("projetos:cliente_comercial_update"),
            data={
                "cliente": "Cliente Apenas Externo",
                "contacto_principal_nome": "Contacto indevido",
                "classificacao_comercial": "estrategico",
                "notas_comerciais": "Alterado indevidamente",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ClienteComercial.objects.filter(
                empresa=self.empresa,
                nome_cliente__iexact="Cliente Apenas Externo",
            ).exists()
        )
        self.assertEqual(
            ClienteComercial.objects.get(empresa=self.empresa_externa, nome_cliente="Cliente Apenas Externo").notas_comerciais,
            "Não deve ser tocado",
        )


class ClientesContratosAnexosAdendasMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Anexos 1")
        self.empresa_externa = criar_empresa(nome="Empresa Anexos 2")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Anexo Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Anexo Externo")
        self.contrato = _criar_contrato(empresa=self.empresa, projeto=self.projeto, numero_contrato="ANX-001")
        self.contrato_externo = _criar_contrato(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            nome_cliente="Cliente Anexo Externo",
            numero_contrato="ANX-EXT-001",
        )
        self.anexo_externo = ClienteContratoAnexo.objects.create(
            contrato=self.contrato_externo,
            empresa=self.empresa_externa,
            titulo="Anexo externo",
            ficheiro=SimpleUploadedFile("externo.txt", b"externo", content_type="text/plain"),
        )
        self.adenda_externa = ClienteContratoAdenda.objects.create(
            contrato=self.contrato_externo,
            empresa=self.empresa_externa,
            titulo="Adenda externa",
            data_adenda=timezone.localdate(),
            nova_data_fim=timezone.localdate() + timedelta(days=30),
        )
        self.user = criar_user(username="admin_anexos")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def test_admin_nao_apaga_anexo_externo_usando_contrato_proprio(self):
        response = self.client.post(
            reverse("projetos:cliente_contrato_anexo_delete", args=[self.contrato.pk, self.anexo_externo.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ClienteContratoAnexo.objects.filter(pk=self.anexo_externo.pk).exists())

    def test_admin_nao_edita_ou_apaga_adenda_externa_usando_contrato_proprio(self):
        urls = [
            reverse("projetos:cliente_contrato_adenda_update", args=[self.contrato.pk, self.adenda_externa.pk]),
            reverse("projetos:cliente_contrato_adenda_delete", args=[self.contrato.pk, self.adenda_externa.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, data={"titulo": "Tentativa indevida"})
                self.assertEqual(response.status_code, 404)

        self.adenda_externa.refresh_from_db()
        self.assertEqual(self.adenda_externa.titulo, "Adenda externa")
