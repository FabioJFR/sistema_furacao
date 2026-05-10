from datetime import date

from django.test import TestCase

from projetos.models import AssiduidadeRegisto, RegistoDiarioEmpregado
from projetos.selectors.assiduidade import (
    construir_contexto_calendario_equipa_empresa,
    construir_contexto_calendario_turnos_empregado,
    listar_assiduidade_empresa_filtro,
)

from .helpers import (
    criar_empresa,
    criar_empregado,
    criar_furo,
    criar_ligacao_empregado_projeto,
    criar_planeamento_turno,
    criar_projeto,
)


class AssiduidadeSelectorsTests(TestCase):
    def setUp(self):
        self.empresa = criar_empresa()
        self.projeto = criar_projeto(empresa=self.empresa, nome="Projeto Alfa")
        self.furo = criar_furo(empresa=self.empresa, projeto=self.projeto, nome="Furo 101")
        self.empregado_1 = criar_empregado(empresa=self.empresa, nome="Operador A")
        self.empregado_2 = criar_empregado(empresa=self.empresa, nome="Operador B")
        criar_ligacao_empregado_projeto(empregado=self.empregado_1, projeto=self.projeto)
        criar_ligacao_empregado_projeto(empregado=self.empregado_2, projeto=self.projeto)

    def test_construir_contexto_calendario_equipa_empresa_agrega_registos_planeamentos_e_ausencias(self):
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_1,
            furo=self.furo,
            nome="Turno A",
            data_inicio=date(2026, 5, 5),
            turno="tarde",
        )
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_2,
            furo=self.furo,
            nome="Turno B",
            data_inicio=date(2026, 5, 6),
            turno="noite",
        )
        RegistoDiarioEmpregado.objects.create(
            empregado=self.empregado_1,
            empresa=self.empresa,
            projeto=self.projeto,
            furo=self.furo,
            data=date(2026, 5, 5),
            turno="Tarde",
            hora_inicio="14:00",
            hora_fim="22:00",
            metros_furados=5.0,
        )
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_2,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 5, 7),
            data_fim=date(2026, 5, 7),
            horas=0.0,
        )

        contexto = construir_contexto_calendario_equipa_empresa(
            self.empresa,
            ano=2026,
            mes=5,
        )

        self.assertEqual(contexto["total_registos"], 1)
        self.assertEqual(contexto["total_turnos"], 2)
        self.assertEqual(contexto["total_ausencias"], 1)

        dia_5 = next(
            dia
            for semana in contexto["semanas"]
            for dia in semana
            if dia["no_mes"] and dia["data"] == date(2026, 5, 5)
        )
        self.assertEqual(dia_5["total_turnos"], 1)
        self.assertEqual(dia_5["entradas"][0]["empregado_nome"], "Operador A")
        self.assertEqual(dia_5["entradas"][0]["origem"], "registo")

        dia_6 = next(
            dia
            for semana in contexto["semanas"]
            for dia in semana
            if dia["no_mes"] and dia["data"] == date(2026, 5, 6)
        )
        self.assertEqual(dia_6["total_turnos"], 1)
        self.assertEqual(dia_6["entradas"][0]["origem"], "planeamento")

        dia_7 = next(
            dia
            for semana in contexto["semanas"]
            for dia in semana
            if dia["no_mes"] and dia["data"] == date(2026, 5, 7)
        )
        self.assertEqual(dia_7["total_ausencias"], 1)
        self.assertEqual(dia_7["ausencias"][0]["tipo_label"], "Férias")

    def test_construir_contexto_calendario_equipa_empresa_filtra_por_empregado(self):
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_1,
            furo=self.furo,
            data_inicio=date(2026, 5, 5),
            turno="manha",
        )
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_2,
            furo=self.furo,
            data_inicio=date(2026, 5, 5),
            turno="tarde",
        )

        contexto = construir_contexto_calendario_equipa_empresa(
            self.empresa,
            ano=2026,
            mes=5,
            empregado_id=str(self.empregado_1.id),
        )

        self.assertEqual(contexto["total_turnos"], 1)
        self.assertEqual(contexto["total_colaboradores"], 1)

    def test_construir_contexto_calendario_equipa_empresa_expande_planeamentos_que_cruzam_mes(self):
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_1,
            furo=self.furo,
            data_inicio=date(2026, 4, 30),
            data_fim=date(2026, 5, 2),
            turno="manha",
        )

        contexto = construir_contexto_calendario_equipa_empresa(
            self.empresa,
            ano=2026,
            mes=5,
        )

        self.assertEqual(contexto["total_turnos"], 2)
        for data_esperada in [date(2026, 5, 1), date(2026, 5, 2)]:
            dia = next(
                dia
                for semana in contexto["semanas"]
                for dia in semana
                if dia["no_mes"] and dia["data"] == data_esperada
            )
            self.assertEqual(dia["total_turnos"], 1)
            self.assertEqual(dia["entradas"][0]["origem"], "planeamento")

    def test_construir_contexto_calendario_equipa_empresa_expande_planeamento_multi_dia_no_mes(self):
        criar_planeamento_turno(
            empresa=self.empresa,
            projeto=self.projeto,
            empregado=self.empregado_1,
            furo=self.furo,
            data_inicio=date(2026, 5, 10),
            data_fim=date(2026, 5, 12),
            turno="manha",
        )

        contexto = construir_contexto_calendario_equipa_empresa(
            self.empresa,
            ano=2026,
            mes=5,
        )

        self.assertEqual(contexto["total_turnos"], 3)
        for data_esperada in [date(2026, 5, 10), date(2026, 5, 11), date(2026, 5, 12)]:
            dia = next(
                dia
                for semana in contexto["semanas"]
                for dia in semana
                if dia["no_mes"] and dia["data"] == data_esperada
            )
            self.assertEqual(dia["total_turnos"], 1)

    def test_calendario_empregado_contabiliza_ferias_que_cruzam_ano(self):
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 12, 30),
            data_fim=date(2027, 1, 3),
            horas=0.0,
        )

        contexto = construir_contexto_calendario_turnos_empregado(self.empregado_1, ano=2027)

        self.assertEqual(contexto["ferias_aprovadas"], 3)
        self.assertEqual(contexto["dias_ferias_gozados"], 3)
        janeiro = contexto["meses"][0]
        dia_2 = next(
            dia
            for semana in janeiro["semanas"]
            for dia in semana
            if dia["no_mes"] and dia["data"] == date(2027, 1, 2)
        )
        self.assertEqual(dia_2["estado_ferias"], "aprovado")

    def test_listar_assiduidade_empresa_filtro_inclui_intervalos_que_cruzam_mes_e_ano(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 12, 30),
            data_fim=date(2027, 1, 3),
            horas=0.0,
        )

        resultados = listar_assiduidade_empresa_filtro(
            self.empresa,
            tipo="ferias",
            mes="1",
            ano="2027",
        )

        self.assertEqual(list(resultados), [pedido])

    def test_listar_assiduidade_empresa_filtro_ignora_periodo_invalido_sem_erro(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 10),
            horas=0.0,
        )
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2025, 8, 10),
            data_fim=date(2025, 8, 10),
            horas=0.0,
        )

        resultados = listar_assiduidade_empresa_filtro(
            self.empresa,
            mes="abc",
            ano="2026",
        )
        resultados_mes_fora_intervalo = listar_assiduidade_empresa_filtro(
            self.empresa,
            mes="13",
            ano="2026",
        )

        self.assertEqual(list(resultados), [pedido])
        self.assertEqual(list(resultados_mes_fora_intervalo), [pedido])

    def test_listar_assiduidade_empresa_filtro_so_mes_usa_sobreposicao_no_ano_atual(self):
        pedido = AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 4, 30),
            data_fim=date(2026, 5, 2),
            horas=0.0,
        )

        resultados = listar_assiduidade_empresa_filtro(
            self.empresa,
            tipo="ferias",
            mes="5",
        )

        self.assertEqual(list(resultados), [pedido])

    def test_dias_ferias_disponiveis_desconta_pedidos_pendentes(self):
        self.empregado_1.dias_ferias_anuais = 5
        self.empregado_1.save()
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="aprovado",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 11),
            horas=0.0,
        )
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 12),
            data_fim=date(2026, 8, 12),
            horas=0.0,
        )

        self.assertEqual(self.empregado_1.dias_ferias_disponiveis(ano=2026), 2)

    def test_calendario_empregado_nao_permite_selecionar_ferias_pendentes(self):
        AssiduidadeRegisto.objects.create(
            empresa=self.empresa,
            empregado=self.empregado_1,
            tipo="ferias",
            estado="pendente",
            data_inicio=date(2026, 8, 10),
            data_fim=date(2026, 8, 10),
            horas=0.0,
        )

        contexto = construir_contexto_calendario_turnos_empregado(self.empregado_1, ano=2026)
        agosto = contexto["meses"][7]
        dia_10 = next(
            dia
            for semana in agosto["semanas"]
            for dia in semana
            if dia["no_mes"] and dia["data"] == date(2026, 8, 10)
        )

        self.assertEqual(dia_10["estado_ferias"], "pendente")
        self.assertFalse(dia_10["selectable"])
