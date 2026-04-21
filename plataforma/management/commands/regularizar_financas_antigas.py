import calendar

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plataforma.models import (
    Empresa,
    MovimentoFinanceiroPlataforma,
    PagamentoEmpresa,
    SubscricaoEmpresa,
)


def add_months(date_obj, months):
    month = date_obj.month - 1 + months
    year = date_obj.year + month // 12
    month = month % 12 + 1
    day = min(date_obj.day, calendar.monthrange(year, month)[1])
    return date_obj.replace(year=year, month=month, day=day)


def normalizar_periodo(valor):
    try:
        periodo = int(valor or 1)
    except (TypeError, ValueError):
        periodo = 1
    return periodo if periodo in [1, 3, 6, 12] else 1


def calcular_valor(plano, ciclo):
    meses = normalizar_periodo(ciclo)
    if meses == 12 and plano.preco_anual:
        return plano.preco_anual or 0
    return (plano.preco_mensal or 0) * meses


class Command(BaseCommand):
    help = "Regulariza subscrições, pagamentos e movimentos financeiros para empresas antigas."

    @transaction.atomic
    def handle(self, *args, **options):
        empresas = Empresa.objects.select_related("plano").all()

        for empresa in empresas:
            if not empresa.plano:
                self.stdout.write(self.style.WARNING(f"[IGNORADA] {empresa.nome}: sem plano"))
                continue

            subscricao = (
                SubscricaoEmpresa.objects
                .filter(empresa=empresa)
                .order_by("-data_inicio", "-criado_em")
                .first()
            )

            if subscricao:
                ciclo = str(subscricao.ciclo_cobranca or "1")
                data_inicio = subscricao.data_inicio or empresa.data_inicio or timezone.now().date()
            else:
                periodos = empresa.plano.periodos_cobranca_disponiveis_normalizados
                ciclo = str(periodos[0] if periodos else 1)
                data_inicio = empresa.data_inicio or timezone.now().date()

            valor = calcular_valor(empresa.plano, ciclo)
            proxima_renovacao = add_months(data_inicio, normalizar_periodo(ciclo))

            if not subscricao:
                subscricao = SubscricaoEmpresa.objects.create(
                    empresa=empresa,
                    plano=empresa.plano,
                    estado="pendente" if empresa.status == "teste" else "ativa",
                    ciclo_cobranca=ciclo,
                    valor=valor,
                    data_inicio=data_inicio,
                    data_fim=proxima_renovacao,
                    proxima_renovacao=proxima_renovacao,
                    renovacao_definida_manualmente=False,
                    renovacao_automatica=False,
                    observacoes="Subscrição criada em regularização de dados antigos.",
                )
                self.stdout.write(self.style.SUCCESS(f"[CRIADA SUBSCRIÇÃO] {empresa.nome}"))
            else:
                subscricao.plano = empresa.plano
                subscricao.valor = valor
                if not subscricao.proxima_renovacao:
                    subscricao.proxima_renovacao = proxima_renovacao
                if not subscricao.data_fim:
                    subscricao.data_fim = subscricao.proxima_renovacao
                subscricao.save()
                self.stdout.write(self.style.SUCCESS(f"[ATUALIZADA SUBSCRIÇÃO] {empresa.nome}"))

            pagamento = PagamentoEmpresa.objects.filter(
                empresa=empresa,
                subscricao=subscricao,
            ).first()

            if not pagamento:
                PagamentoEmpresa.objects.create(
                    empresa=empresa,
                    subscricao=subscricao,
                    descricao="Regularização inicial de empresas antigas",
                    valor=valor,
                    data_vencimento=data_inicio,
                    estado="pendente",
                    observacoes="Criado automaticamente para alinhar dados financeiros antigos.",
                )
                self.stdout.write(self.style.SUCCESS(f"[CRIADO PAGAMENTO] {empresa.nome}"))

            movimento = MovimentoFinanceiroPlataforma.objects.filter(
                empresa=empresa,
                subscricao=subscricao,
                categoria="subscricao",
            ).first()

            if not movimento:
                MovimentoFinanceiroPlataforma.objects.create(
                    empresa=empresa,
                    plano=empresa.plano,
                    subscricao=subscricao,
                    tipo_movimento="cobranca",
                    natureza_fluxo="entrada",
                    categoria="subscricao",
                    metodo_pagamento="manual",
                    ciclo_cobranca=ciclo,
                    valor=valor,
                    valor_bruto=valor,
                    valor_liquido=valor,
                    descricao="Regularização financeira de empresa antiga",
                    entidade_nome=empresa.nome,
                    data_competencia=data_inicio,
                    data_vencimento=data_inicio,
                    estado="pendente",
                    observacoes="Criado automaticamente para alinhar dados financeiros antigos.",
                )
                self.stdout.write(self.style.SUCCESS(f"[CRIADO MOVIMENTO] {empresa.nome}"))
            else:
                movimento.plano = empresa.plano
                movimento.valor = valor
                movimento.valor_bruto = valor
                movimento.valor_liquido = valor
                movimento.ciclo_cobranca = ciclo
                movimento.entidade_nome = empresa.nome
                movimento.save()
                self.stdout.write(self.style.SUCCESS(f"[ATUALIZADO MOVIMENTO] {empresa.nome}"))

        self.stdout.write(self.style.SUCCESS("Regularização concluída."))
