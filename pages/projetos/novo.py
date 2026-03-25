""" from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.persistencia import carregar_projetos  # função para carregar projetos

# pages/projetos/editar.py
def layout(projeto_id):
    projetos = carregar_projetos()
    proj_obj = None

    # Localiza o projeto pelo ID
    for p in projetos:
        if p.id == projeto_id:
            proj_obj = p
            break

    if not proj_obj:
        return html.Div([
            html.H3("Projeto não encontrado"),
            dcc.Link("⬅ Voltar", href="/projetos/listar")
        ])

    # Para simplificar acesso
    p = proj_obj

    return dbc.Container([
        html.H2(f"Editar Projeto: {getattr(p, 'nome', '—')}"),
        html.Hr(),

        dbc.Row([

            # COLUNA ESQUERDA (Dados principais)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Informações Gerais", className="mb-3"),

                        dbc.Label("Nome do Projeto"),
                        dbc.Input(id={"type": "proj-nome", "index": projeto_id}, value=getattr(p, 'nome', '')),

                        dbc.Label("Cliente", className="mt-3"),
                        dbc.Input(id={"type": "proj-cliente", "index": projeto_id}, value=getattr(p, 'cliente', '')),
                    ])
                )
            ], width=6),

            # COLUNA DIREITA (Localização)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([
                        html.H5("Localização", className="mb-3"),

                        dbc.Label("Latitude"),
                        dbc.Input(id={"type": "proj-lat", "index": projeto_id}, type="number",
                                  value=getattr(p, 'latitude', 0)),

                        dbc.Label("Longitude", className="mt-3"),
                        dbc.Input(id={"type": "proj-lon", "index": projeto_id}, type="number",
                                  value=getattr(p, 'longitude', 0)),

                        html.Small("Dica: pode copiar coordenadas do Google Maps", className="text-muted")
                    ])
                )
            ], width=6),
        ]),

        html.Br(),

        # Botões
        dbc.Row([
            dbc.Col(dbc.Button("💾 Salvar", id={"type": "btn-salvar-proj", "index": projeto_id}, color="success"), width="auto"),
            dbc.Col(dbc.Button("🗑 Apagar", id={"type": "btn-apagar-proj", "index": projeto_id}, color="danger"), width="auto"),
            dbc.Col(dbc.Button("✖ Cancelar", id={"type": "btn-cancelar-edicao", "index": projeto_id}, color="secondary"), width="auto")
        ], className="mt-3"),

        # Modal de confirmação de apagamento
        dbc.Modal([
            dbc.ModalHeader("Confirmação de Apagamento"),
            dbc.ModalBody("Tem certeza que deseja apagar este projeto? Esta ação não pode ser desfeita."),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id={"type": "btn-cancelar-apagar", "index": projeto_id}, color="secondary", className="me-2"),
                dbc.Button("Apagar", id={"type": "btn-confirmar-apagar", "index": projeto_id}, color="danger")
            ])
        ], id={"type": "modal-apagar", "index": projeto_id}, is_open=False),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/projetos/listar")

    ], fluid=True) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(prefix="novo"):
    """
    prefix: string para tornar os IDs dinâmicos (ex: 'novo', 'editar')
    """
    return html.Div([

        # 🔹 Título
        html.H2("📁 Novo Projeto", className="mb-4"),

        dbc.Row([

            # 🔸 COLUNA ESQUERDA (Dados principais)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([

                        html.H5("Informações Gerais", className="mb-3"),

                        dbc.Label("Nome do Projeto"),
                        dbc.Input(
                            id={"type": "proj-nome", "index": prefix}, 
                            placeholder="Ex: Furo Mina Aljustrel"
                        ),

                        dbc.Label("Cliente", className="mt-3"),
                        dbc.Input(
                            id={"type": "proj-cliente", "index": prefix}, 
                            placeholder="Ex: Empresa X"
                        ),

                    ])
                )
            ], width=6),

            # 🔸 COLUNA DIREITA (Localização)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([

                        html.H5("Localização", className="mb-3"),

                        dbc.Label("Latitude"),
                        dbc.Input(
                            id={"type": "proj-lat", "index": prefix}, 
                            type="number", 
                            placeholder="Ex: 37.9"
                        ),

                        dbc.Label("Longitude", className="mt-3"),
                        dbc.Input(
                            id={"type": "proj-lon", "index": prefix}, 
                            type="number", 
                            placeholder="Ex: -8.1"
                        ),

                        html.Small(
                            "Dica: pode copiar coordenadas do Google Maps", 
                            className="text-muted"
                        )

                    ])
                )
            ], width=6),

        ]),

        html.Br(),

        # 🔹 Ações
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "💾 Guardar Projeto", 
                    id={"type": "btn-add-projeto", "index": prefix}, 
                    color="success", size="lg"
                ),
                dcc.Link(
                    "⬅ Voltar", 
                    href="/", 
                    className="ms-3", 
                    id={"type": "link-voltar-proj", "index": prefix}
                )
            ])
        ])

    ], style={"maxWidth": "900px"})