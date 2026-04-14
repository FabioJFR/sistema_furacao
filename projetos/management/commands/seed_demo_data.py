from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
import random

from projetos.models import (
    Projeto,
    Furo,
    Empregados,
    Maquina,
    Material,
    Medicao,
    RegistoDiarioEmpregado,
    LevantamentoMaterial,
    ConfiguracaoPerfuracaoEmpregado,
)


class Command(BaseCommand):
    help = "Cria dados de demonstração completos"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("A criar dados de demonstração..."))

        # Limpeza
        RegistoDiarioEmpregado.objects.all().delete()
        LevantamentoMaterial.objects.all().delete()
        ConfiguracaoPerfuracaoEmpregado.objects.all().delete()
        Medicao.objects.all().delete()
        Material.objects.all().delete()
        Maquina.objects.all().delete()
        Furo.objects.all().delete()
        Projeto.objects.all().delete()
        Empregados.objects.all().delete()

        locais = [
            ("Aljustrel", "Portugal", 37.877, -8.165),
            ("Castro Verde", "Portugal", 37.698, -8.085),
            ("Panasqueira", "Portugal", 40.158, -7.764),
            ("Neves-Corvo", "Portugal", 37.575, -7.971),
            ("Almada de Ouro", "Portugal", 37.560, -7.910),
        ]

        projetos = []
        empregados = []
        maquinas = []
        materiais = []

        # Projetos
        for i in range(1, 6):
            cidade, pais, lat, lon = locais[(i - 1) % len(locais)]
            projeto = Projeto.objects.create(
                nome=f"TesteProjeto{i}",
                cliente=f"Cliente Demo {i}",
                cidade=cidade,
                pais=pais,
                localizacao_lat=lat + random.uniform(-0.01, 0.01),
                localizacao_lon=lon + random.uniform(-0.01, 0.01),
                status="ativo",
                notas=f"Projeto de demonstração em {cidade}.",
            )
            projetos.append(projeto)

        # Empregados
        funcoes = ["Sondador", "Ajudante", "Supervisor"]
        for i in range(1, 10):
            emp = Empregados.objects.create(
                nome=f"Sondador{i}",
                funcao=random.choice(funcoes),
                aprovado=True,
                salario=1200 + i * 50,
            )
            empregados.append(emp)

        # Máquinas
        for i in range(1, 6):
            maq = Maquina.objects.create(
                nome=f"Máquina{i}",
                tipo="Perfuradora",
                marca="Atlas Copco",
                modelo=f"Demo-{i}",
                estado="operacional",
                horimetro=random.uniform(1000, 5000),
            )
            maquinas.append(maq)

        # Associar máquinas a projetos
        for projeto in projetos:
            projeto_maquinas = random.sample(maquinas, k=min(2, len(maquinas)))
            for maq in projeto_maquinas:
                maq.projetos.add(projeto)
                maq.projeto_atual = projeto
                maq.save()

        # Furos + medições + materiais + registos + configs
        for projeto in projetos:
            furos_projeto = []

            for j in range(1, random.randint(4, 7)):
                lat = projeto.localizacao_lat + random.uniform(-0.002, 0.002)
                lon = projeto.localizacao_lon + random.uniform(-0.002, 0.002)

                inclinacao_base = random.choice([-45, -60, -70, -80, -90])
                azimute_base = random.uniform(0, 360)

                furo = Furo.objects.create(
                    nome=f"{projeto.nome}_Furo{j}",
                    projeto=projeto,
                    latitude=lat,
                    longitude=lon,
                    altitude=random.uniform(100, 250),
                    inclinacao=inclinacao_base,
                    azimute=azimute_base,
                    profundidade_inicial=0,
                    profundidade_atual=0,
                    profundidade_final=0,
                    profundidade_alvo=random.choice([120, 150, 180, 200, 250]),
                    origem_este=0,
                    origem_norte=0,
                    origem_tvd=0,
                    estado="ativo",
                )
                furos_projeto.append(furo)

                # Associar empregados
                emp_set = random.sample(empregados, k=min(2, len(empregados)))
                for emp in emp_set:
                    emp.furos.add(furo)

                    # Configuração de perfuração por empregado+furo
                    ConfiguracaoPerfuracaoEmpregado.objects.create(
                        empregado=emp,
                        furo=furo,
                        comprimento_tubo=3.0,
                        comprimento_karoutier=1.5,
                        comprimento_acrescento=0.6,
                        comprimento_calibrador=0.4,
                        comprimento_record=0.5,
                        comprimento_bit=0.2,
                        comprimento_caixa_mola=1.2,
                        comprimento_tubo_interior=3.0,
                        comprimento_cabeca_interior=0.5,
                    )

                # Medições
                profundidade = 0.0
                total_medicoes = random.randint(12, 25)

                for k in range(total_medicoes):
                    incremento = random.uniform(1.5, 3.0)
                    profundidade += incremento

                    Medicao.objects.create(
                        furo=furo,
                        profundidade=round(profundidade, 2),
                        inclinacao=round(inclinacao_base + random.uniform(-3, 3), 2),
                        azimute=round(azimute_base + random.uniform(-8, 8), 2),
                        magnetismo=round(random.uniform(0, 1), 2),
                        altitude=furo.altitude,
                        latitude=lat,
                        longitude=lon,
                        tipo_rocha=random.choice(["xisto", "quartzo", "sulfureto", "gnaisse"]),
                        dureza=round(random.uniform(2, 8), 1),
                    )

                furo.profundidade_atual = profundidade
                furo.profundidade_final = profundidade
                furo.save()

            # Materiais do projeto
            nomes_materiais = ["Tubo NQ", "Bit NQ", "Lama", "Aditivo", "Caixa de mola", "Tubo interior"]
            for nome in nomes_materiais:
                material = Material.objects.create(
                    projeto=projeto,
                    furo=random.choice(furos_projeto),
                    nome=nome,
                    tipo="Consumível",
                    quantidade=random.randint(10, 80),
                    unidade="un",
                    valor=round(random.uniform(20, 400), 2),
                    estado="em_estoque",
                    fornecedor="Fornecedor Demo",
                )
                materiais.append(material)

            # Registos diários + levantamentos
            for emp in random.sample(empregados, k=min(4, len(empregados))):
                if not furos_projeto:
                    continue

                furo = random.choice(furos_projeto)

                for d in range(5):
                    data_reg = timezone.now().date() - timedelta(days=d)

                    horas = round(random.uniform(6, 10), 2)
                    metros = round(random.uniform(3, 18), 2)

                    RegistoDiarioEmpregado.objects.create(
                        empregado=emp,
                        projeto=projeto,
                        furo=furo,
                        data=data_reg,
                        hora_inicio=time(8, 0),
                        hora_inicio_pausa=time(12, 0),
                        hora_fim_pausa=time(13, 0),
                        hora_fim=time(17, 0),
                        horas_trabalhadas=horas,
                        metros_furados=metros,
                        observacoes="Registo gerado automaticamente para demonstração.",
                    )

                    material = random.choice(materiais)
                    LevantamentoMaterial.objects.create(
                        empregado=emp,
                        material=material,
                        projeto=projeto,
                        furo=furo,
                        quantidade=random.randint(1, 5),
                        data=data_reg,
                        observacoes="Levantamento demo",
                    )

        self.stdout.write(self.style.SUCCESS("✔ Dados de demonstração criados com sucesso."))