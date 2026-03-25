""" from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.persistencia import carregar_projetos

# pages/furos/editar.py
def layout(furo_id):
    projetos = carregar_projetos()
    furo_obj = None
    projeto_obj = None

    # 🔹 Localiza o furo pelo ID
    for p in projetos:
        for f in getattr(p, "furos", []):
            if getattr(f, "id", None) == furo_id:
                furo_obj = f
                projeto_obj = p
                break
        if furo_obj:
            break

    if not furo_obj:
        return html.Div([
            html.H3("Furo não encontrado"),
            dcc.Link("⬅ Voltar", href="/furos/listar")
        ])

    # Para simplificar acesso
    f = furo_obj

    return dbc.Container([
        html.H3(f"Editar Furo: {getattr(f, 'nome', '—')} (Projeto: {getattr(projeto_obj, 'nome', '—')})"),
        html.Hr(),

        dbc.Form([
            # Linha 1: Nome e Estado
            dbc.Row([
                dbc.Col([
                    dbc.Label("Nome"),
                    dbc.Input(id={"type": "furo-nome", "index": furo_id}, value=getattr(f, 'nome', ''))
                ]),
                dbc.Col([
                    dbc.Label("Estado"),
                    dbc.Select(
                        id={"type": "furo-estado", "index": furo_id},
                        options=[
                            {"label": "Ativo", "value": "ativo"},
                            {"label": "Parado", "value": "parado"},
                            {"label": "Concluído", "value": "concluido"}
                        ],
                        value=getattr(f, 'estado', 'ativo')
                    )
                ])
            ], className="mb-3"),

            # Linha 2: Profundidade Alvo, Inclinação, Azimute
            dbc.Row([
                dbc.Col([
                    dbc.Label("Profundidade Alvo"),
                    dbc.Input(id={"type": "furo-prof-alvo", "index": furo_id}, type="number",
                              value=getattr(f, 'profundidade_alvo', 0))
                ]),
                dbc.Col([
                    dbc.Label("Inclinação"),
                    dbc.Input(id={"type": "furo-inclinacao", "index": furo_id}, type="number",
                              value=getattr(f, 'inclinacao', 0))
                ]),
                dbc.Col([
                    dbc.Label("Azimute"),
                    dbc.Input(id={"type": "furo-azimute", "index": furo_id}, type="number",
                              value=getattr(f, 'azimute', 0))
                ])
            ], className="mb-3"),

            # Linha 3: Local Sondagem e Tipo
            dbc.Row([
                dbc.Col([
                    dbc.Label("Local de Sondagem"),
                    dbc.Input(id={"type": "furo-local", "index": furo_id}, value=getattr(f, 'local_sondagem', ''))
                ]),
                dbc.Col([
                    dbc.Label("Tipo"),
                    dbc.Input(id={"type": "furo-tipo", "index": furo_id}, value=getattr(f, 'tipo', ''))
                ])
            ], className="mb-3"),

            # Linha 4: Profundidade Atual, Profundidade Final, Detalhes
            dbc.Row([
                dbc.Col([
                    dbc.Label("Profundidade Atual"),
                    dbc.Input(id={"type": "furo-prof-atual", "index": furo_id}, type="number",
                              value=getattr(f, 'profundidade_atual', 0))
                ]),
                dbc.Col([
                    dbc.Label("Profundidade Final"),
                    dbc.Input(id={"type": "furo-prof-final", "index": furo_id}, type="number",
                              value=getattr(f, 'profundidade_final', 0))
                ]),
                dbc.Col([
                    dbc.Label("Detalhes"),
                    dbc.Input(id={"type": "furo-detalhes", "index": furo_id}, value=getattr(f, 'detalhes', ''))
                ])
            ], className="mb-3"),

            # Linha 5: Cliente e Planeamento
            dbc.Row([
                dbc.Col([
                    dbc.Label("Cliente"),
                    dbc.Input(id={"type": "furo-cliente", "index": furo_id}, value=getattr(f, 'cliente', ''))
                ]),
                dbc.Col([
                    dbc.Label("Planeamento"),
                    dbc.Input(id={"type": "furo-planeamento", "index": furo_id}, value=getattr(f, 'planeamento', ''))
                ])
            ], className="mb-3"),

            # Botões
            dbc.Row([
                dbc.Col(dbc.Button("💾 Salvar", id={"type": "btn-salvar-furo", "index": furo_id}, color="success"), width="auto"),
                dbc.Col(dbc.Button("🗑 Apagar", id={"type": "btn-apagar-furo", "index": furo_id}, color="danger"), width="auto"),
                dbc.Col(dbc.Button("✖ Cancelar", id={"type": "btn-cancelar-edicao", "index": furo_id}, color="secondary"), width="auto")
            ], className="mt-3")
        ]),

        # Modal de confirmação de apagamento
        dbc.Modal([
            dbc.ModalHeader("Confirmação de Apagamento"),
            dbc.ModalBody("Tem certeza que deseja apagar este furo? Esta ação não pode ser desfeita."),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id={"type": "btn-cancelar-apagar", "index": furo_id}, color="secondary", className="me-2"),
                dbc.Button("Apagar", id={"type": "btn-confirmar-apagar", "index": furo_id}, color="danger")
            ])
        ], id={"type": "modal-apagar", "index": furo_id}, is_open=False),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/furos/listar")
    ], fluid=True) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(furo_id, prefix="editar-furo"):
    """
    furo_id: ID do furo a editar
    """
    return html.Div([

        html.H3(f"✏️ Editar Furo", className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([

                        dbc.Label("Profundidade (m)"),
                        dbc.Input(
                            id={"type": "med-prof", "index": furo_id}, 
                            type="number"
                        ),

                        dbc.Label("Inclinação (°)", className="mt-3"),
                        dbc.Input(
                            id={"type": "med-inc", "index": furo_id}, 
                            type="number"
                        ),

                        dbc.Label("Azimute (°)", className="mt-3"),
                        dbc.Input(
                            id={"type": "med-azi", "index": furo_id}, 
                            type="number"
                        ),

                        dbc.Label("Magnetismo", className="mt-3"),
                        dbc.Input(
                            id={"type": "med-mag", "index": furo_id}, 
                            type="number"
                        ),

                        html.Br(),
                        dbc.Button(
                            "💾 Adicionar Medição",
                            id={"type": "btn-add-med", "index": furo_id}, 
                            color="primary"
                        )

                    ])
                )
            ])
        ]),

        html.Br(),

        dcc.Link("⬅ Voltar", href="/furos/listar", className="btn btn-secondary")
    ], style={"maxWidth": "900px"})