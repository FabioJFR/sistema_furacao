import math

from django.core.management.base import BaseCommand
from django.db import transaction

from plataforma.models import Empresa
from projetos.management.commands.gerar_dados_demo_operacao import Command as BaseDemoCommand
from projetos.models import Empregados, Furo, Maquina, Material, Projeto


class Command(BaseDemoCommand):
    help = "Adiciona furos demo com inclinação negativa e gera medições/evolução operacional."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            action="append",
            dest="empresas",
            help="Nome exato da empresa a processar. Pode ser repetido.",
        )
        parser.add_argument(
            "--por-projeto",
            type=int,
            default=2,
            help="Número de novos furos negativos a criar por projeto.",
        )
        parser.add_argument(
            "--dias",
            type=int,
            default=16,
            help="Número base de dias operacionais por novo furo.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=84,
            help="Seed aleatória para reproduzir o mesmo cenário.",
        )

    def handle(self, *args, **options):
        self.random = __import__("random").Random(options["seed"])
        dias = max(options["dias"], 8)
        por_projeto = max(options["por_projeto"], 1)

        empresas = Empresa.objects.filter(projetos__isnull=False).distinct().order_by("nome")
        nomes_empresa = options.get("empresas") or []
        if nomes_empresa:
            empresas = empresas.filter(nome__in=nomes_empresa)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("Nenhuma empresa com projetos encontrada para adicionar furos negativos."))
            return

        self.stdout.write(self.style.WARNING("A adicionar furos demo com inclinação negativa..."))

        total_empresas = 0
        total_furos = 0
        total_medicoes = 0
        total_registos = 0

        for empresa in empresas:
            with transaction.atomic():
                resumo = self._processar_empresa_negativa(empresa=empresa, dias=dias, por_projeto=por_projeto)
                total_empresas += 1
                total_furos += resumo["furos"]
                total_medicoes += resumo["medicoes"]
                total_registos += resumo["registos"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Empresa {empresa.nome}: {resumo['furos']} novos furos negativos, "
                        f"{resumo['medicoes']} medições, {resumo['registos']} registos."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Criados {total_furos} novos furos negativos em {total_empresas} empresas, "
                f"com {total_medicoes} medições e {total_registos} registos."
            )
        )

    def _processar_empresa_negativa(self, empresa, dias, por_projeto):
        projetos = list(Projeto.objects.filter(empresa=empresa).order_by("nome"))
        empregados = list(Empregados.objects.filter(empresa=empresa, aprovado=True).order_by("nome"))
        maquinas = list(Maquina.objects.filter(empresa=empresa).order_by("nome"))
        materiais = list(Material.objects.filter(empresa=empresa).order_by("nome"))

        if not projetos or not empregados:
            return {"furos": 0, "medicoes": 0, "registos": 0}

        created_furos = []
        total_medicoes = 0
        total_registos = 0

        for projeto_idx, projeto in enumerate(projetos):
            for sequencia in range(1, por_projeto + 1):
                indice_global = projeto_idx * por_projeto + (sequencia - 1)
                created_furos.append(self._criar_furo_negativo(projeto, indice_global, sequencia))

        if created_furos and maquinas:
            self._preparar_maquinas(empresa, projetos, created_furos, maquinas)

        deepest_furo_id = self._escolher_furo_circular(created_furos) if created_furos else None

        for indice_furo, furo in enumerate(created_furos):
            padrao = self._padrao_furo_negativo(furo, indice_furo, deepest_furo_id)
            colaboradores = self._selecionar_empregados_para_furo(empregados, indice_furo)

            self._ligar_empregados(furo, colaboradores, empresa)
            self._criar_configuracoes(furo, colaboradores, empresa, padrao)
            total_furo = padrao["profundidade_final"]
            total_registos += self._criar_registos_diarios(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                dias=max(dias, math.ceil(total_furo / 20)),
                total_metros=total_furo,
                padrao=padrao,
            )
            total_medicoes += self._criar_medicoes(furo=furo, empresa=empresa, padrao=padrao)
            self._criar_movimentos_materiais(
                empresa=empresa,
                furo=furo,
                colaboradores=colaboradores,
                materiais=materiais,
                padrao=padrao,
            )
            self._criar_despesas(empresa=empresa, furo=furo, maquinas=maquinas, padrao=padrao)

        return {
            "furos": len(created_furos),
            "medicoes": total_medicoes,
            "registos": total_registos,
        }

    def _criar_furo_negativo(self, projeto, indice_global, sequencia_projeto):
        nome = self._proximo_nome_furo_negativo(projeto, sequencia_projeto)
        lat = projeto.localizacao_lat if projeto.localizacao_lat is not None else None
        lon = projeto.localizacao_lon if projeto.localizacao_lon is not None else None

        return Furo.objects.create(
            projeto=projeto,
            nome=nome,
            profundidade_inicial=0.0,
            profundidade_alvo_inicial=0.0,
            profundidade_alvo_atual=0.0,
            profundidade_atual=0.0,
            profundidade_maxima_atingida=0.0,
            inclinacao_planeada_inicial=-45.0,
            azimute_planeado_inicial=float((160 + indice_global * 33) % 360),
            inclinacao_planeada_atual=-45.0,
            azimute_planeado_atual=float((172 + indice_global * 33) % 360),
            latitude=lat,
            longitude=lon,
            altitude=0.0,
            localizacao=f"Setor Negativo {sequencia_projeto}",
            local_sondagem=f"Rampa {chr(65 + (indice_global % 5))}",
            origem_este=(indice_global + 1) * 16.0,
            origem_norte=(indice_global + 1) * 12.5,
            origem_tvd=0.0,
            tipo="fundo",
            estado="ativo",
            detalhes="Furo demo com inclinação negativa para testes de trajetória e analytics.",
        )

    def _proximo_nome_furo_negativo(self, projeto, sequencia_projeto):
        base = f"FuroNegativo{sequencia_projeto}{projeto.nome.replace(' ', '')}"
        nome = base
        sufixo = 2
        while Furo.objects.filter(projeto=projeto, nome=nome).exists():
            nome = f"{base}_{sufixo}"
            sufixo += 1
        return nome

    def _padrao_furo_negativo(self, furo, indice, deepest_furo_id):
        base_targets = [120, 165, 210, 255, 300, 345]
        profundidade_final = base_targets[indice % len(base_targets)] + (indice // len(base_targets)) * 25
        if furo.id == deepest_furo_id:
            profundidade_final = max(profundidade_final, 420)

        inclinacao_base = [-48, -54, -61, -67, -72, -78][indice % 6]
        azimute_base = (160 + indice * 36) % 360
        profundidade_alvo_atual = profundidade_final + (12 if indice % 2 == 0 else 6)

        furo.profundidade_inicial = 0.0
        furo.profundidade_atual = float(profundidade_final)
        furo.profundidade_maxima_atingida = float(profundidade_final)
        furo.profundidade_alvo_inicial = float(profundidade_final)
        furo.profundidade_alvo_atual = float(profundidade_alvo_atual)
        furo.inclinacao_planeada_inicial = float(inclinacao_base)
        furo.inclinacao_planeada_atual = float(inclinacao_base - (2 if indice % 3 == 0 else 0))
        furo.azimute_planeado_inicial = float(azimute_base)
        furo.azimute_planeado_atual = float((azimute_base + 15) % 360)
        furo.metros_furados = float(profundidade_final)
        furo.estado = "ativo"
        furo.detalhes = (
            "Cenário demo com inclinação negativa, medições regulares e evolução "
            "operacional para testes 3D e analytics."
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
