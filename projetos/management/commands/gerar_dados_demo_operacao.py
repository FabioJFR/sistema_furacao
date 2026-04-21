import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plataforma.models import Empresa
from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    DevolucaoMaterial,
    Despesa,
    EmpregadoFuro,
    EmpregadoProjeto,
    Empregados,
    EventoAnalytics,
    Furo,
    LevantamentoMaterial,
    Maquina,
    Material,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
)


class Command(BaseCommand):
    help = "Gera dados demo operacionais para empresas, projetos e furos já existentes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            action="append",
            dest="empresas",
            help="Nome exato da empresa a processar. Pode ser repetido.",
        )
        parser.add_argument(
            "--dias",
            type=int,
            default=14,
            help="Número base de dias operacionais a gerar por furo.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed aleatória para reproduzir os mesmos dados demo.",
        )

    def handle(self, *args, **options):
        self.random = random.Random(options["seed"])
        dias = max(options["dias"], 8)

        empresas = Empresa.objects.filter(projetos__isnull=False).distinct().order_by("nome")
        nomes_empresa = options.get("empresas") or []
        if nomes_empresa:
            empresas = empresas.filter(nome__in=nomes_empresa)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("Nenhuma empresa com projetos encontrada para gerar dados demo."))
            return

        self.stdout.write(self.style.WARNING("A gerar dados demo operacionais sobre a base atual..."))

        total_empresas = 0
        total_furos = 0
        total_medicoes = 0
        total_registos = 0

        for empresa in empresas:
            with transaction.atomic():
                resumo = self._processar_empresa(empresa, dias=dias)
                total_empresas += 1
                total_furos += resumo["furos"]
                total_medicoes += resumo["medicoes"]
                total_registos += resumo["registos"]

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Empresa {empresa.nome}: {resumo['furos']} furos, "
                        f"{resumo['medicoes']} medições, {resumo['registos']} registos diários."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Dados demo criados para {total_empresas} empresas, "
                f"{total_furos} furos, {total_medicoes} medições e {total_registos} registos."
            )
        )

    def _processar_empresa(self, empresa, dias):
        projetos = list(Projeto.objects.filter(empresa=empresa).order_by("nome"))
        empregados = list(Empregados.objects.filter(empresa=empresa, aprovado=True).order_by("nome"))
        maquinas = list(Maquina.objects.filter(empresa=empresa).order_by("nome"))
        materiais = list(Material.objects.filter(empresa=empresa).order_by("nome"))
        furos = list(Furo.objects.filter(empresa=empresa).select_related("projeto").order_by("projeto__nome", "nome"))

        if not projetos or not empregados or not furos:
            return {"furos": 0, "medicoes": 0, "registos": 0}

        self._limpar_operacao_empresa(empresa)
        self._preparar_maquinas(empresa, projetos, furos, maquinas)

        deepest_furo_id = self._escolher_furo_circular(furos)
        total_medicoes = 0
        total_registos = 0

        for indice_furo, furo in enumerate(furos):
            padrao = self._padrao_furo(furo, indice_furo, deepest_furo_id)
            colaboradores = self._selecionar_empregados_para_furo(empregados, indice_furo)

            self._ligar_empregados(furo, colaboradores, empresa)
            self._criar_configuracoes(furo, colaboradores, empresa, padrao)

            total_furo = padrao["profundidade_final"]
            registos_criados = self._criar_registos_diarios(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                dias=max(dias, math.ceil(total_furo / 22)),
                total_metros=total_furo,
                padrao=padrao,
            )
            total_registos += registos_criados

            medicoes_criadas = self._criar_medicoes(furo=furo, empresa=empresa, padrao=padrao)
            total_medicoes += medicoes_criadas

            self._criar_movimentos_materiais(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                materiais=materiais,
                padrao=padrao,
            )
            self._criar_despesas(empresa=empresa, furo=furo, maquinas=maquinas, padrao=padrao)

        return {"furos": len(furos), "medicoes": total_medicoes, "registos": total_registos}

    def _limpar_operacao_empresa(self, empresa):
        DevolucaoMaterial.objects.filter(empresa=empresa).delete()
        LevantamentoMaterial.objects.filter(empresa=empresa).delete()
        Despesa.objects.filter(empresa=empresa).delete()
        RegistoDiarioEmpregado.objects.filter(empresa=empresa).delete()
        Medicao.objects.filter(empresa=empresa).delete()
        ConfiguracaoPerfuracaoEmpregado.objects.filter(empresa=empresa).delete()
        EmpregadoFuro.objects.filter(empresa=empresa).delete()
        EmpregadoProjeto.objects.filter(empresa=empresa).delete()
        EventoAnalytics.objects.filter(empresa=empresa).delete()

    def _preparar_maquinas(self, empresa, projetos, furos, maquinas):
        furos_por_projeto = {}
        for furo in furos:
            furos_por_projeto.setdefault(furo.projeto_id, []).append(furo)

        for indice, maquina in enumerate(maquinas):
            projeto = projetos[indice % len(projetos)]
            maquina.projetos.set([projeto])
            maquina.projeto_atual = projeto
            maquina.estado = "operacional"
            maquina.km = 14000 + indice * 3700
            maquina.horimetro = round(1850 + indice * 420.5, 1)
            maquina.localizacao_atual = f"Base {empresa.nome} / {projeto.nome}"
            maquina.observacoes = "Preparada para cenário demo operacional."
            maquina.save()

            maquina.furos.set(furos_por_projeto.get(projeto.id, []))

    def _escolher_furo_circular(self, furos):
        for furo in furos:
            if "Empresa2" in (furo.projeto.nome or "") or "Empresa2" in (getattr(furo.projeto, "cliente", "") or ""):
                return furo.id
        return furos[-1].id

    def _padrao_furo(self, furo, indice, deepest_furo_id):
        base_targets = [140, 190, 240, 310, 360, 420]
        profundidade_final = base_targets[indice % len(base_targets)] + (indice // len(base_targets)) * 35

        if furo.id == deepest_furo_id:
            profundidade_final = max(profundidade_final, 540)

        inclinacao_base = [64, 68, 72, 76, 80, 83][indice % 6]
        azimute_base = (38 + indice * 47) % 360

        profundidade_alvo_atual = profundidade_final + (10 if indice % 2 == 0 else 0)

        furo.profundidade_inicial = 0.0
        furo.profundidade_atual = float(profundidade_final)
        furo.profundidade_maxima_atingida = float(profundidade_final)
        furo.profundidade_alvo_inicial = float(profundidade_final)
        furo.profundidade_alvo_atual = float(profundidade_alvo_atual)
        furo.inclinacao_planeada_inicial = float(inclinacao_base)
        furo.inclinacao_planeada_atual = float(inclinacao_base + (2 if indice % 3 == 0 else 0))
        furo.azimute_planeado_inicial = float(azimute_base)
        furo.azimute_planeado_atual = float((azimute_base + 12) % 360)
        furo.origem_este = float(indice * 14.0)
        furo.origem_norte = float(indice * 11.0)
        furo.origem_tvd = 0.0
        furo.localizacao = f"Plataforma {indice + 1}"
        furo.local_sondagem = f"Frente {chr(65 + (indice % 4))}"
        furo.estado = "ativo"
        furo.metros_furados = float(profundidade_final)
        furo.metros_furados_diario = []
        furo.detalhes = (
            "Cenário demo gerado automaticamente com evolução diária, "
            "medições regulares e histórico para analytics."
        )
        furo.save()

        return {
            "profundidade_final": float(profundidade_final),
            "profundidade_alvo_atual": float(profundidade_alvo_atual),
            "inclinacao_base": float(inclinacao_base),
            "azimute_base": float(azimute_base),
            "trajetoria": "circular" if furo.id == deepest_furo_id else ["suave", "desvio", "corretiva"][indice % 3],
            "indice": indice,
        }

    def _selecionar_empregados_para_furo(self, empregados, indice_furo):
        total = min(2, len(empregados))
        selecionados = []
        for offset in range(total):
            selecionados.append(empregados[(indice_furo + offset) % len(empregados)])
        return selecionados

    def _ligar_empregados(self, furo, colaboradores, empresa):
        funcoes = ["sondador_1", "ajudante_sondador"]
        inicio = timezone.now().date() - timedelta(days=21)
        for idx, empregado in enumerate(colaboradores):
            EmpregadoProjeto.objects.get_or_create(
                empregado=empregado,
                projeto=furo.projeto,
                empresa=empresa,
                data_inicio=inicio,
                defaults={"ativo": True},
            )
            EmpregadoFuro.objects.get_or_create(
                empregado=empregado,
                furo=furo,
                empresa=empresa,
                defaults={
                    "funcao": funcoes[idx % len(funcoes)],
                    "data_inicio": inicio,
                    "ativo": True,
                    "observacoes": "Ligação demo operacional.",
                },
            )

    def _criar_configuracoes(self, furo, colaboradores, empresa, padrao):
        for idx, empregado in enumerate(colaboradores):
            ConfiguracaoPerfuracaoEmpregado.objects.create(
                empregado=empregado,
                empresa=empresa,
                furo=furo,
                comprimento_tubo=3.0,
                comprimento_karoutier=1.5,
                quantidade_karoutier=2 if idx == 0 else 1,
                comprimento_acrescento=0.6,
                quantidade_acrescento=3 if padrao["trajetoria"] == "circular" else 2,
                comprimento_calibrador=0.45,
                quantidade_calibrador=2,
                comprimento_record=0.55,
                quantidade_record=2,
                comprimento_bit=0.18,
                comprimento_caixa_mola=1.25,
                comprimento_tubo_interior=3.0,
                quantidade_tubo_interior=6 if padrao["trajetoria"] == "circular" else 4,
                comprimento_acrescento_tubo_interior=0.7,
                quantidade_acrescento_tubo_interior=3 if padrao["trajetoria"] == "circular" else 2,
                comprimento_cabeca_interior=0.45,
            )

    def _criar_registos_diarios(self, empresa, furo, colaboradores, dias, total_metros, padrao):
        inicio = timezone.now().date() - timedelta(days=dias - 1)
        metros_diarios = self._distribuir_total(total_metros, dias, minimo=8.0, maximo=28.0)
        metros_acumulados = 0.0

        historico = []
        for idx, metros in enumerate(metros_diarios):
            empregado = colaboradores[idx % len(colaboradores)]
            data_registo = inicio + timedelta(days=idx)
            antes = round(metros_acumulados, 2)
            metros_acumulados += metros
            depois = round(min(metros_acumulados, total_metros), 2)

            registo = RegistoDiarioEmpregado.objects.create(
                empregado=empregado,
                empresa=empresa,
                projeto=furo.projeto,
                furo=furo,
                data=data_registo,
                hora_inicio=timezone.datetime.strptime("08:00", "%H:%M").time(),
                hora_inicio_pausa=timezone.datetime.strptime("12:00", "%H:%M").time(),
                hora_fim_pausa=timezone.datetime.strptime("13:00", "%H:%M").time(),
                hora_fim=timezone.datetime.strptime("17:00", "%H:%M").time(),
                horas_paragem=0.5 if idx % 5 == 0 else 0.0,
                tipo_paragem="cliente" if idx % 5 == 0 else "",
                metros_furados=round(metros, 2),
                observacoes=(
                    f"[DEMO_OP] Produção do dia no {furo.nome}. "
                    f"Trajetória {padrao['trajetoria']} com avanço controlado."
                ),
                profundidade_furo_antes=antes,
                profundidade_furo_depois=depois,
                profundidade_alvo_inicial_furo=furo.profundidade_alvo_inicial,
                profundidade_alvo_atual_furo=furo.profundidade_alvo_atual,
                inclinacao_planeada_inicial_furo=furo.inclinacao_planeada_inicial,
                inclinacao_planeada_atual_furo=furo.inclinacao_planeada_atual,
                azimute_planeado_inicial_furo=furo.azimute_planeado_inicial,
                azimute_planeado_atual_furo=furo.azimute_planeado_atual,
            )
            historico.append(
                {
                    "data": data_registo.isoformat(),
                    "metros": round(metros, 2),
                    "registo_id": str(registo.pk),
                    "profundidade_final_dia": depois,
                }
            )

        furo.metros_furados_diario = historico
        furo.save(update_fields=["metros_furados_diario"])
        return len(metros_diarios)

    def _criar_medicoes(self, furo, empresa, padrao):
        profundidade_final = int(padrao["profundidade_final"])
        passos = list(range(10, profundidade_final + 1, 10))
        if passos and passos[-1] != profundidade_final:
            passos.append(profundidade_final)
        elif not passos:
            passos = [profundidade_final]

        ultima_inclinacao = padrao["inclinacao_base"]
        ultimo_azimute = padrao["azimute_base"]
        total = len(passos)

        for indice, profundidade in enumerate(passos, start=1):
            progresso = profundidade / max(profundidade_final, 1)
            inclinacao, azimute = self._calcular_desvio(padrao, progresso, indice)
            ultima_inclinacao = inclinacao
            ultimo_azimute = azimute

            Medicao.objects.create(
                empresa=empresa,
                furo=furo,
                profundidade_medida=float(profundidade),
                inclinacao_real_medida=round(inclinacao, 2),
                azimute_real_medido=round(azimute % 360, 2),
                magnetismo=round(1.2 + progresso * 0.9 + (indice % 4) * 0.08, 2),
                altitude=furo.altitude,
                latitude=furo.latitude,
                longitude=furo.longitude,
                tipo_rocha=self._tipo_rocha(indice, padrao["trajetoria"]),
                cor=self._cor_rocha(indice),
                dureza=round(3.4 + (indice % 5) * 0.9 + progresso, 1),
                observacoes=(
                    f"[DEMO_OP] Medição a {profundidade} m com padrão {padrao['trajetoria']}."
                ),
            )

        furo.inclinacao_real_atual = round(ultima_inclinacao, 2)
        furo.azimute_real_atual = round(ultimo_azimute % 360, 2)
        furo.save(update_fields=["inclinacao_real_atual", "azimute_real_atual"])
        return total

    def _criar_movimentos_materiais(self, empresa, furo, colaboradores, materiais, padrao):
        if not materiais:
            return

        materiais_projeto = [m for m in materiais if m.projeto_id == furo.projeto_id]
        alvo_materiais = materiais_projeto[: min(3, len(materiais_projeto))]
        base_data = timezone.now().date() - timedelta(days=10)

        for idx, material in enumerate(alvo_materiais):
            empregado = colaboradores[idx % len(colaboradores)]
            quantidade_levantada = min(max(3 + idx, 1), max(material.quantidade // 6, 1))
            quantidade_devolvida = max(1, quantidade_levantada // 3)

            LevantamentoMaterial.objects.create(
                empregado=empregado,
                material=material,
                empresa=empresa,
                projeto=furo.projeto,
                furo=furo,
                quantidade=quantidade_levantada,
                data=base_data + timedelta(days=idx * 2),
                observacoes=f"[DEMO_OP] Material levantado para operação no {furo.nome}.",
            )

            DevolucaoMaterial.objects.create(
                empregado=empregado,
                material=material,
                empresa=empresa,
                projeto=furo.projeto,
                furo=furo,
                quantidade=quantidade_devolvida,
                data=base_data + timedelta(days=idx * 2 + 1),
                observacoes=f"[DEMO_OP] Devolução parcial após operação no {furo.nome}.",
            )

            material.quantidade = max(material.quantidade - quantidade_levantada + quantidade_devolvida, 1)
            material.estado = "em_estoque" if material.quantidade > material.stock_minimo else "sem_stock"
            material.furo = furo if idx == 0 else material.furo
            material.observacoes = "[DEMO_OP] Stock atualizado com consumo demo."
            material.save()

    def _criar_despesas(self, empresa, furo, maquinas, padrao):
        maquina = maquinas[padrao["indice"] % len(maquinas)] if maquinas else None
        hoje = timezone.now().date()

        despesas = [
            {
                "categoria": "combustivel",
                "tipo": "combustivel",
                "descricao": f"Consumo de combustível - {furo.nome}",
                "valor": round(180 + padrao["profundidade_final"] * 0.35, 2),
                "data": hoje - timedelta(days=6),
                "maquina": maquina,
                "projeto": None,
                "furo": None,
            },
            {
                "categoria": "pecas",
                "tipo": "bit NQ",
                "descricao": f"Substituição de bit - {furo.nome}",
                "valor": round(320 + padrao["profundidade_final"] * 0.22, 2),
                "data": hoje - timedelta(days=4),
                "maquina": None,
                "projeto": None,
                "furo": furo,
            },
            {
                "categoria": "manutencao",
                "tipo": "manutencao",
                "descricao": f"Manutenção preventiva - {furo.projeto.nome}",
                "valor": round(450 + padrao["indice"] * 35, 2),
                "data": hoje - timedelta(days=2),
                "maquina": None,
                "projeto": furo.projeto,
                "furo": None,
            },
            {
                "categoria": "outros",
                "tipo": "geral",
                "descricao": f"Alojamento e apoio logístico - {empresa.nome}",
                "valor": round(260 + padrao["indice"] * 20, 2),
                "data": hoje - timedelta(days=1),
                "maquina": None,
                "projeto": None,
                "furo": None,
            },
        ]

        for item in despesas:
            Despesa.objects.create(
                empresa=empresa,
                categoria=item["categoria"],
                tipo=item["tipo"],
                maquina=item["maquina"],
                projeto=item["projeto"],
                furo=item["furo"],
                descricao=f"[DEMO_OP] {item['descricao']}",
                valor=item["valor"],
                data=item["data"],
                observacoes="Despesa criada automaticamente para cenário demo operacional.",
            )

    def _distribuir_total(self, total, partes, minimo=5.0, maximo=25.0):
        if partes <= 1:
            return [round(total, 2)]

        pesos = [self.random.uniform(0.8, 1.25) for _ in range(partes)]
        soma_pesos = sum(pesos) or 1.0
        bruto = [total * (peso / soma_pesos) for peso in pesos]

        valores = [min(max(valor, minimo), maximo) for valor in bruto]
        ajuste = total - sum(valores)

        idx = 0
        while abs(ajuste) > 0.01 and idx < 1000:
            pos = idx % partes
            margem = maximo - valores[pos] if ajuste > 0 else valores[pos] - minimo
            if margem > 0:
                delta = min(abs(ajuste), margem, 1.5)
                valores[pos] += delta if ajuste > 0 else -delta
                ajuste += -delta if ajuste > 0 else delta
            idx += 1

        valores[-1] += total - sum(valores)
        return [round(max(valor, 0.5), 2) for valor in valores]

    def _calcular_desvio(self, padrao, progresso, indice):
        inclinacao_base = padrao["inclinacao_base"]
        azimute_base = padrao["azimute_base"]
        tipo = padrao["trajetoria"]

        if tipo == "circular":
            inclinacao = inclinacao_base + math.sin(progresso * math.pi * 2.2) * 7.5 + progresso * 4.0
            azimute = azimute_base + progresso * 420 + math.sin(progresso * math.pi * 5) * 18
        elif tipo == "desvio":
            inclinacao = inclinacao_base + progresso * 9 - math.cos(progresso * math.pi * 2) * 2.2
            azimute = azimute_base + progresso * 55 + (indice % 3) * 3.5
        else:
            inclinacao = inclinacao_base + math.sin(progresso * math.pi * 1.6) * 3.0
            azimute = azimute_base + math.sin(progresso * math.pi * 2.8) * 14

        return inclinacao, azimute

    def _tipo_rocha(self, indice, tipo):
        if tipo == "circular":
            opcoes = ["quartzo", "diorito", "gnaisse", "sulfureto"]
        elif tipo == "desvio":
            opcoes = ["xisto", "quartzito", "filito", "gnaisse"]
        else:
            opcoes = ["granito", "xisto", "argilito", "quartzo"]
        return opcoes[indice % len(opcoes)]

    def _cor_rocha(self, indice):
        cores = ["gray", "brown", "darkslategray", "slategray", "darkolivegreen"]
        return cores[indice % len(cores)]
