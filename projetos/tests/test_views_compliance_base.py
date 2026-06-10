from datetime import date

from django.test import TestCase
from django.urls import reverse

from projetos.models import AuditoriaHSE, ChecklistHSE, IncidenteSeguranca, PlanoAuditoriaHSE

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_projeto, criar_user


class ComplianceBaseMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Compliance 1")
        self.empresa_externa = criar_empresa(nome="Empresa Compliance 2")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Compliance Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Compliance Externo")
        self.responsavel = criar_empregado(empresa=self.empresa, nome="Responsável HSE Interno")
        self.responsavel_externo = criar_empregado(empresa=self.empresa_externa, nome="Responsável HSE Externo")

        self.checklist = ChecklistHSE.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            titulo="Checklist Interna",
            area="Operação",
            data_check=date(2026, 5, 1),
        )
        self.checklist_externa = ChecklistHSE.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            titulo="Checklist Externa",
            area="Operação",
            data_check=date(2026, 5, 1),
        )
        self.incidente = IncidenteSeguranca.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            reportado_por=self.responsavel,
            responsavel=self.responsavel,
            titulo="Incidente Interno",
            data_incidente=date(2026, 5, 2),
        )
        self.incidente_externo = IncidenteSeguranca.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            reportado_por=self.responsavel_externo,
            responsavel=self.responsavel_externo,
            titulo="Incidente Externo",
            data_incidente=date(2026, 5, 2),
        )
        self.auditoria = AuditoriaHSE.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            titulo="Auditoria Interna",
            data_auditoria=date(2026, 5, 3),
        )
        self.auditoria_externa = AuditoriaHSE.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            titulo="Auditoria Externa",
            data_auditoria=date(2026, 5, 3),
        )
        self.plano = PlanoAuditoriaHSE.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            titulo="Plano Interno",
            proxima_execucao=date(2026, 6, 1),
        )
        self.plano_externo = PlanoAuditoriaHSE.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            titulo="Plano Externo",
            proxima_execucao=date(2026, 6, 1),
        )

        self.user = criar_user(username="admin_compliance")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def _checklist_payload(self, *, projeto, responsavel, titulo="Checklist Nova"):
        return {
            "titulo": titulo,
            "area": "Operação",
            "projeto": str(projeto.pk),
            "responsavel": str(responsavel.pk),
            "data_check": "2026-05-10",
            "status": "pendente",
            "observacoes": "Observação teste",
        }

    def _incidente_payload(self, *, projeto, reportado_por, responsavel, titulo="Incidente Novo"):
        return {
            "titulo": titulo,
            "descricao": "Descrição teste",
            "projeto": str(projeto.pk),
            "reportado_por": str(reportado_por.pk),
            "responsavel": str(responsavel.pk),
            "gravidade": "media",
            "status": "aberto",
            "data_incidente": "2026-05-11",
        }

    def _auditoria_payload(self, *, projeto, responsavel, titulo="Auditoria Nova"):
        return {
            "titulo": titulo,
            "area": "Operação",
            "projeto": str(projeto.pk),
            "responsavel": str(responsavel.pk),
            "data_auditoria": "2026-05-12",
            "status": "planeada",
            "resultado": "observacao",
            "observacoes": "Observação teste",
        }

    def _plano_payload(self, *, projeto, responsavel, titulo="Plano Novo"):
        return {
            "titulo": titulo,
            "area": "Operação",
            "projeto": str(projeto.pk),
            "responsavel": str(responsavel.pk),
            "frequencia": "mensal",
            "ativo": "on",
            "proxima_execucao": "2026-06-15",
            "observacoes": "Observação teste",
        }

    def test_dashboard_compliance_mostra_apenas_dados_da_empresa(self):
        response = self.client.get(reverse("projetos:gestao_compliance_seguranca"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.checklist.titulo)
        self.assertContains(response, self.incidente.titulo)
        self.assertContains(response, self.auditoria.titulo)
        self.assertContains(response, self.plano.titulo)
        self.assertNotContains(response, self.checklist_externa.titulo)
        self.assertNotContains(response, self.incidente_externo.titulo)
        self.assertNotContains(response, self.auditoria_externa.titulo)
        self.assertNotContains(response, self.plano_externo.titulo)

    def test_admin_nao_cria_objetos_base_com_projeto_ou_responsavel_externo(self):
        cenarios = [
            (
                "projetos:gestao_checklist_hse_create",
                self._checklist_payload(projeto=self.projeto_externo, responsavel=self.responsavel_externo),
                ChecklistHSE,
                "Checklist Nova",
                ["projeto", "responsavel"],
            ),
            (
                "projetos:gestao_incidente_create",
                self._incidente_payload(
                    projeto=self.projeto_externo,
                    reportado_por=self.responsavel_externo,
                    responsavel=self.responsavel_externo,
                ),
                IncidenteSeguranca,
                "Incidente Novo",
                ["projeto", "reportado_por", "responsavel"],
            ),
            (
                "projetos:gestao_auditoria_hse_create",
                self._auditoria_payload(projeto=self.projeto_externo, responsavel=self.responsavel_externo),
                AuditoriaHSE,
                "Auditoria Nova",
                ["projeto", "responsavel"],
            ),
            (
                "projetos:gestao_plano_auditoria_hse_create",
                self._plano_payload(projeto=self.projeto_externo, responsavel=self.responsavel_externo),
                PlanoAuditoriaHSE,
                "Plano Novo",
                ["projeto", "responsavel"],
            ),
        ]

        for rota, payload, model, titulo, campos_erro in cenarios:
            with self.subTest(rota=rota):
                response = self.client.post(reverse(rota), data=payload)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(model.objects.filter(empresa=self.empresa, titulo=titulo).exists())
                for campo in campos_erro:
                    self.assertIn(campo, response.context["form"].errors)

    def test_admin_nao_atualiza_objetos_base_com_ligacoes_externas(self):
        cenarios = [
            (
                "projetos:gestao_checklist_hse_update",
                self.checklist,
                self._checklist_payload(
                    projeto=self.projeto_externo,
                    responsavel=self.responsavel_externo,
                    titulo="Checklist Invadida",
                ),
                ["projeto", "responsavel"],
            ),
            (
                "projetos:gestao_incidente_update",
                self.incidente,
                self._incidente_payload(
                    projeto=self.projeto_externo,
                    reportado_por=self.responsavel_externo,
                    responsavel=self.responsavel_externo,
                    titulo="Incidente Invadido",
                ),
                ["projeto", "reportado_por", "responsavel"],
            ),
            (
                "projetos:gestao_auditoria_hse_update",
                self.auditoria,
                self._auditoria_payload(
                    projeto=self.projeto_externo,
                    responsavel=self.responsavel_externo,
                    titulo="Auditoria Invadida",
                ),
                ["projeto", "responsavel"],
            ),
            (
                "projetos:gestao_plano_auditoria_hse_update",
                self.plano,
                self._plano_payload(
                    projeto=self.projeto_externo,
                    responsavel=self.responsavel_externo,
                    titulo="Plano Invadido",
                ),
                ["projeto", "responsavel"],
            ),
        ]

        for rota, obj, payload, campos_erro in cenarios:
            with self.subTest(rota=rota):
                titulo_original = obj.titulo
                response = self.client.post(reverse(rota, args=[obj.pk]), data=payload)
                self.assertEqual(response.status_code, 200)
                obj.refresh_from_db()
                self.assertEqual(obj.titulo, titulo_original)
                self.assertEqual(obj.projeto_id, self.projeto.pk)
                for campo in campos_erro:
                    self.assertIn(campo, response.context["form"].errors)

    def test_admin_nao_edita_ou_apaga_objetos_base_externos(self):
        cenarios = [
            (
                self.checklist_externa,
                [
                    reverse("projetos:gestao_checklist_hse_update", args=[self.checklist_externa.pk]),
                    reverse("projetos:gestao_checklist_hse_delete", args=[self.checklist_externa.pk]),
                    reverse("projetos:gestao_checklist_hse_evidencia_create", args=[self.checklist_externa.pk]),
                ],
            ),
            (
                self.incidente_externo,
                [
                    reverse("projetos:gestao_incidente_update", args=[self.incidente_externo.pk]),
                    reverse("projetos:gestao_incidente_delete", args=[self.incidente_externo.pk]),
                    reverse("projetos:gestao_incidente_estado", args=[self.incidente_externo.pk, "fechado"]),
                    reverse("projetos:gestao_incidente_evidencia_create", args=[self.incidente_externo.pk]),
                ],
            ),
            (
                self.auditoria_externa,
                [
                    reverse("projetos:gestao_auditoria_hse_update", args=[self.auditoria_externa.pk]),
                    reverse("projetos:gestao_auditoria_hse_delete", args=[self.auditoria_externa.pk]),
                    reverse("projetos:gestao_auditoria_hse_evidencia_create", args=[self.auditoria_externa.pk]),
                ],
            ),
            (
                self.plano_externo,
                [
                    reverse("projetos:gestao_plano_auditoria_hse_update", args=[self.plano_externo.pk]),
                    reverse("projetos:gestao_plano_auditoria_hse_delete", args=[self.plano_externo.pk]),
                ],
            ),
        ]

        for obj, urls in cenarios:
            for url in urls:
                with self.subTest(url=url):
                    response = self.client.post(url)
                    self.assertEqual(response.status_code, 302)
            obj.refresh_from_db()
            self.assertTrue(obj.__class__.objects.filter(pk=obj.pk).exists())
