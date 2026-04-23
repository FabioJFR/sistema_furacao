import math
import random

from django.core.management.base import BaseCommand

from plataforma.models import Empresa
from projetos.models import Furo, Material, Projeto


MATERIAIS_BASE = [
    {
        "nome": "Tubo NQ",
        "tipo": "Drilling",
        "marca": "Boart Longyear",
        "quantidade": 24,
        "stock_minimo": 8,
        "unidade": "un",
        "valor": 185.0,
        "fornecedor": "Fornecedor drilling",
        "localizacao": "Armazem drilling",
    },
    {
        "nome": "Tubo HQ",
        "tipo": "Drilling",
        "marca": "Boart Longyear",
        "quantidade": 18,
        "stock_minimo": 6,
        "unidade": "un",
        "valor": 240.0,
        "fornecedor": "Fornecedor drilling",
        "localizacao": "Armazem drilling",
    },
    {
        "nome": "Bit NQ impregnado",
        "tipo": "Drilling",
        "marca": "Sandvik",
        "quantidade": 12,
        "stock_minimo": 4,
        "unidade": "un",
        "valor": 320.0,
        "fornecedor": "Fornecedor drilling",
        "localizacao": "Armazem drilling",
    },
    {
        "nome": "Bit HQ impregnado",
        "tipo": "Drilling",
        "marca": "Sandvik",
        "quantidade": 10,
        "stock_minimo": 4,
        "unidade": "un",
        "valor": 380.0,
        "fornecedor": "Fornecedor drilling",
        "localizacao": "Armazem drilling",
    },
    {
        "nome": "Lama polimerica",
        "tipo": "Drilling",
        "marca": "AMC",
        "quantidade": 40,
        "stock_minimo": 12,
        "unidade": "saco",
        "valor": 28.0,
        "fornecedor": "Fornecedor drilling",
        "localizacao": "Armazem consumiveis",
    },
    {
        "nome": "Graxa para roscas",
        "tipo": "Mecanica",
        "marca": "Shell",
        "quantidade": 20,
        "stock_minimo": 6,
        "unidade": "un",
        "valor": 12.5,
        "fornecedor": "Fornecedor mecanica",
        "localizacao": "Oficina mecanica",
    },
    {
        "nome": "Oleo hidraulico 46",
        "tipo": "Mecanica",
        "marca": "Galp",
        "quantidade": 16,
        "stock_minimo": 6,
        "unidade": "bidon",
        "valor": 64.0,
        "fornecedor": "Fornecedor mecanica",
        "localizacao": "Oficina mecanica",
    },
    {
        "nome": "Rolamento 6205",
        "tipo": "Mecanica",
        "marca": "SKF",
        "quantidade": 24,
        "stock_minimo": 8,
        "unidade": "un",
        "valor": 9.5,
        "fornecedor": "Fornecedor mecanica",
        "localizacao": "Prateleira pecas",
    },
    {
        "nome": "Correia trapezoidal SPA",
        "tipo": "Mecanica",
        "marca": "Optibelt",
        "quantidade": 12,
        "stock_minimo": 4,
        "unidade": "un",
        "valor": 18.0,
        "fornecedor": "Fornecedor mecanica",
        "localizacao": "Prateleira pecas",
    },
    {
        "nome": "Varão roscado M16",
        "tipo": "Serralharia mecanica",
        "marca": "Generico",
        "quantidade": 30,
        "stock_minimo": 10,
        "unidade": "un",
        "valor": 6.0,
        "fornecedor": "Fornecedor serralharia",
        "localizacao": "Zona serralharia",
    },
    {
        "nome": "Chapa inox 3 mm",
        "tipo": "Serralharia mecanica",
        "marca": "Generico",
        "quantidade": 8,
        "stock_minimo": 3,
        "unidade": "folha",
        "valor": 42.0,
        "fornecedor": "Fornecedor serralharia",
        "localizacao": "Zona serralharia",
    },
    {
        "nome": "Disco de corte 125 mm",
        "tipo": "Serralharia mecanica",
        "marca": "Bosch",
        "quantidade": 60,
        "stock_minimo": 20,
        "unidade": "un",
        "valor": 1.8,
        "fornecedor": "Fornecedor serralharia",
        "localizacao": "Zona serralharia",
    },
    {
        "nome": "Eletrodo 6013",
        "tipo": "Serralharia mecanica",
        "marca": "ESAB",
        "quantidade": 25,
        "stock_minimo": 8,
        "unidade": "kg",
        "valor": 7.5,
        "fornecedor": "Fornecedor soldadura",
        "localizacao": "Zona soldadura",
    },
    {
        "nome": 'Parafuso sextavado M12',
        "tipo": "Mecanica",
        "marca": "Generico",
        "quantidade": 200,
        "stock_minimo": 60,
        "unidade": "un",
        "valor": 0.35,
        "fornecedor": "Fornecedor ferragens",
        "localizacao": "Prateleira ferragens",
    },
    {
        "nome": "Anilha M12",
        "tipo": "Mecanica",
        "marca": "Generico",
        "quantidade": 300,
        "stock_minimo": 100,
        "unidade": "un",
        "valor": 0.08,
        "fornecedor": "Fornecedor ferragens",
        "localizacao": "Prateleira ferragens",
    },
    {
        "nome": "Luvas nitrilo",
        "tipo": "Seguranca",
        "marca": "Generico",
        "quantidade": 40,
        "stock_minimo": 10,
        "unidade": "caixa",
        "valor": 4.5,
        "fornecedor": "Fornecedor EPI",
        "localizacao": "Armazem EPI",
    },
    {
        "nome": "Capacete de seguranca",
        "tipo": "Seguranca",
        "marca": "3M",
        "quantidade": 15,
        "stock_minimo": 5,
        "unidade": "un",
        "valor": 14.0,
        "fornecedor": "Fornecedor EPI",
        "localizacao": "Armazem EPI",
    },
    {
        "nome": "Bloco A4 quadriculado",
        "tipo": "Material de escritorio",
        "marca": "Oxford",
        "quantidade": 30,
        "stock_minimo": 10,
        "unidade": "un",
        "valor": 2.8,
        "fornecedor": "Papelaria local",
        "localizacao": "Escritorio",
    },
    {
        "nome": "Marcador permanente azul",
        "tipo": "Material de escritorio",
        "marca": "Pilot",
        "quantidade": 36,
        "stock_minimo": 12,
        "unidade": "un",
        "valor": 1.2,
        "fornecedor": "Papelaria local",
        "localizacao": "Escritorio",
    },
    {
        "nome": "Resma A4",
        "tipo": "Material de escritorio",
        "marca": "Navigator",
        "quantidade": 25,
        "stock_minimo": 8,
        "unidade": "resma",
        "valor": 5.4,
        "fornecedor": "Papelaria local",
        "localizacao": "Escritorio",
    },
]


def _offset_graus_por_metros(metros_norte, metros_este, latitude_base):
    lat_offset = metros_norte / 111_320.0
    cos_lat = math.cos(math.radians(latitude_base)) or 0.000001
    lon_offset = metros_este / (111_320.0 * cos_lat)
    return lat_offset, lon_offset


def _gerar_coordenadas_proximas(lat_base, lon_base, raio_metros):
    distancia = random.uniform(15, raio_metros)
    angulo = random.uniform(0, 2 * math.pi)
    metros_norte = math.cos(angulo) * distancia
    metros_este = math.sin(angulo) * distancia
    lat_offset, lon_offset = _offset_graus_por_metros(
        metros_norte,
        metros_este,
        lat_base,
    )
    return lat_base + lat_offset, lon_base + lon_offset


class Command(BaseCommand):
    help = (
        "Preenche coordenadas dos furos com base na localização do projeto "
        "e adiciona materiais base úteis por empresa."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            type=str,
            help="Nome exato ou parcial da empresa a processar.",
        )
        parser.add_argument(
            "--raio-metros",
            type=float,
            default=250.0,
            help="Raio máximo em metros para espalhar os furos em torno do projeto.",
        )
        parser.add_argument(
            "--forcar-furos",
            action="store_true",
            help="Reatribui latitude/longitude mesmo a furos que já tenham coordenadas.",
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Mostra o que seria alterado sem guardar dados.",
        )

    def handle(self, *args, **options):
        empresa_filtro = (options.get("empresa") or "").strip()
        raio_metros = max(float(options.get("raio_metros") or 250.0), 30.0)
        forcar_furos = options.get("forcar_furos", False)
        simular = options.get("simular", False)

        empresas = Empresa.objects.all().order_by("nome")
        if empresa_filtro:
            empresas = empresas.filter(nome__icontains=empresa_filtro)

        if not empresas.exists():
            self.stdout.write(
                self.style.ERROR("Nenhuma empresa encontrada para processar.")
            )
            return

        total_furos_atualizados = 0
        total_furos_sem_base = 0
        total_materiais_criados = 0

        for empresa in empresas:
            self.stdout.write(
                self.style.WARNING(f"\nEmpresa: {empresa.nome}")
            )

            projetos = Projeto.objects.filter(empresa=empresa).order_by("nome")
            materiais_criados_empresa = 0
            furos_atualizados_empresa = 0
            furos_sem_base_empresa = 0

            for projeto in projetos:
                if projeto.localizacao_lat is None or projeto.localizacao_lon is None:
                    furos_sem_base = projeto.furos.count()
                    if furos_sem_base:
                        furos_sem_base_empresa += furos_sem_base
                        self.stdout.write(
                            f"  - Projeto '{projeto.nome}' sem coordenadas base: "
                            f"{furos_sem_base} furos ignorados."
                        )
                    continue

                furos = projeto.furos.all().order_by("nome")
                for furo in furos:
                    if (
                        not forcar_furos
                        and furo.latitude is not None
                        and furo.longitude is not None
                    ):
                        continue

                    latitude, longitude = _gerar_coordenadas_proximas(
                        projeto.localizacao_lat,
                        projeto.localizacao_lon,
                        raio_metros,
                    )
                    if not simular:
                        furo.latitude = round(latitude, 7)
                        furo.longitude = round(longitude, 7)
                        if furo.localizacao == "" and projeto.cidade:
                            furo.localizacao = projeto.cidade
                        furo.save(
                            update_fields=["latitude", "longitude", "localizacao", "empresa"]
                        )
                    furos_atualizados_empresa += 1

            for material_base in MATERIAIS_BASE:
                nome_material = material_base["nome"]
                existe = Material.objects.filter(
                    empresa=empresa,
                    nome__iexact=nome_material,
                ).exists()
                if existe:
                    continue

                if not simular:
                    Material.objects.create(
                        empresa=empresa,
                        nome=nome_material,
                        tipo=material_base.get("tipo", ""),
                        marca=material_base.get("marca", ""),
                        quantidade=material_base.get("quantidade", 0),
                        stock_minimo=material_base.get("stock_minimo", 0),
                        unidade=material_base.get("unidade", "un"),
                        valor=material_base.get("valor", 0.0),
                        fornecedor=material_base.get("fornecedor", ""),
                        estado="em_estoque",
                        localizacao=material_base.get("localizacao", ""),
                        observacoes="Material base criado automaticamente para apoio operacional.",
                    )
                materiais_criados_empresa += 1

            total_furos_atualizados += furos_atualizados_empresa
            total_furos_sem_base += furos_sem_base_empresa
            total_materiais_criados += materiais_criados_empresa

            self.stdout.write(
                self.style.SUCCESS(
                    f"  - Furos atualizados: {furos_atualizados_empresa}"
                )
            )
            self.stdout.write(
                f"  - Furos sem projeto com coordenadas base: {furos_sem_base_empresa}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  - Materiais novos criados: {materiais_criados_empresa}"
                )
            )

        if simular:
            self.stdout.write(self.style.WARNING("\nSimulação concluída sem gravar dados."))
        else:
            self.stdout.write(self.style.SUCCESS("\nProcessamento concluído."))
        self.stdout.write(f"Furos atualizados: {total_furos_atualizados}")
        self.stdout.write(
            f"Furos ignorados por falta de coordenadas no projeto: {total_furos_sem_base}"
        )
        self.stdout.write(f"Materiais criados: {total_materiais_criados}")
