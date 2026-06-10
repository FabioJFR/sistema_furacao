from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from projetos.models import NotificacaoGestao

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_user


class NotificacoesGestaoMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Notificações 1")
        self.empresa_externa = criar_empresa(nome="Empresa Notificações 2")
        self.empregado = criar_empregado(empresa=self.empresa, nome="Responsável Interno")
        self.empregado_externo = criar_empregado(empresa=self.empresa_externa, nome="Responsável Externo")
        self.notificacao = NotificacaoGestao.objects.create(
            empresa=self.empresa,
            titulo="Notificação Interna",
            tipo="Operacional",
            prioridade="alta",
            estado="aberta",
            responsavel=self.empregado,
            prazo=timezone.now() + timezone.timedelta(days=1),
            detalhes="Alerta interno",
        )
        self.notificacao_externa = NotificacaoGestao.objects.create(
            empresa=self.empresa_externa,
            titulo="Notificação Externa",
            tipo="Operacional",
            prioridade="alta",
            estado="aberta",
            responsavel=self.empregado_externo,
            prazo=timezone.now() + timezone.timedelta(days=1),
            detalhes="Alerta externo",
        )
        self.user = criar_user(username="admin_notificacoes")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def _payload(self, *, responsavel):
        return {
            "titulo": "Notificação Nova",
            "tipo": "SLA",
            "prioridade": "media",
            "estado": "aberta",
            "responsavel": str(responsavel.pk),
            "prazo": "2026-06-01T10:30",
            "origem_url": "/app/teste/",
            "detalhes": "Detalhes de teste",
        }

    def test_admin_lista_e_exporta_apenas_notificacoes_da_sua_empresa(self):
        response = self.client.get(reverse("projetos:gestao_notificacoes"))
        response_csv = self.client.get(reverse("projetos:gestao_notificacoes_export_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.notificacao.titulo)
        self.assertNotContains(response, self.notificacao_externa.titulo)
        self.assertEqual(response_csv.status_code, 200)
        self.assertContains(response_csv, self.notificacao.titulo)
        self.assertNotContains(response_csv, self.notificacao_externa.titulo)

    def test_admin_nao_cria_notificacao_com_responsavel_externo(self):
        response = self.client.post(
            reverse("projetos:gestao_notificacao_create"),
            data=self._payload(responsavel=self.empregado_externo),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NotificacaoGestao.objects.filter(titulo="Notificação Nova").exists())
        self.assertIn("responsavel", response.context["form"].errors)

    def test_admin_nao_atualiza_notificacao_com_responsavel_externo(self):
        response = self.client.post(
            reverse("projetos:gestao_notificacao_update", args=[self.notificacao.pk]),
            data=self._payload(responsavel=self.empregado_externo),
        )

        self.assertEqual(response.status_code, 200)
        self.notificacao.refresh_from_db()
        self.assertEqual(self.notificacao.responsavel_id, self.empregado.pk)
        self.assertIn("responsavel", response.context["form"].errors)

    def test_admin_nao_edita_apaga_ou_muda_estado_de_notificacao_externa(self):
        urls = [
            reverse("projetos:gestao_notificacao_update", args=[self.notificacao_externa.pk]),
            reverse("projetos:gestao_notificacao_delete", args=[self.notificacao_externa.pk]),
            reverse("projetos:gestao_notificacao_estado", args=[self.notificacao_externa.pk, "resolvida"]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, data=self._payload(responsavel=self.empregado))
                self.assertEqual(response.status_code, 302)

        self.notificacao_externa.refresh_from_db()
        self.assertEqual(self.notificacao_externa.estado, "aberta")
        self.assertEqual(self.notificacao_externa.titulo, "Notificação Externa")
        self.assertTrue(NotificacaoGestao.objects.filter(pk=self.notificacao_externa.pk).exists())
