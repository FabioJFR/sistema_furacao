from django.test import TestCase
from django.urls import reverse

from projetos.models import (
    AcaoCorretiva,
    AcaoPreventiva,
    IncidenteSeguranca,
    NotificacaoGestao,
    PedidoCompra,
)

from .helpers import criar_empresa, criar_perfil, criar_user


class GestaoEstadoViewsTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Gestão")
        self.user = criar_user(username="admin_gestao")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def test_pedido_compra_estado_exige_post(self):
        pedido = PedidoCompra.objects.create(
            empresa=self.empresa,
            descricao="Comprar EPI",
            estado="pendente",
        )
        url = reverse("projetos:gestao_pedido_compra_estado", args=[pedido.pk, "aprovado"])

        response_get = self.client.get(url)
        pedido.refresh_from_db()
        self.assertEqual(response_get.status_code, 302)
        self.assertEqual(pedido.estado, "pendente")

        response_post = self.client.post(url)
        pedido.refresh_from_db()
        self.assertEqual(response_post.status_code, 302)
        self.assertEqual(pedido.estado, "aprovado")

    def test_notificacao_gestao_estado_exige_post(self):
        notificacao = NotificacaoGestao.objects.create(
            empresa=self.empresa,
            titulo="Alerta gestão",
            estado="aberta",
        )
        url = reverse("projetos:gestao_notificacao_estado", args=[notificacao.pk, "resolvida"])

        response_get = self.client.get(url)
        notificacao.refresh_from_db()
        self.assertEqual(response_get.status_code, 302)
        self.assertEqual(notificacao.estado, "aberta")

        response_post = self.client.post(url)
        notificacao.refresh_from_db()
        self.assertEqual(response_post.status_code, 302)
        self.assertEqual(notificacao.estado, "resolvida")

    def test_compliance_estado_exige_post(self):
        incidente = IncidenteSeguranca.objects.create(
            empresa=self.empresa,
            titulo="Quase acidente",
            status="aberto",
        )
        corretiva = AcaoCorretiva.objects.create(
            empresa=self.empresa,
            titulo="Corrigir procedimento",
            status="aberta",
        )
        preventiva = AcaoPreventiva.objects.create(
            empresa=self.empresa,
            titulo="Prevenir reincidência",
            status="aberta",
        )
        cenarios = [
            (incidente, "status", "aberto", "investigacao", "projetos:gestao_incidente_estado"),
            (corretiva, "status", "aberta", "em_andamento", "projetos:gestao_acao_corretiva_estado"),
            (preventiva, "status", "aberta", "em_andamento", "projetos:gestao_acao_preventiva_estado"),
        ]

        for obj, campo, estado_inicial, estado_final, rota in cenarios:
            with self.subTest(rota=rota):
                url = reverse(rota, args=[obj.pk, estado_final])

                response_get = self.client.get(url)
                obj.refresh_from_db()
                self.assertEqual(response_get.status_code, 302)
                self.assertEqual(getattr(obj, campo), estado_inicial)

                response_post = self.client.post(url)
                obj.refresh_from_db()
                self.assertEqual(response_post.status_code, 302)
                self.assertEqual(getattr(obj, campo), estado_final)
