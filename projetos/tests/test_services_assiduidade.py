from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from projetos.forms import AssiduidadeRegistoForm
from projetos.models import AssiduidadeRegisto, NotificacaoGestao
from projetos.services.assiduidade import (
    aprovar_assiduidade,
    criar_assiduidade,
    criar_pedidos_ferias_empregado,
    rejeitar_assiduidade,
)

from .helpers import criar_empresa, criar_empregado


class AssiduidadeServicesTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa()
        self.empregado = criar_empregado(
            empresa=self.empresa,
            nome="Operador 1",
            email="operador1@example.com",
        )

    def _origem_ferias(self, pedido):
        return f"{reverse('projetos:calendario_turnos_empregado')}?assiduidade={pedido.pk}"

    def test_criar_pedidos_ferias_empregado_cria_registos_e_notificacoes(self):
        datas = [date(2026, 8, 10), date(2026, 8, 11)]

        resultado = criar_pedidos_ferias_empregado(
            empregado=self.empregado,
            datas=datas,
            motivo="Férias de verão",
            notas="Planeadas com antecedência.",
        )

        self.assertEqual(len(resultado["criados"]), 2)
        self.assertEqual(
            AssiduidadeRegisto.objects.filter(
                empresa=self.empresa,
                empregado=self.empregado,
                tipo="ferias",
                estado="pendente",
            ).count(),
            2,
        )
        self.assertEqual(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                tipo="ferias_empregado",
                estado="aberta",
            ).count(),
            2,
        )

    def test_criar_pedidos_ferias_empregado_bloqueia_dias_dentro_de_intervalo_existente(self):
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 15),
            horas=0.0,
        )

        resultado = criar_pedidos_ferias_empregado(
            empregado=self.empregado,
            datas=[date(2026, 8, 12), date(2026, 8, 16)],
        )

        self.assertEqual(len(resultado["criados"]), 1)
        self.assertEqual(resultado["criados"][0].data_inicio, date(2026, 8, 16))
        self.assertEqual(resultado["datas_bloqueadas"], [date(2026, 8, 12)])

    def test_criar_pedidos_ferias_empregado_impede_exceder_saldo_anual_com_pendentes(self):
        self.empregado.dias_ferias_anuais = 2
        self.empregado.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 10),
            horas=0.0,
        )

        with self.assertRaisesMessage(ValidationError, "excede o saldo de férias disponível"):
            criar_pedidos_ferias_empregado(
                empregado=self.empregado,
                datas=[date(2026, 8, 11), date(2026, 8, 12)],
            )

        self.assertEqual(
            AssiduidadeRegisto.objects.filter(
                empresa=self.empresa,
                empregado=self.empregado,
                tipo="ferias",
            ).count(),
            1,
        )

    def test_criar_assiduidade_admin_impede_ferias_acima_do_saldo(self):
        self.empregado.dias_ferias_anuais = 1
        self.empregado.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 10),
            horas=0.0,
        )
        form = AssiduidadeRegistoForm(
            data={
                "empregado": str(self.empregado.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "pendente",
                "data_inicio": "2026-08-11",
                "data_fim": "2026-08-11",
                "horas": "0",
                "motivo": "",
                "notas": "",
            },
            empresa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaisesMessage(ValidationError, "excede o saldo de férias disponível"):
            criar_assiduidade(form=form, empresa=self.empresa)

    def test_criar_assiduidade_admin_impede_ferias_sobrepostas(self):
        self.empregado.dias_ferias_anuais = 22
        self.empregado.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 15),
            horas=0.0,
        )
        form = AssiduidadeRegistoForm(
            data={
                "empregado": str(self.empregado.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "pendente",
                "data_inicio": "2026-08-12",
                "data_fim": "2026-08-16",
                "horas": "0",
                "motivo": "",
                "notas": "",
            },
            empresa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaisesMessage(ValidationError, "sobrepõem-se"):
            criar_assiduidade(form=form, empresa=self.empresa)

    def test_criar_assiduidade_admin_ferias_aprovadas_cria_notificacao_aprovada(self):
        form = AssiduidadeRegistoForm(
            data={
                "empregado": str(self.empregado.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "aprovado",
                "data_inicio": "2026-08-12",
                "data_fim": "2026-08-12",
                "horas": "0",
                "motivo": "",
                "notas": "",
            },
            empresa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        criar_assiduidade(form=form, empresa=self.empresa)

        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 12/08/2026",
                estado="aberta",
            ).exists()
        )
        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias submetido · 12/08/2026",
            ).exists()
        )

    def test_criar_assiduidade_admin_ferias_rejeitadas_cria_notificacao_rejeitada(self):
        form = AssiduidadeRegistoForm(
            data={
                "empregado": str(self.empregado.pk),
                "projeto": "",
                "tipo": "ferias",
                "estado": "rejeitado",
                "data_inicio": "2026-08-12",
                "data_fim": "2026-08-12",
                "horas": "0",
                "motivo": "",
                "notas": "",
            },
            empresa=self.empresa,
        )

        self.assertTrue(form.is_valid(), form.errors)
        criar_assiduidade(form=form, empresa=self.empresa)

        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 12/08/2026",
                estado="aberta",
            ).exists()
        )
        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias submetido · 12/08/2026",
            ).exists()
        )

    def test_aprovar_assiduidade_admin_impede_ferias_acima_do_saldo(self):
        self.empregado.dias_ferias_anuais = 1
        self.empregado.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 10),
            horas=0.0,
        )
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="rejeitado",
            data_inicio=date(2026, 8, 11),
            data_fim=date(2026, 8, 11),
            horas=0.0,
        )

        with self.assertRaisesMessage(ValidationError, "excede o saldo de férias disponível"):
            aprovar_assiduidade(obj=pedido)
        self.assertEqual(pedido.estado, "rejeitado")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "rejeitado")

    def test_aprovar_assiduidade_admin_impede_ferias_sobrepostas(self):
        self.empregado.dias_ferias_anuais = 22
        self.empregado.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 15),
            horas=0.0,
        )
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="rejeitado",
            data_inicio=date(2026, 8, 12),
            data_fim=date(2026, 8, 16),
            horas=0.0,
        )

        with self.assertRaisesMessage(ValidationError, "sobrepõem-se"):
            aprovar_assiduidade(obj=pedido)
        self.assertEqual(pedido.estado, "rejeitado")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "rejeitado")

    def test_aprovar_pedido_ferias_resolve_submissao_e_cria_confirmacao(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 15),
            data_fim=date(2026, 8, 15),
            horas=0.0,
        )
        criar_pedidos_ferias_empregado(
            empregado=self.empregado,
            datas=[date(2026, 8, 16)],
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias submetido · 15/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            origem_url=self._origem_ferias(pedido),
        )

        aprovar_assiduidade(obj=pedido)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "aprovado")
        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias submetido · 15/08/2026",
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 15/08/2026",
                estado="aberta",
            ).exists()
        )

    def test_rejeitar_ferias_aprovadas_resolve_notificacao_aprovada_anterior(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 18),
            data_fim=date(2026, 8, 18),
            horas=0.0,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias aprovado · 18/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            origem_url=self._origem_ferias(pedido),
        )

        rejeitar_assiduidade(obj=pedido)

        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 18/08/2026",
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 18/08/2026",
                estado="aberta",
            ).exists()
        )

    def test_aprovar_ferias_rejeitadas_resolve_notificacao_rejeitada_anterior(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="rejeitado",
            data_inicio=date(2026, 8, 19),
            data_fim=date(2026, 8, 19),
            horas=0.0,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias rejeitado · 19/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="em_andamento",
            origem_url=self._origem_ferias(pedido),
        )

        aprovar_assiduidade(obj=pedido)

        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 19/08/2026",
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 19/08/2026",
                estado="aberta",
            ).exists()
        )

    def test_resolver_notificacao_ferias_nao_afeta_outro_pedido_na_mesma_data(self):
        pedido_a = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="rejeitado",
            data_inicio=date(2026, 8, 21),
            data_fim=date(2026, 8, 21),
            horas=0.0,
        )
        pedido_b = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="rejeitado",
            data_inicio=date(2026, 8, 21),
            data_fim=date(2026, 8, 21),
            horas=0.0,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias rejeitado · 21/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            origem_url=self._origem_ferias(pedido_a),
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias rejeitado · 21/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            origem_url=self._origem_ferias(pedido_b),
        )

        aprovar_assiduidade(obj=pedido_a)

        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 21/08/2026",
                origem_url=self._origem_ferias(pedido_a),
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 21/08/2026",
                origem_url=self._origem_ferias(pedido_b),
                estado="aberta",
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 21/08/2026",
                origem_url=self._origem_ferias(pedido_a),
                estado="aberta",
            ).exists()
        )

    def test_resolver_notificacao_ferias_resolve_origem_legada_sem_uuid(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 22),
            data_fim=date(2026, 8, 22),
            horas=0.0,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias submetido · 22/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="aberta",
            origem_url=reverse("projetos:calendario_turnos_empregado"),
        )

        aprovar_assiduidade(obj=pedido)

        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias submetido · 22/08/2026",
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias aprovado · 22/08/2026",
                origem_url=self._origem_ferias(pedido),
                estado="aberta",
            ).exists()
        )

    def test_rejeitar_pedido_ferias_resolve_submissao_e_cria_confirmacao(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 20),
            data_fim=date(2026, 8, 20),
            horas=0.0,
        )
        NotificacaoGestao.objects.create(
            empresa=self.empresa,
            responsavel=self.empregado,
            titulo="Pedido de férias submetido · 20/08/2026",
            tipo="ferias_empregado",
            prioridade="media",
            estado="em_andamento",
            origem_url=self._origem_ferias(pedido),
        )

        rejeitar_assiduidade(obj=pedido)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "rejeitado")
        self.assertFalse(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias submetido · 20/08/2026",
                estado__in=["aberta", "em_andamento"],
            ).exists()
        )
        self.assertTrue(
            NotificacaoGestao.objects.filter(
                empresa=self.empresa,
                responsavel=self.empregado,
                titulo="Pedido de férias rejeitado · 20/08/2026",
                estado="aberta",
            ).exists()
        )
