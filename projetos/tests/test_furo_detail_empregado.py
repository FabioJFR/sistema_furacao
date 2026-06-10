from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    HistoricoConfiguracaoPerfuracao,
    Individual,
    RegistoDiarioEmpregado,
)

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_perfil,
    criar_projeto,
    criar_user,
)


class FuroDetailEmpregadoTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa(nome="Empresa Furo")
        self.user = criar_user(username="empregado_furo_config")
        criar_perfil(user=self.user, tipo_acesso="empregado", empresa=self.empresa)
        self.empregado = criar_empregado(
            empresa=self.empresa,
            user=self.user,
            nome="Operador Furo",
            aprovado=True,
        )
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Config")
        self.furo = criar_furo(
            empresa=self.empresa,
            projeto=self.projeto,
            nome="Furo Configurado",
        )
        RegistoDiarioEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            projeto=self.projeto,
            furo=self.furo,
            data=date(2026, 5, 20),
            metros_furados=1.5,
            horas_trabalhadas=2.0,
        )
        self.client.force_login(self.user)

    def test_detalhe_furo_mostra_configuracao_inicio_do_empregado(self):
        ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            medida_morta=1.75,
            comprimento_tubo=3.0,
            comprimento_karoutier=1.2,
            quantidade_karoutier=2,
            comprimento_acrescento=0.5,
            quantidade_acrescento=1,
            comprimento_calibrador=0.4,
            quantidade_calibrador=1,
            comprimento_record=0.3,
            quantidade_record=1,
            comprimento_bit=0.2,
            comprimento_caixa_mola=0.6,
            comprimento_tubo_interior=1.1,
            quantidade_tubo_interior=2,
            comprimento_acrescento_tubo_interior=0.7,
            quantidade_acrescento_tubo_interior=1,
            comprimento_cabeca_interior=0.8,
        )

        response = self.client.get(
            reverse("projetos:furo_detail_empregado", args=[self.furo.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuração de Inicio de Furo")
        self.assertContains(response, "Conjunto de fundo")
        self.assertContains(response, "3,80 m")
        self.assertContains(response, "4,30 m")
        self.assertContains(response, "Alterar configuração")
        self.assertContains(response, "Medida Morta")
        self.assertContains(response, "maquina_drilling.png")
        self.assertContains(response, "1,75 m")

    def test_configuracao_do_furo_e_partilhada_com_outro_empregado_autorizado(self):
        outro_user = criar_user(username="empregado_furo_config_2")
        criar_perfil(user=outro_user, tipo_acesso="empregado", empresa=self.empresa)
        outro_empregado = criar_empregado(
            empresa=self.empresa,
            user=outro_user,
            nome="Segundo Operador",
            aprovado=True,
        )
        RegistoDiarioEmpregado.objects.create(
            empregado=outro_empregado,
            empresa=self.empresa,
            projeto=self.projeto,
            furo=self.furo,
            data=date(2026, 5, 21),
            metros_furados=2.5,
            horas_trabalhadas=3.0,
        )
        ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=2.0,
            quantidade_karoutier=1,
            comprimento_bit=0.4,
            comprimento_caixa_mola=1.0,
            comprimento_tubo_interior=1.5,
            quantidade_tubo_interior=1,
        )

        self.client.force_login(outro_user)
        response = self.client.get(
            reverse("projetos:furo_detail_empregado", args=[self.furo.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuração de Inicio de Furo")
        self.assertContains(response, "2,40 m")
        self.assertContains(response, "Alterar configuração")

    def test_lista_furos_mostra_configuracao_e_historico_por_furo(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )

        response = self.client.get(reverse("projetos:meus_furos_empregado"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configuração")
        self.assertContains(
            response,
            reverse("projetos:configuracao_perfuracao_update_empregado", args=[configuracao.pk]),
        )
        self.assertContains(response, "Histórico")
        self.assertContains(response, reverse("projetos:historico_furo_list", args=[self.furo.pk]))

    def test_empregado_autorizado_consegue_ver_historico_do_furo(self):
        response = self.client.get(reverse("projetos:historico_furo_list", args=[self.furo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Histórico de Configurações do Furo")
        self.assertContains(response, "Furo Configurado")

    def test_empregado_de_outra_empresa_nao_ve_historico_do_furo(self):
        empresa_externa = criar_empresa(nome="Empresa Externa")
        user_externo = criar_user(username="empregado_empresa_externa")
        criar_perfil(user=user_externo, tipo_acesso="empregado", empresa=empresa_externa)
        criar_empregado(
            empresa=empresa_externa,
            user=user_externo,
            nome="Empregado Externo",
            aprovado=True,
        )

        self.client.force_login(user_externo)
        response = self.client.get(reverse("projetos:historico_furo_list", args=[self.furo.pk]))

        self.assertEqual(response.status_code, 404)

    def test_empregado_de_outra_empresa_nao_edita_configuracao_do_furo(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        empresa_externa = criar_empresa(nome="Empresa Externa Config")
        user_externo = criar_user(username="empregado_empresa_externa_config")
        criar_perfil(user=user_externo, tipo_acesso="empregado", empresa=empresa_externa)
        criar_empregado(
            empresa=empresa_externa,
            user=user_externo,
            nome="Empregado Externo Config",
            aprovado=True,
        )

        self.client.force_login(user_externo)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_update_empregado", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_empregado_de_outra_empresa_nao_apaga_configuracao_do_furo(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        empresa_externa = criar_empresa(nome="Empresa Externa Delete")
        user_externo = criar_user(username="empregado_empresa_externa_delete")
        criar_perfil(user=user_externo, tipo_acesso="empregado", empresa=empresa_externa)
        criar_empregado(
            empresa=empresa_externa,
            user=user_externo,
            nome="Empregado Externo Delete",
            aprovado=True,
        )

        self.client.force_login(user_externo)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_delete_empregado", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_conta_individual_nao_edita_configuracao_de_empresa_por_url_direto(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        user_individual = criar_user(username="individual_config")
        criar_perfil(user=user_individual, tipo_acesso="individual")
        Individual.objects.create(
            user=user_individual,
            nome="Conta Individual Config",
            email=user_individual.email,
            ativo=True,
        )

        self.client.force_login(user_individual)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_update_empregado", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_conta_individual_nao_apaga_configuracao_de_empresa_por_url_direto(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        user_individual = criar_user(username="individual_delete_config")
        criar_perfil(user=user_individual, tipo_acesso="individual")
        Individual.objects.create(
            user=user_individual,
            nome="Conta Individual Delete Config",
            email=user_individual.email,
            ativo=True,
        )

        self.client.force_login(user_individual)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_delete_empregado", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_de_outra_empresa_nao_edita_configuracao_por_url_direto(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        empresa_externa = criar_empresa(nome="Empresa Admin Externa")
        admin_externo = criar_user(username="admin_empresa_externa")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=empresa_externa)

        self.client.force_login(admin_externo)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_update_admin", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_de_outra_empresa_nao_apaga_configuracao_por_url_direto(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        empresa_externa = criar_empresa(nome="Empresa Admin Externa Delete")
        admin_externo = criar_user(username="admin_empresa_externa_delete")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=empresa_externa)

        self.client.force_login(admin_externo)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_delete_admin", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_de_outra_empresa_nao_ve_historico_do_furo(self):
        empresa_externa = criar_empresa(nome="Empresa Admin Externa Hist")
        admin_externo = criar_user(username="admin_empresa_externa_hist")
        criar_perfil(user=admin_externo, tipo_acesso="empresa_admin", empresa=empresa_externa)

        self.client.force_login(admin_externo)
        response = self.client.get(reverse("projetos:historico_furo_list", args=[self.furo.pk]))

        self.assertEqual(response.status_code, 404)

    def test_admin_da_empresa_consegue_editar_configuracao_do_furo(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        admin_user = criar_user(username="admin_empresa_config")
        criar_perfil(user=admin_user, tipo_acesso="empresa_admin", empresa=self.empresa)

        self.client.force_login(admin_user)
        response = self.client.get(
            reverse("projetos:configuracao_perfuracao_update_admin", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar Configuração de Perfuração")
        self.assertContains(response, "Máquina")

    def test_admin_da_empresa_consegue_ver_historico_do_furo(self):
        admin_user = criar_user(username="admin_empresa_hist")
        criar_perfil(user=admin_user, tipo_acesso="empresa_admin", empresa=self.empresa)

        self.client.force_login(admin_user)
        response = self.client.get(reverse("projetos:historico_furo_list", args=[self.furo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Histórico de Configurações do Furo")

    def test_empregado_consegue_apagar_configuracao_e_preservar_historico(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            medida_morta=1.25,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )

        response = self.client.post(
            reverse("projetos:configuracao_perfuracao_delete_empregado", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConfiguracaoPerfuracaoEmpregado.objects.filter(pk=configuracao.pk).exists())
        historico = HistoricoConfiguracaoPerfuracao.objects.filter(furo=self.furo).latest("criado_em")
        self.assertEqual(historico.acao, "apagado")
        self.assertEqual(historico.medida_morta, Decimal("1.25"))

    def test_admin_da_empresa_consegue_apagar_configuracao_e_preservar_historico(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            medida_morta=2.5,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        admin_user = criar_user(username="admin_empresa_delete_config")
        criar_perfil(user=admin_user, tipo_acesso="empresa_admin", empresa=self.empresa)

        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("projetos:configuracao_perfuracao_delete_admin", args=[configuracao.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConfiguracaoPerfuracaoEmpregado.objects.filter(pk=configuracao.pk).exists())
        historico = HistoricoConfiguracaoPerfuracao.objects.filter(furo=self.furo).latest("criado_em")
        self.assertEqual(historico.acao, "apagado")
        self.assertEqual(historico.medida_morta, Decimal("2.50"))

    def test_empregado_consegue_restaurar_historico_com_medida_morta(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            medida_morta=1.10,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        historico = HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="editado",
            utilizador=self.user,
            observacoes="Snapshot para restaurar.",
        )
        configuracao.medida_morta = 4.2
        configuracao.save()

        response = self.client.post(reverse("projetos:historico_restaurar", args=[historico.pk]))

        self.assertEqual(response.status_code, 302)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.medida_morta, 1.1)
        historico_restauro = HistoricoConfiguracaoPerfuracao.objects.filter(configuracao=configuracao).latest("criado_em")
        self.assertEqual(historico_restauro.acao, "editado")
        self.assertEqual(historico_restauro.medida_morta, Decimal("1.10"))

    def test_admin_da_empresa_consegue_restaurar_historico_com_medida_morta(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            medida_morta=2.20,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )
        historico = HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="editado",
            utilizador=self.user,
            observacoes="Snapshot admin para restaurar.",
        )
        configuracao.medida_morta = 5.4
        configuracao.save()
        admin_user = criar_user(username="admin_empresa_restore_config")
        criar_perfil(user=admin_user, tipo_acesso="empresa_admin", empresa=self.empresa)

        self.client.force_login(admin_user)
        response = self.client.post(reverse("projetos:historico_restaurar", args=[historico.pk]))

        self.assertEqual(response.status_code, 302)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.medida_morta, 2.2)
        historico_restauro = HistoricoConfiguracaoPerfuracao.objects.filter(configuracao=configuracao).latest("criado_em")
        self.assertEqual(historico_restauro.acao, "editado")
        self.assertEqual(historico_restauro.medida_morta, Decimal("2.20"))

    def test_empregado_consegue_editar_configuracao_existente_do_furo(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )

        response = self.client.post(
            reverse("projetos:configuracao_perfuracao_update_empregado", args=[configuracao.pk]),
            {
                "comprimento_tubo": "3.00",
                "medida_morta": "2.35",
                "comprimento_karoutier": "2.50",
                "quantidade_karoutier": "1",
                "comprimento_acrescento": "0.00",
                "quantidade_acrescento": "1",
                "comprimento_calibrador": "0.00",
                "quantidade_calibrador": "1",
                "comprimento_record": "0.00",
                "quantidade_record": "1",
                "comprimento_bit": "0.30",
                "comprimento_caixa_mola": "0.00",
                "comprimento_tubo_interior": "0.00",
                "quantidade_tubo_interior": "1",
                "comprimento_acrescento_tubo_interior": "0.00",
                "quantidade_acrescento_tubo_interior": "1",
                "comprimento_cabeca_interior": "0.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.furo_id, self.furo.pk)
        self.assertEqual(configuracao.medida_morta, 2.35)
        self.assertEqual(configuracao.comprimento_karoutier, 2.5)
        historico = HistoricoConfiguracaoPerfuracao.objects.filter(configuracao=configuracao).latest("criado_em")
        self.assertEqual(historico.medida_morta, Decimal("2.35"))

    def test_post_criacao_para_furo_com_configuracao_existente_atualiza_existente(self):
        configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
            empregado=self.empregado,
            empresa=self.empresa,
            furo=self.furo,
            comprimento_karoutier=1.0,
            quantidade_karoutier=1,
        )

        response = self.client.post(
            reverse("projetos:configuracao_perfuracao_create_empregado"),
            {
                "furo": str(self.furo.pk),
                "medida_morta": "1.20",
                "comprimento_tubo": "3.00",
                "comprimento_karoutier": "4.25",
                "quantidade_karoutier": "1",
                "comprimento_acrescento": "0.00",
                "quantidade_acrescento": "1",
                "comprimento_calibrador": "0.00",
                "quantidade_calibrador": "1",
                "comprimento_record": "0.00",
                "quantidade_record": "1",
                "comprimento_bit": "0.30",
                "comprimento_caixa_mola": "0.00",
                "comprimento_tubo_interior": "0.00",
                "quantidade_tubo_interior": "1",
                "comprimento_acrescento_tubo_interior": "0.00",
                "quantidade_acrescento_tubo_interior": "1",
                "comprimento_cabeca_interior": "0.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        configuracao.refresh_from_db()
        self.assertEqual(ConfiguracaoPerfuracaoEmpregado.objects.filter(furo=self.furo).count(), 1)
        self.assertEqual(configuracao.medida_morta, 1.2)
        self.assertEqual(configuracao.comprimento_karoutier, 4.25)
