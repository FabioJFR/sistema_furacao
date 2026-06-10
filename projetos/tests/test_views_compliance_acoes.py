from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from projetos.models import (
    AcaoCorretiva,
    AcaoPreventiva,
    AuditoriaHSE,
    ChecklistHSE,
    EvidenciaCompliance,
    FechoAcaoCorretiva,
    IncidenteSeguranca,
)

from .helpers import criar_empregado, criar_empresa, criar_perfil, criar_projeto, criar_user


class ComplianceAcoesMultiempresaTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Ações HSE 1")
        self.empresa_externa = criar_empresa(nome="Empresa Ações HSE 2")
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Ação Interno")
        self.projeto_externo = criar_projeto(empresa=self.empresa_externa, nome="Projeto Ação Externo")
        self.responsavel = criar_empregado(empresa=self.empresa, nome="Responsável Ação Interno")
        self.responsavel_externo = criar_empregado(empresa=self.empresa_externa, nome="Responsável Ação Externo")

        self.checklist = ChecklistHSE.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            titulo="Checklist Ação Interna",
        )
        self.checklist_externa = ChecklistHSE.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            titulo="Checklist Ação Externa",
        )
        self.incidente = IncidenteSeguranca.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            reportado_por=self.responsavel,
            responsavel=self.responsavel,
            titulo="Incidente Ação Interno",
        )
        self.incidente_externo = IncidenteSeguranca.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            reportado_por=self.responsavel_externo,
            responsavel=self.responsavel_externo,
            titulo="Incidente Ação Externo",
        )
        self.auditoria = AuditoriaHSE.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            titulo="Auditoria Ação Interna",
        )
        self.auditoria_externa = AuditoriaHSE.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            titulo="Auditoria Ação Externa",
        )
        self.acao = AcaoCorretiva.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            checklist=self.checklist,
            incidente=self.incidente,
            auditoria=self.auditoria,
            titulo="Ação Corretiva Interna",
            prazo=date(2026, 6, 1),
        )
        self.acao_externa = AcaoCorretiva.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            checklist=self.checklist_externa,
            incidente=self.incidente_externo,
            auditoria=self.auditoria_externa,
            titulo="Ação Corretiva Externa",
            prazo=date(2026, 6, 1),
        )
        self.preventiva = AcaoPreventiva.objects.create(
            empresa=self.empresa,
            projeto=self.projeto,
            responsavel=self.responsavel,
            checklist=self.checklist,
            incidente=self.incidente,
            auditoria=self.auditoria,
            titulo="Ação Preventiva Interna",
            prazo=date(2026, 6, 2),
        )
        self.preventiva_externa = AcaoPreventiva.objects.create(
            empresa=self.empresa_externa,
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            checklist=self.checklist_externa,
            incidente=self.incidente_externo,
            auditoria=self.auditoria_externa,
            titulo="Ação Preventiva Externa",
            prazo=date(2026, 6, 2),
        )
        self.evidencia_externa = EvidenciaCompliance.objects.create(
            empresa=self.empresa_externa,
            acao_corretiva=self.acao_externa,
            tipo="documento",
            titulo="Evidência Externa",
            ficheiro=SimpleUploadedFile("externa.txt", b"externa", content_type="text/plain"),
        )
        self.user = criar_user(username="admin_compliance_acoes")
        criar_perfil(user=self.user, tipo_acesso="empresa_admin", empresa=self.empresa)
        self.client.force_login(self.user)

    def _acao_payload(self, *, projeto, responsavel, checklist, incidente, auditoria, titulo="Ação Nova"):
        return {
            "titulo": titulo,
            "descricao": "Descrição teste",
            "projeto": str(projeto.pk),
            "responsavel": str(responsavel.pk),
            "checklist": str(checklist.pk),
            "incidente": str(incidente.pk),
            "auditoria": str(auditoria.pk),
            "prioridade": "alta",
            "status": "aberta",
            "prazo": "2026-06-20",
            "observacoes": "Observação teste",
        }

    def _evidencia_payload(self):
        return {
            "tipo": "documento",
            "titulo": "Evidência Nova",
            "descricao": "Evidência de teste",
            "ficheiro": SimpleUploadedFile("evidencia.txt", b"conteudo", content_type="text/plain"),
        }

    def test_admin_nao_cria_acoes_com_ligacoes_externas(self):
        payload = self._acao_payload(
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            checklist=self.checklist_externa,
            incidente=self.incidente_externo,
            auditoria=self.auditoria_externa,
        )

        cenarios = [
            ("projetos:gestao_acao_corretiva_create", AcaoCorretiva),
            ("projetos:gestao_acao_preventiva_create", AcaoPreventiva),
        ]
        for rota, model in cenarios:
            with self.subTest(rota=rota):
                response = self.client.post(reverse(rota), data=payload)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(model.objects.filter(empresa=self.empresa, titulo="Ação Nova").exists())
                for campo in ["projeto", "responsavel", "checklist", "incidente", "auditoria"]:
                    self.assertIn(campo, response.context["form"].errors)

    def test_admin_nao_atualiza_acoes_com_ligacoes_externas(self):
        payload = self._acao_payload(
            projeto=self.projeto_externo,
            responsavel=self.responsavel_externo,
            checklist=self.checklist_externa,
            incidente=self.incidente_externo,
            auditoria=self.auditoria_externa,
            titulo="Ação Invadida",
        )
        cenarios = [
            ("projetos:gestao_acao_corretiva_update", self.acao),
            ("projetos:gestao_acao_preventiva_update", self.preventiva),
        ]
        for rota, obj in cenarios:
            with self.subTest(rota=rota):
                response = self.client.post(reverse(rota, args=[obj.pk]), data=payload)
                self.assertEqual(response.status_code, 200)
                obj.refresh_from_db()
                self.assertNotEqual(obj.titulo, "Ação Invadida")
                self.assertEqual(obj.projeto_id, self.projeto.pk)
                for campo in ["projeto", "responsavel", "checklist", "incidente", "auditoria"]:
                    self.assertIn(campo, response.context["form"].errors)

    def test_admin_nao_edita_apaga_muda_estado_ou_fecha_acao_corretiva_externa(self):
        urls = [
            reverse("projetos:gestao_acao_corretiva_update", args=[self.acao_externa.pk]),
            reverse("projetos:gestao_acao_corretiva_delete", args=[self.acao_externa.pk]),
            reverse("projetos:gestao_acao_corretiva_estado", args=[self.acao_externa.pk, "em_andamento"]),
            reverse("projetos:gestao_acao_corretiva_fecho", args=[self.acao_externa.pk]),
            reverse("projetos:gestao_acao_corretiva_evidencia_create", args=[self.acao_externa.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, data={"data_fecho": "2026-06-30", "resumo_execucao": "Fecho indevido", "eficaz": "on"})
                self.assertEqual(response.status_code, 302)

        self.acao_externa.refresh_from_db()
        self.assertEqual(self.acao_externa.status, "aberta")
        self.assertFalse(FechoAcaoCorretiva.objects.filter(acao=self.acao_externa).exists())
        self.assertTrue(AcaoCorretiva.objects.filter(pk=self.acao_externa.pk).exists())

    def test_admin_nao_edita_apaga_muda_estado_ou_cria_evidencia_preventiva_externa(self):
        urls = [
            reverse("projetos:gestao_acao_preventiva_update", args=[self.preventiva_externa.pk]),
            reverse("projetos:gestao_acao_preventiva_delete", args=[self.preventiva_externa.pk]),
            reverse("projetos:gestao_acao_preventiva_estado", args=[self.preventiva_externa.pk, "concluida"]),
            reverse("projetos:gestao_acao_preventiva_evidencia_create", args=[self.preventiva_externa.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.post(url, data=self._evidencia_payload())
                self.assertEqual(response.status_code, 302)

        self.preventiva_externa.refresh_from_db()
        self.assertEqual(self.preventiva_externa.status, "aberta")
        self.assertTrue(AcaoPreventiva.objects.filter(pk=self.preventiva_externa.pk).exists())
        self.assertFalse(
            EvidenciaCompliance.objects.filter(acao_preventiva=self.preventiva_externa, titulo="Evidência Nova").exists()
        )

    def test_admin_nao_apaga_evidencia_externa(self):
        response = self.client.post(reverse("projetos:gestao_evidencia_compliance_delete", args=[self.evidencia_externa.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(EvidenciaCompliance.objects.filter(pk=self.evidencia_externa.pk).exists())
