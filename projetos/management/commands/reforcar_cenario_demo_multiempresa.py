import math
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from plataforma.models import Empresa
from projetos.management.commands.gerar_dados_demo_operacao import Command as BaseDemoCommand
from projetos.models import (
    Despesa,
    Empregados,
    Furo,
    Maquina,
    Material,
    Projeto,
)


class Command(BaseDemoCommand):
    help = (
        "Reforca o cenario demo multiempresa com materiais, alertas de stock baixo, "
        "novos trabalhadores, maquinas e furos de fundo/superficie com inclinacoes negativas."
    )

    inclinacoes_negativas = [-90, -80, -70, -60, -50]

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
            default=18,
            help="Numero base de dias operacionais a gerar por novo furo.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=126,
            help="Seed aleatoria para reproduzir o mesmo cenario.",
        )
        parser.add_argument(
            "--empregados-por-tipo",
            type=int,
            default=2,
            help="Quantos novos trabalhadores criar por tipo: fundo e superficie.",
        )
        parser.add_argument(
            "--maquinas-por-tipo",
            type=int,
            default=1,
            help="Quantas novas maquinas criar por tipo: fundo e superficie.",
        )
        parser.add_argument(
            "--materiais-por-projeto",
            type=int,
            default=4,
            help="Quantos novos materiais criar por projeto.",
        )

    def handle(self, *args, **options):
        self.random = random.Random(options["seed"])
        dias = max(options["dias"], 10)
        empregados_por_tipo = max(options["empregados_por_tipo"], 1)
        maquinas_por_tipo = max(options["maquinas_por_tipo"], 1)
        materiais_por_projeto = max(options["materiais_por_projeto"], 2)

        empresas = Empresa.objects.filter(projetos__isnull=False).distinct().order_by("nome")
        nomes_empresa = options.get("empresas") or []
        if nomes_empresa:
            empresas = empresas.filter(nome__in=nomes_empresa)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("Nenhuma empresa com projetos encontrada para reforcar o cenario demo."))
            return

        self.stdout.write(self.style.WARNING("A reforcar cenario demo multiempresa com stock baixo e furos negativos..."))

        total_empresas = 0
        total_furos = 0
        total_medicoes = 0
        total_registos = 0
        total_alertas = 0
        total_alertas_maquinas = 0
        total_materiais = 0
        total_empregados = 0
        total_maquinas = 0

        for empresa in empresas:
            with transaction.atomic():
                resumo = self._processar_empresa(
                    empresa=empresa,
                    dias=dias,
                    empregados_por_tipo=empregados_por_tipo,
                    maquinas_por_tipo=maquinas_por_tipo,
                    materiais_por_projeto=materiais_por_projeto,
                )
                total_empresas += 1
                total_furos += resumo["furos"]
                total_medicoes += resumo["medicoes"]
                total_registos += resumo["registos"]
                total_alertas += resumo["alertas_stock"]
                total_alertas_maquinas += resumo["alertas_maquinas"]
                total_materiais += resumo["materiais"]
                total_empregados += resumo["empregados"]
                total_maquinas += resumo["maquinas"]

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Empresa {empresa.nome}: "
                        f"{resumo['furos']} furos, {resumo['medicoes']} medicoes, "
                        f"{resumo['registos']} registos, {resumo['materiais']} materiais novos, "
                        f"{resumo['alertas_stock']} alertas de stock baixo e "
                        f"{resumo['alertas_maquinas']} maquinas em alerta."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Reforco concluido em {total_empresas} empresas: "
                f"{total_empregados} trabalhadores, {total_maquinas} maquinas, "
                f"{total_materiais} materiais, {total_furos} furos, "
                f"{total_medicoes} medicoes, {total_registos} registos e "
                f"{total_alertas} materiais em stock baixo e "
                f"{total_alertas_maquinas} maquinas em alerta."
            )
        )

    def _processar_empresa(self, empresa, dias, empregados_por_tipo, maquinas_por_tipo, materiais_por_projeto):
        projetos = list(Projeto.objects.filter(empresa=empresa).order_by("nome"))
        if not projetos:
            return {
                "furos": 0,
                "medicoes": 0,
                "registos": 0,
                "materiais": 0,
                "empregados": 0,
                "maquinas": 0,
                "alertas_stock": 0,
                "alertas_maquinas": 0,
            }

        empregados_criados = self._garantir_empregados_extra(empresa, empregados_por_tipo)
        maquinas_criadas = self._garantir_maquinas_extra(empresa, maquinas_por_tipo)
        materiais_criados = self._garantir_materiais_extra(empresa, projetos, materiais_por_projeto)

        todos_empregados = list(Empregados.objects.filter(empresa=empresa, aprovado=True).order_by("nome"))
        todas_maquinas = list(Maquina.objects.filter(empresa=empresa).order_by("nome"))
        todos_materiais = list(Material.objects.filter(empresa=empresa).order_by("nome"))

        furos_novos = self._criar_furos_negativos(empresa, projetos)
        total_medicoes = 0
        total_registos = 0

        self._alocar_maquinas_novos_furos(projetos, todas_maquinas, furos_novos)

        empregados_fundo = [e for e in todos_empregados if "EmpregadoFundo" in (e.nome or "")]
        empregados_superficie = [e for e in todos_empregados if "EmpregadoSuperficie" in (e.nome or "")]

        for indice_furo, furo in enumerate(furos_novos):
            padrao = self._padrao_furo_negativo(furo, indice_furo)
            colaboradores = self._selecionar_empregados_por_tipo(
                empregados_fundo if furo.tipo == "fundo" else empregados_superficie,
                todos_empregados,
                indice_furo,
            )

            self._ligar_empregados(furo, colaboradores, empresa)
            self._criar_configuracoes(furo, colaboradores, empresa, padrao)
            total_registos += self._criar_registos_diarios(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                dias=max(dias, math.ceil(padrao["profundidade_final"] / 18)),
                total_metros=padrao["profundidade_final"],
                padrao=padrao,
            )
            total_medicoes += self._criar_medicoes(furo=furo, empresa=empresa, padrao=padrao)
            self._criar_movimentos_materiais(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                materiais=todos_materiais,
                padrao=padrao,
            )
            self._criar_despesas(empresa=empresa, furo=furo, maquinas=todas_maquinas, padrao=padrao)

        alertas_stock = self._forcar_stock_baixo(empresa)
        alertas_maquinas = self._forcar_alertas_maquinas(empresa)
        return {
            "furos": len(furos_novos),
            "medicoes": total_medicoes,
            "registos": total_registos,
            "materiais": materiais_criados,
            "empregados": empregados_criados,
            "maquinas": maquinas_criadas,
            "alertas_stock": alertas_stock,
            "alertas_maquinas": alertas_maquinas,
        }

    def _garantir_empregados_extra(self, empresa, empregados_por_tipo):
        criados = 0
        prefixos = [
            ("EmpregadoFundo", "Perfurador1a"),
            ("EmpregadoSuperficie", "Perfurador2a"),
        ]
        for prefixo, funcao in prefixos:
            for _ in range(empregados_por_tipo):
                nome = self._proximo_nome_sequencial(prefixo, empresa.nome)
                Empregados.objects.create(
                    nome=nome,
                    empresa=empresa,
                    funcao=funcao,
                    aprovado=True,
                    data_aprovacao=timezone.now(),
                    email=f"{nome.lower()}@demo.local".replace(" ", ""),
                    telefone=f"9{self.random.randint(10000000, 99999999)}",
                    nacionalidade="Portuguesa",
                    morada=f"Base operacional {empresa.nome}",
                    salario=1450.0 if "Fundo" in prefixo else 1325.0,
                    horas_diarias=8,
                )
                criados += 1
        return criados

    def _garantir_maquinas_extra(self, empresa, maquinas_por_tipo):
        criadas = 0
        for prefixo, tipo in [("MaquinaFundo", "Sonda Fundo"), ("MaquinaSuperficie", "Sonda Superficie")]:
            for _ in range(maquinas_por_tipo):
                nome = self._proximo_nome_sequencial(prefixo, empresa.nome)
                Maquina.objects.create(
                    nome=nome,
                    empresa=empresa,
                    tipo=tipo,
                    marca="Atlas Copco" if "Fundo" in prefixo else "Sandvik",
                    modelo="DEMO-XF" if "Fundo" in prefixo else "DEMO-XS",
                    numero_serie=f"{prefixo[:3].upper()}-{self.random.randint(1000, 9999)}",
                    localizacao_atual=f"Parque {empresa.nome}",
                    estado="operacional",
                    km=18000 + criadas * 2200,
                    horimetro=2300.0 + criadas * 315.5,
                    valor=185000.0 if "Fundo" in prefixo else 132000.0,
                    observacoes="Maquina demo criada para furos negativos e analytics.",
                )
                criadas += 1
        return criadas

    def _garantir_materiais_extra(self, empresa, projetos, materiais_por_projeto):
        catalogo = [
            ("Tubos NQ", "tubos", "un"),
            ("Bits HQ", "bit", "un"),
            ("Polimeros", "consumivel", "kg"),
            ("Caixa Molas", "componente", "un"),
            ("Karoutier", "componente", "un"),
            ("Calibradores", "componente", "un"),
            ("Rolamentos Cabeça", "mecanica", "un"),
            ("Borrachas Expansivas", "mecanica", "un"),
            ("Massa Lubrificante", "mecanica", "kg"),
            ("Cabeca de Injecao", "drilling", "un"),
            ("Bombas de Agua", "mecanica", "un"),
            ("Bicos de Massa", "drilling", "un"),
            ("Tubo Interior NQ", "tubo interior", "un"),
            ("Anel Centralizador NQ", "mecanica", "un"),
        ]
        criados = 0
        for projeto_idx, projeto in enumerate(projetos):
            for indice in range(materiais_por_projeto):
                base_nome, tipo, unidade = catalogo[indice % len(catalogo)]
                nome = f"{base_nome} {empresa.nome} {projeto.nome} {indice + 1}"
                if Material.objects.filter(empresa=empresa, projeto=projeto, nome=nome).exists():
                    continue

                stock_minimo = 8 + (indice % 4) * 4
                quantidade = stock_minimo + 12 + projeto_idx + indice
                if indice % 2 == 0:
                    quantidade = max(stock_minimo - (2 + indice), 0)

                Material.objects.create(
                    empresa=empresa,
                    projeto=projeto,
                    nome=nome,
                    tipo=tipo,
                    marca="DemoSupply",
                    numero_serie=f"MAT-{projeto_idx + 1}-{indice + 1}-{self.random.randint(100, 999)}",
                    stock_minimo=stock_minimo,
                    quantidade=quantidade,
                    unidade=unidade,
                    diametro=76.0 if "Tubos" in base_nome or "Interior" in base_nome else 0.0,
                    valor=round(45 + indice * 18.5 + projeto_idx * 7.5 + (10 if "Lubrificante" in base_nome else 0), 2),
                    fornecedor="Fornecedor Demo",
                    estado="sem_stock" if quantidade <= stock_minimo else "em_estoque",
                    localizacao=f"Armazem {projeto.nome}",
                    observacoes="Material demo criado para reforco multiempresa.",
                )
                criados += 1
        return criados

    def _criar_furos_negativos(self, empresa, projetos):
        furos = []
        for projeto_idx, projeto in enumerate(projetos):
            for tipo in ["fundo", "superficie"]:
                for inclinacao in self.inclinacoes_negativas:
                    nome = self._proximo_nome_furo(empresa, projeto, tipo, inclinacao)
                    furos.append(
                        Furo.objects.create(
                            projeto=projeto,
                            empresa=empresa,
                            nome=nome,
                            profundidade_inicial=0.0,
                            profundidade_alvo_inicial=0.0,
                            profundidade_alvo_atual=0.0,
                            profundidade_atual=0.0,
                            profundidade_maxima_atingida=0.0,
                            inclinacao_planeada_inicial=float(inclinacao),
                            inclinacao_planeada_atual=float(inclinacao),
                            azimute_planeado_inicial=float((145 + projeto_idx * 28 + abs(inclinacao)) % 360),
                            azimute_planeado_atual=float((158 + projeto_idx * 28 + abs(inclinacao)) % 360),
                            latitude=projeto.localizacao_lat,
                            longitude=projeto.localizacao_lon,
                            altitude=0.0,
                            localizacao=f"Setor {tipo.title()} Negativo {abs(inclinacao)}",
                            local_sondagem=f"{'FN' if tipo == 'fundo' else 'SP'}-{abs(inclinacao)}",
                            origem_este=(projeto_idx + 1) * 25.0 + abs(inclinacao) / 2,
                            origem_norte=(projeto_idx + 1) * 19.0 + abs(inclinacao) / 3,
                            origem_tvd=0.0,
                            tipo=tipo,
                            estado="ativo",
                            detalhes=(
                                "Furo demo negativo criado para exercitar 3D, "
                                "analytics, desvios e comparacao entre tipos de furo."
                            ),
                        )
                    )
        return furos

    def _padrao_furo_negativo(self, furo, indice):
        inclinacao_base = float(furo.inclinacao_planeada_inicial or -60.0)
        tipo = furo.tipo or "fundo"
        base_profundidade = 240 if tipo == "fundo" else 130
        profundidade_final = base_profundidade + (abs(int(inclinacao_base)) - 50) * (2.6 if tipo == "fundo" else 1.8)
        profundidade_final += (indice % 3) * (25 if tipo == "fundo" else 14)
        profundidade_final = round(profundidade_final, 2)
        profundidade_alvo_atual = profundidade_final + (18 if tipo == "fundo" else 10)
        azimute_base = float(furo.azimute_planeado_inicial or 180.0)

        if tipo == "fundo":
            trajetoria = ["circular", "desvio", "corretiva", "desvio", "suave"][indice % 5]
        else:
            trajetoria = ["suave", "desvio", "corretiva", "suave", "desvio"][indice % 5]

        furo.profundidade_atual = profundidade_final
        furo.profundidade_maxima_atingida = profundidade_final
        furo.profundidade_alvo_inicial = profundidade_final
        furo.profundidade_alvo_atual = profundidade_alvo_atual
        furo.metros_furados = profundidade_final
        furo.inclinacao_planeada_atual = inclinacao_base
        furo.azimute_planeado_atual = (azimute_base + 12 + indice * 3) % 360
        furo.estado = "ativo"
        furo.save()

        return {
            "profundidade_final": profundidade_final,
            "profundidade_alvo_atual": profundidade_alvo_atual,
            "inclinacao_base": inclinacao_base,
            "azimute_base": azimute_base,
            "trajetoria": trajetoria,
            "indice": indice,
            "tipo_furo": tipo,
        }

    def _selecionar_empregados_por_tipo(self, candidatos_tipo, todos_empregados, indice_furo):
        universo = candidatos_tipo or todos_empregados
        if not universo:
            return []
        total = min(2, len(universo))
        return [universo[(indice_furo + offset) % len(universo)] for offset in range(total)]

    def _alocar_maquinas_novos_furos(self, projetos, maquinas, furos):
        if not maquinas or not furos:
            return

        maquinas_fundo = [m for m in maquinas if "MaquinaFundo" in (m.nome or "")]
        maquinas_superficie = [m for m in maquinas if "MaquinaSuperficie" in (m.nome or "")]

        for indice, projeto in enumerate(projetos):
            maquinas_projeto = [m for m in maquinas if projeto in m.projetos.all()]
            if maquinas_projeto:
                continue

            alvo = maquinas_fundo if indice % 2 == 0 else maquinas_superficie
            if not alvo:
                alvo = maquinas

            maquina = alvo[indice % len(alvo)]
            maquina.projetos.add(projeto)
            if not maquina.projeto_atual_id:
                maquina.projeto_atual = projeto
                maquina.save(update_fields=["projeto_atual"])

        for indice, furo in enumerate(furos):
            pool = maquinas_fundo if furo.tipo == "fundo" and maquinas_fundo else maquinas_superficie
            if not pool:
                pool = maquinas
            maquina = pool[indice % len(pool)]
            maquina.projetos.add(furo.projeto)
            maquina.furos.add(furo)
            maquina.projeto_atual = furo.projeto
            maquina.localizacao_atual = f"{furo.projeto.nome} / {furo.nome}"
            maquina.save(update_fields=["projeto_atual", "localizacao_atual"])

    def _forcar_stock_baixo(self, empresa):
        materiais = list(Material.objects.filter(empresa=empresa).order_by("projeto__nome", "nome"))
        if not materiais:
            return 0

        total_alertas = 0
        for indice, material in enumerate(materiais[: max(4, len(materiais) // 3)]):
            novo_minimo = max(material.stock_minimo, 6 + indice * 2)
            nova_quantidade = max(novo_minimo - (2 + indice), 0)
            material.stock_minimo = novo_minimo
            material.quantidade = nova_quantidade
            material.estado = "sem_stock"
            material.observacoes = "Stock forçado para alerta baixo no cenario demo multiempresa."
            material.save()
            total_alertas += 1
        return total_alertas

    def _forcar_alertas_maquinas(self, empresa):
        maquinas = list(Maquina.objects.filter(empresa=empresa).order_by("nome"))
        if not maquinas:
            return 0

        estados_alerta = ["avariada", "reparacao", "parada"]
        total_alertas = 0
        alvo = max(2, len(maquinas) // 3)
        for indice, maquina in enumerate(maquinas[:alvo]):
            maquina.estado = estados_alerta[indice % len(estados_alerta)]
            maquina.localizacao_atual = f"Oficina / Alerta {empresa.nome}"
            maquina.observacoes = (
                "Maquina colocada em estado de alerta para exercitar dashboard, "
                "cards e graficos operacionais."
            )
            maquina.save(update_fields=["estado", "localizacao_atual", "observacoes"])
            total_alertas += 1
        return total_alertas

    def _proximo_nome_sequencial(self, prefixo, nome_empresa):
        empresa_slug = (nome_empresa or "Empresa").replace(" ", "")
        existentes = []

        if prefixo.startswith("Empregado"):
            nomes = Empregados.objects.filter(nome__startswith=prefixo, empresa__nome=nome_empresa).values_list("nome", flat=True)
        else:
            nomes = Maquina.objects.filter(nome__startswith=prefixo, empresa__nome=nome_empresa).values_list("nome", flat=True)

        for nome in nomes:
            sufixo = nome.replace(prefixo, "").replace(empresa_slug, "")
            try:
                existentes.append(int(sufixo))
            except (TypeError, ValueError):
                continue

        proximo = max(existentes, default=0) + 1
        return f"{prefixo}{proximo}{empresa_slug}"

    def _proximo_nome_furo(self, empresa, projeto, tipo, inclinacao):
        tipo_label = "Fundo" if tipo == "fundo" else "Superficie"
        base = f"Furo{tipo_label}Neg{abs(int(inclinacao))}{projeto.nome.replace(' ', '')}"
        nome = base
        contador = 2
        while Furo.objects.filter(empresa=empresa, projeto=projeto, nome=nome).exists():
            nome = f"{base}_{contador}"
            contador += 1
        return nome

    def _calcular_desvio(self, padrao, progresso, indice):
        inclinacao_base = float(padrao["inclinacao_base"])
        azimute_base = float(padrao["azimute_base"])
        tipo = padrao["trajetoria"]

        if tipo == "circular":
            inclinacao = inclinacao_base + math.sin(progresso * math.pi * 3.2) * 2.2
            azimute = azimute_base + progresso * 540 + math.cos(progresso * math.pi * 4.1) * 20
        elif tipo == "desvio":
            inclinacao = inclinacao_base + math.sin(progresso * math.pi * 1.8) * 4.5 + progresso * 1.8
            azimute = azimute_base + progresso * 85 + (indice % 4) * 5.5
        elif tipo == "corretiva":
            inclinacao = inclinacao_base - math.cos(progresso * math.pi * 2.4) * 3.8 - progresso * 1.2
            azimute = azimute_base + math.sin(progresso * math.pi * 2.2) * 26
        else:
            inclinacao = inclinacao_base + math.sin(progresso * math.pi * 1.2) * 1.8
            azimute = azimute_base + math.cos(progresso * math.pi * 1.7) * 11

        inclinacao = max(-89.9, min(89.9, inclinacao))
        azimute = azimute % 360
        return inclinacao, azimute

    def _criar_despesas(self, empresa, furo, maquinas, padrao):
        maquina = maquinas[padrao["indice"] % len(maquinas)] if maquinas else None
        hoje = timezone.now().date()

        despesas = [
            {
                "categoria": "combustivel",
                "tipo": "combustivel",
                "descricao": f"Consumo gasoleo operacional - {furo.nome}",
                "valor": round(210 + padrao["profundidade_final"] * 0.42, 2),
                "data": hoje - timedelta(days=9),
                "maquina": maquina,
                "projeto": None,
                "furo": None,
            },
            {
                "categoria": "pecas",
                "tipo": "bit NQ",
                "descricao": f"Substituicao bit NQ - {furo.nome}",
                "valor": round(340 + padrao["profundidade_final"] * 0.25, 2),
                "data": hoje - timedelta(days=7),
                "maquina": None,
                "projeto": None,
                "furo": furo,
            },
            {
                "categoria": "pecas",
                "tipo": "karoutier",
                "descricao": f"Reposicao karoutier - {furo.nome}",
                "valor": round(180 + padrao["indice"] * 22, 2),
                "data": hoje - timedelta(days=6),
                "maquina": None,
                "projeto": None,
                "furo": furo,
            },
            {
                "categoria": "pecas",
                "tipo": "tubo interior",
                "descricao": f"Conjunto tubo interior - {furo.nome}",
                "valor": round(255 + padrao["profundidade_final"] * 0.18, 2),
                "data": hoje - timedelta(days=5),
                "maquina": None,
                "projeto": None,
                "furo": furo,
            },
            {
                "categoria": "manutencao",
                "tipo": "manutencao",
                "descricao": f"Manutencao preventiva de sonda - {furo.projeto.nome}",
                "valor": round(520 + padrao["indice"] * 40, 2),
                "data": hoje - timedelta(days=4),
                "maquina": maquina,
                "projeto": None,
                "furo": None,
            },
            {
                "categoria": "outros",
                "tipo": "servicos",
                "descricao": f"Servico mecanico externo - {furo.projeto.nome}",
                "valor": round(290 + padrao["indice"] * 18, 2),
                "data": hoje - timedelta(days=3),
                "maquina": None,
                "projeto": furo.projeto,
                "furo": None,
            },
            {
                "categoria": "outros",
                "tipo": "alojamento",
                "descricao": f"Alojamento equipa de sondagem - {furo.projeto.nome}",
                "valor": round(215 + padrao["indice"] * 12, 2),
                "data": hoje - timedelta(days=2),
                "maquina": None,
                "projeto": furo.projeto,
                "furo": None,
            },
            {
                "categoria": "outros",
                "tipo": "transporte",
                "descricao": f"Transporte tecnico e logistica - {empresa.nome}",
                "valor": round(165 + padrao["indice"] * 10, 2),
                "data": hoje - timedelta(days=2),
                "maquina": None,
                "projeto": None,
                "furo": None,
            },
            {
                "categoria": "outros",
                "tipo": "ferramentas",
                "descricao": f"Ferramentas e consumiveis mecanicos - {furo.nome}",
                "valor": round(145 + padrao["indice"] * 14, 2),
                "data": hoje - timedelta(days=1),
                "maquina": None,
                "projeto": None,
                "furo": furo,
            },
        ]

        for item in despesas:
            maquina_item = item["maquina"]
            projeto_item = item["projeto"]
            furo_item = item["furo"]

            if maquina_item is None and projeto_item is None and furo_item is None:
                if item["tipo"] in {"combustivel", "manutencao", "servicos", "alojamento", "transporte"}:
                    projeto_item = furo.projeto
                else:
                    furo_item = furo

            Despesa.objects.create(
                empresa=empresa,
                categoria=item["categoria"],
                tipo=item["tipo"],
                maquina=maquina_item,
                projeto=projeto_item,
                furo=furo_item,
                descricao=f"[DEMO_MULTI] {item['descricao']}",
                valor=item["valor"],
                data=item["data"],
                observacoes="Despesa criada automaticamente para reforco dos graficos e analytics.",
            )
