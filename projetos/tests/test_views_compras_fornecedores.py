from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import FornecedorCompra, PedidoCompra, PropostaFornecedorCompra

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_projeto, criar_user


def _criar_pedido(*, empresa, projeto=None, solicitado_por=None, descricao="Pedido Teste", estado="pendente"):
    return PedidoCompra.objects.create(
        empresa=empresa,
        projeto=projeto,
        solicitado_por=solicitado_por,
        descricao=descricao,
        categoria="Ferramentas",
        fornecedor_sugerido="Fornecedor Sugerido",
        valor_estimado=250,
        prioridade="media",
        estado=estado,
        data_necessidade=date(2026, 6, 1),
    )


def _criar_fornecedor(*, empresa, nome="Fornecedor Teste"):
    return FornecedorCompra.objects.create(
        empresa=empresa,
        nome=nome,
        email=f"{nome.lower().replace(' ', '.')}@example.com",
        sla_dias_entrega=5,
        avaliacao=4,
        ativo=True,
    )


class ComprasFornecedoresMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Compras 1")
        self.empresa_externa = criar_empresa(nome="Empresa Compras 2")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Compra Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Compra Externo")
        self.empregado = criar_empregado(empresa=self.empresa, nome="Solicitante Interno")
        self.empregado_externo = criar_empregado(empresa=self.empresa_externa, nome="Solicitante Externo")
        self.pedido = _criar_pedido(
            empresa=self.empresa,
            projeto=self.projeto,
            solicitado_por=self.empregado,
            descricao="Pedido Interno",
        )
        self.pedido_externo = _criar_pedido(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            solicitado_por=self.empregado_externo,
            descricao="Pedido Externo",
        )
        self.fornecedor = _criar_fornecedor(empresa=self.empresa, nome="Fornecedor Interno")
        self.fornecedor_externo = _criar_fornecedor(empresa=self.empresa_externa, nome="Fornecedor Externo")
        self.proposta = PropostaFornecedorCompra.objects.create(
            pedido=self.pedido,
            fornecedor=self.fornecedor,
            valor_proposto=220,
            prazo_entrega_dias=4,
        )
        self.proposta_externa = PropostaFornecedorCompra.objects.create(
            pedido=self.pedido_externo,
            fornecedor=self.fornecedor_externo,
            valor_proposto=200,
            prazo_entrega_dias=3,
        )
        self.user = criar_user(username="admin_compras")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def _pedido_payload(self, *, projeto, solicitado_por):
        return {
            "projeto": str(projeto.pk),
            "solicitado_por": str(solicitado_por.pk),
            "descricao": "Pedido Novo",
            "categoria": "Consumíveis",
            "fornecedor_sugerido": "Fornecedor X",
            "valor_estimado": "300",
            "prioridade": "alta",
            "data_necessidade": "2026-06-10",
            "observacoes": "Pedido de teste",
        }

    def _fornecedor_payload(self, *, nome="Fornecedor Alterado"):
        return {
            "nome": nome,
            "contacto_nome": "Contacto",
            "email": "fornecedor@example.com",
            "telefone": "910000000",
            "sla_dias_entrega": "3",
            "avaliacao": "4.5",
            "ativo": "on",
            "observacoes": "Fornecedor de teste",
        }

    def _proposta_payload(self, *, fornecedor):
        return {
            "fornecedor": str(fornecedor.pk),
            "valor_proposto": "199",
            "prazo_entrega_dias": "2",
            "observacoes": "Proposta de teste",
            "selecionada": "",
        }

    def test_admin_lista_e_exporta_apenas_pedidos_da_sua_empresa(self):
        response = self.client.get(reverse("projetos:gestao_compras_fornecedores"))
        response_csv = self.client.get(reverse("projetos:gestao_compras_export_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.pedido.descricao)
        self.assertNotContains(response, self.pedido_externo.descricao)
        self.assertEqual(response_csv.status_code, 200)
        self.assertContains(response_csv, self.pedido.descricao)
        self.assertNotContains(response_csv, self.pedido_externo.descricao)

    def test_admin_nao_cria_pedido_com_projeto_ou_solicitante_externo(self):
        response_projeto = self.client.post(
            reverse("projetos:gestao_pedido_compra_create"),
            data=self._pedido_payload(projeto=self.projeto_externo, solicitado_por=self.empregado),
        )
        response_empregado = self.client.post(
            reverse("projetos:gestao_pedido_compra_create"),
            data=self._pedido_payload(projeto=self.projeto, solicitado_por=self.empregado_externo),
        )

        self.assertEqual(response_projeto.status_code, 200)
        self.assertEqual(response_empregado.status_code, 200)
        self.assertFalse(PedidoCompra.objects.filter(descricao="Pedido Novo").exists())
        self.assertIn("projeto", response_projeto.context["form"].errors)
        self.assertIn("solicitado_por", response_empregado.context["form"].errors)

    def test_admin_nao_atualiza_pedido_com_projeto_ou_solicitante_externo(self):
        response = self.client.post(
            reverse("projetos:gestao_pedido_compra_update", args=[self.pedido.pk]),
            data=self._pedido_payload(projeto=self.projeto_externo, solicitado_por=self.empregado_externo),
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.projeto_id, self.projeto.pk)
        self.assertEqual(self.pedido.solicitado_por_id, self.empregado.pk)
        self.assertIn("projeto", response.context["form"].errors)
        self.assertIn("solicitado_por", response.context["form"].errors)

    def test_admin_nao_muda_estado_ou_remove_pedido_externo(self):
        urls = [
            reverse("projetos:gestao_pedido_compra_estado", args=[self.pedido_externo.pk, "aprovado"]),
            reverse("projetos:gestao_pedido_compra_delete", args=[self.pedido_externo.pk]),
            reverse("projetos:gestao_pedido_compra_comparar", args=[self.pedido_externo.pk]),
            reverse("projetos:gestao_pedido_compra_selecionar_melhor", args=[self.pedido_externo.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url)
                self.assertEqual(response.status_code, 302)

        self.pedido_externo.refresh_from_db()
        self.assertEqual(self.pedido_externo.estado, "pendente")
        self.assertTrue(PedidoCompra.objects.filter(pk=self.pedido_externo.pk).exists())
        self.assertFalse(
            PropostaFornecedorCompra.objects.filter(pk=self.proposta_externa.pk, selecionada=True).exists()
        )

    def test_admin_nao_edita_ou_remove_fornecedor_externo(self):
        response_update = self.client.post(
            reverse("projetos:gestao_fornecedor_update", args=[self.fornecedor_externo.pk]),
            data=self._fornecedor_payload(nome="Fornecedor Invadido"),
        )
        response_delete = self.client.post(reverse("projetos:gestao_fornecedor_delete", args=[self.fornecedor_externo.pk]))

        self.assertEqual(response_update.status_code, 302)
        self.assertEqual(response_delete.status_code, 302)
        self.fornecedor_externo.refresh_from_db()
        self.assertEqual(self.fornecedor_externo.nome, "Fornecedor Externo")
        self.assertTrue(FornecedorCompra.objects.filter(pk=self.fornecedor_externo.pk).exists())

    def test_admin_nao_cria_ou_atualiza_proposta_com_fornecedor_externo(self):
        response_create = self.client.post(
            reverse("projetos:gestao_proposta_compra_create", args=[self.pedido.pk]),
            data=self._proposta_payload(fornecedor=self.fornecedor_externo),
        )
        response_update = self.client.post(
            reverse("projetos:gestao_proposta_compra_update", args=[self.proposta.pk]),
            data=self._proposta_payload(fornecedor=self.fornecedor_externo),
        )

        self.assertEqual(response_create.status_code, 200)
        self.assertEqual(response_update.status_code, 200)
        self.assertEqual(PropostaFornecedorCompra.objects.filter(pedido=self.pedido).count(), 1)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.fornecedor_id, self.fornecedor.pk)
        self.assertIn("fornecedor", response_create.context["form"].errors)
        self.assertIn("fornecedor", response_update.context["form"].errors)

    def test_admin_nao_edita_remove_ou_seleciona_proposta_externa(self):
        urls = [
            reverse("projetos:gestao_proposta_compra_update", args=[self.proposta_externa.pk]),
            reverse("projetos:gestao_proposta_compra_delete", args=[self.proposta_externa.pk]),
            reverse(
                "projetos:gestao_pedido_compra_selecionar_proposta",
                args=[self.pedido.pk, self.proposta_externa.pk],
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, data=self._proposta_payload(fornecedor=self.fornecedor))
                self.assertEqual(response.status_code, 302)

        self.proposta_externa.refresh_from_db()
        self.assertEqual(self.proposta_externa.valor_proposto, 200)
        self.assertFalse(self.proposta_externa.selecionada)
        self.assertTrue(PropostaFornecedorCompra.objects.filter(pk=self.proposta_externa.pk).exists())
