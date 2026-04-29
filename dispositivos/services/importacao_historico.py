import csv
import io

from dispositivos.models import ImportacaoDispositivoHistorico


def criar_historico_importacao(
    *,
    empresa,
    sessao,
    utilizador,
    nome_ficheiro,
    formato,
    modo_aplicacao,
    total_linhas,
    total_gravadas,
    total_ignoradas,
    furos_criados,
    furos_sem_match,
    resumo_por_furo,
):
    return ImportacaoDispositivoHistorico.objects.create(
        empresa=empresa,
        sessao=sessao,
        utilizador=utilizador,
        nome_ficheiro=nome_ficheiro or "importacao.csv",
        formato=(formato or "").lower(),
        modo_aplicacao=modo_aplicacao or "all_existing",
        total_linhas=total_linhas or 0,
        total_gravadas=total_gravadas or 0,
        total_ignoradas=total_ignoradas or 0,
        furos_criados=furos_criados or 0,
        furos_sem_match=furos_sem_match or [],
        resumo_por_furo=resumo_por_furo or {},
    )


def render_historico_importacao_csv(historico):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "historico_id",
            "data",
            "ficheiro",
            "formato",
            "modo_aplicacao",
            "furo",
            "gravadas",
            "ignoradas",
            "criado_agora",
            "total_linhas",
            "total_gravadas",
            "total_ignoradas",
            "furos_criados",
        ]
    )

    resumo = historico.resumo_por_furo or {}
    if not resumo:
        writer.writerow(
            [
                str(historico.pk),
                historico.criado_em.isoformat(),
                historico.nome_ficheiro,
                historico.formato,
                historico.modo_aplicacao,
                "",
                0,
                0,
                "nao",
                historico.total_linhas,
                historico.total_gravadas,
                historico.total_ignoradas,
                historico.furos_criados,
            ]
        )
    else:
        for nome_furo, dados in resumo.items():
            writer.writerow(
                [
                    str(historico.pk),
                    historico.criado_em.isoformat(),
                    historico.nome_ficheiro,
                    historico.formato,
                    historico.modo_aplicacao,
                    nome_furo,
                    dados.get("gravadas", 0),
                    dados.get("ignoradas", 0),
                    "sim" if dados.get("criado") else "nao",
                    historico.total_linhas,
                    historico.total_gravadas,
                    historico.total_ignoradas,
                    historico.furos_criados,
                ]
            )

    return output.getvalue()
