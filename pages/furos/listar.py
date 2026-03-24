from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.alertas import analisar_furo

def layout(projetos):
    cards = []

    for p in projetos:
        for f in p.furos:

            # 🔹 Garantir que estado é sempre string
            estado = str(f.estado).lower()

            # 🔹 Última medição segura
            ultima = f.medicoes[-1] if f.medicoes else None

            # 🔹 Alertas automáticos
            alertas = analisar_furo(f)

            # 🔹 Bola indicador
            cor_bola = {
                "ativo": "green",
                "parado": "orange",
                "concluido": "gray"
            }.get(estado, "blue")  # cor padrão
            if alertas:
                cor_bola = "red"  # sobrescreve se houver alertas

            bola = html.Span(
                "●",
                style={"color": cor_bola, "margin-right": "5px", "font-size": "18px"}
            )

            # 🔹 Accordion para dados dentro do card
            accordion = dbc.Accordion([
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Alvo: {f.profundidade_alvo} m"),
                        html.P(f"Inclinação: {f.inclinacao}°"),
                        html.P(f"Azimute: {f.azimute}°"),
                        html.P(f"Local de Sondagem: {f.local_sondagem}"),
                        html.P(f"Tipo: {f.tipo}")
                    ],
                    title="📌 Dados Planejados"
                ),
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Atual: {ultima.profundidade} m" if ultima else "Sem medições"),
                        html.P(f"Inclinação Atual: {ultima.inclinacao}°" if ultima else "—"),
                        html.P(f"Azimute Atual: {ultima.azimute}°" if ultima else "—"),
                        html.P(f"Magnetismo: {ultima.magnetismo}" if ultima else "—"),
                    ],
                    title="⏱️ Última Medição"
                ),
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Atual: {f.profundidade_atual} m"),
                        html.P(f"Nº Medições: {len(f.medicoes)}"),
                        html.P(f"Metros Furados Diário: {sum(f.metros_furados_diario):.2f} m"),
                        html.P(f"Total Metros Furados: {f.metros_furados:.2f} m")
                    ],
                    title="📊 Estado Atual"
                ),
                dbc.AccordionItem(
                    html.Div([
                        dbc.Alert(a, color="danger", className="p-1")
                        for a in alertas
                    ]) if alertas else html.P("Sem alertas"),
                    title="⚠️ Alertas"
                )
            ], always_open=True)

            card = dbc.Card(
                dbc.CardBody([
                    # Nome do furo com indicador
                    html.H5([bola, f"{f.nome} (Projeto: {p.nome})"]),
                    html.Hr(),
                    accordion,
                    html.Hr(),
                    # Botões
                    html.Div([
                        dcc.Link("🔍 Detalhes", href=f"/furo/{f.id}", style={"margin-right": "10px"}),
                        dcc.Link("📍 Ver no Mapa", href=f"/projeto/{p.id}")
                    ])
                ]),
                style={"margin": "5px"}
            )

            cards.append(card)

    if not cards:
        cards.append(html.P("Não existem furos cadastrados."))

    return html.Div([
        html.H3("Painel de Furos"),
        dbc.Row([dbc.Col(card, width=4) for card in cards]),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])