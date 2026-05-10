from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.text import slugify


def _artigo_ajuda(*, titulo, categoria, resumo, passos, palavras_chave="", rota=None, acao_label="Abrir"):
    return {
        "id": slugify(f"{categoria}-{titulo}"),
        "titulo": titulo,
        "categoria": categoria,
        "resumo": resumo,
        "passos": passos,
        "palavras_chave": palavras_chave,
        "rota": rota,
        "acao_label": acao_label,
    }


def _ajuda_por_perfil():
    return [
        {
            "chave": "empresa",
            "titulo": "Empresas",
            "descricao": "Tutoriais para administração, operação, gestão transversal e leitura executiva da plataforma.",
            "artigos": [
                _artigo_ajuda(
                    titulo="Centro de Gestão",
                    categoria="Gestão",
                    resumo="Usa o hub de Gestão para entrar nas áreas de clientes, planeamento, RH, compras, compliance, notificações e relatórios executivos.",
                    passos=[
                        "Abre o menu Gestão e entra em Centro de Gestão.",
                        "Lê os cartões principais para perceber pendências e módulos com mais atividade.",
                        "Entra na área certa conforme o tipo de decisão que precisas de tomar.",
                    ],
                    palavras_chave="gestão hub centro painel administração empresa",
                    rota="projetos:gestao_hub",
                ),
                _artigo_ajuda(
                    titulo="Clientes & Contratos",
                    categoria="Gestão",
                    resumo="Regista contratos, adendas, anexos, workflows comerciais, alertas de renovação e fichas comerciais por cliente.",
                    passos=[
                        "Cria ou abre um contrato para o cliente certo.",
                        "Preenche datas, workflow comercial, contactos e valor estimado.",
                        "Usa adendas, anexos e alertas para acompanhar renovação e histórico.",
                    ],
                    palavras_chave="clientes contratos renovação adendas anexos workflow comercial cliente",
                    rota="projetos:cliente_contrato_list",
                ),
                _artigo_ajuda(
                    titulo="Planeamento",
                    categoria="Gestão",
                    resumo="Planeia turnos por dia, empregado, máquina e furo, com conflitos, calendário semanal/mensal e horários por máquina.",
                    passos=[
                        "Abre Planeamento e cria o turno com projeto, furo, máquina e empregado.",
                        "Se a máquina tiver horário oficial, o sistema aplica esse turno automaticamente.",
                        "Consulta o calendário para ver conflitos, cobertura e turnos confirmados.",
                    ],
                    palavras_chave="planeamento turnos calendário máquina conflitos horários",
                    rota="projetos:planeamento_turno_list",
                ),
                _artigo_ajuda(
                    titulo="RH & Assiduidade",
                    categoria="Gestão",
                    resumo="Controla presença, férias, faltas, baixas, horas extra, saldos e agora também o calendário operacional da equipa.",
                    passos=[
                        "Filtra por mês, ano, empregado, tipo e estado para encontrar o que precisas.",
                        "Usa o calendário operacional para ver quem trabalhou em cada dia e em que turno.",
                        "Aprova ou rejeita férias e consulta o saldo mensal por colaborador.",
                    ],
                    palavras_chave="rh assiduidade férias faltas baixas horas extra calendário equipa",
                    rota="projetos:assiduidade_list",
                ),
                _artigo_ajuda(
                    titulo="Compras & Fornecedores",
                    categoria="Gestão",
                    resumo="Controla pedidos de compra, fornecedores, propostas, comparações de prazo/preço e decisões de aquisição.",
                    passos=[
                        "Cria o pedido de compra com descrição, prioridade e data de necessidade.",
                        "Adiciona fornecedores e propostas recebidas.",
                        "Usa a comparação automática para escolher a melhor proposta e fechar a decisão.",
                    ],
                    palavras_chave="compras fornecedores propostas pedido compra comparação aprovação",
                    rota="projetos:gestao_compras_fornecedores",
                ),
                _artigo_ajuda(
                    titulo="Compliance & Segurança",
                    categoria="Gestão",
                    resumo="Regista checklists, incidentes, auditorias, ações corretivas/preventivas, evidências e leitura de risco operacional.",
                    passos=[
                        "Cria a base operacional com checklists, auditorias e incidentes.",
                        "Abre ações com responsável, prioridade e prazo.",
                        "Consulta o dashboard para taxa de fecho, SLA, alertas e risco por responsável/projeto.",
                    ],
                    palavras_chave="compliance segurança auditorias incidentes ações corretivas preventivas risco",
                    rota="projetos:gestao_compliance_seguranca",
                ),
                _artigo_ajuda(
                    titulo="Centro de Notificações",
                    categoria="Gestão",
                    resumo="Acompanha pendências operacionais, prioridades, SLA e encaminhamento de ações críticas da empresa.",
                    passos=[
                        "Entra no Centro de Notificações para ver a fila operacional.",
                        "Filtra por estado e prioridade.",
                        "Atualiza responsáveis e estado para manter o fluxo de resolução controlado.",
                    ],
                    palavras_chave="notificações sla pendências prioridades alertas empresa",
                    rota="projetos:gestao_notificacoes",
                ),
                _artigo_ajuda(
                    titulo="Relatórios Executivos",
                    categoria="Gestão",
                    resumo="Lê KPIs globais, exporta CSV/XLSX/PDF e envia relatórios por email com ou sem agendamento automático.",
                    passos=[
                        "Define o período e gera o resumo financeiro, RH e compliance.",
                        "Exporta para CSV, XLSX ou PDF executivo.",
                        "Usa envio manual ou agendamento para distribuição automática.",
                    ],
                    palavras_chave="relatórios executivos pdf csv xlsx email agendamento kpi",
                    rota="projetos:gestao_relatorios_executivos",
                ),
                _artigo_ajuda(
                    titulo="Projetos, Furos e Medições",
                    categoria="Operação",
                    resumo="A área operacional da empresa centraliza projetos, furos, medições e toda a evolução técnica da obra.",
                    passos=[
                        "Cria o projeto e associa logo os furos previstos.",
                        "Mantém cada furo com profundidade, orientação e estado corretos.",
                        "Consulta medições e detalhe técnico para acompanhar a execução.",
                    ],
                    palavras_chave="projetos furos medições operação obra produção",
                    rota="projetos:projeto_list",
                ),
                _artigo_ajuda(
                    titulo="Empregados e Máquinas",
                    categoria="Operação",
                    resumo="Gere trabalhadores, documentos, turnos, máquinas e avarias na mesma plataforma.",
                    passos=[
                        "Cria ou edita o trabalhador com empresa, função e dias de férias anuais.",
                        "Configura turnos por máquina quando o horário oficial depende do equipamento.",
                        "Usa o histórico e as avarias para manter operação e manutenção alinhadas.",
                    ],
                    palavras_chave="empregados máquinas avarias documentos funções férias",
                    rota="projetos:empregado_list",
                ),
                _artigo_ajuda(
                    titulo="Materiais e Stock",
                    categoria="Operação",
                    resumo="Controla materiais, entradas, saídas, levantamentos e devoluções, mantendo rastreabilidade do stock da operação.",
                    passos=[
                        "Abre Materiais para consultar o stock atual da empresa.",
                        "Usa entradas e saídas para corrigir ou atualizar movimentos internos.",
                        "Consulta levantamentos e devoluções para manter rastreio por utilizador e contexto operacional.",
                    ],
                    palavras_chave="materiais stock entradas saídas levantamentos devoluções armazém",
                    rota="projetos:material_list",
                ),
                _artigo_ajuda(
                    titulo="Registos de Produção e Fichas Técnicas",
                    categoria="Registos",
                    resumo="Consulta, valida e exporta os registos operacionais e técnicos produzidos pela equipa.",
                    passos=[
                        "Abre Registos de Produção para ver todos os registos lançados.",
                        "Usa as Fichas Técnicas para detalhe técnico, furadas, equipa e ocorrências.",
                        "Exporta apenas a partir da área da empresa quando precisares de documentação formal.",
                    ],
                    palavras_chave="registos produção fichas técnicas exportação turno",
                    rota="projetos:registos_admin_list",
                ),
                _artigo_ajuda(
                    titulo="Finanças",
                    categoria="Finanças",
                    resumo="Acompanha despesas, definições financeiras e leitura de custos dentro da operação.",
                    passos=[
                        "Consulta a lista de despesas e mantém as categorias corretas.",
                        "Usa definições financeiras para parâmetros globais da empresa.",
                        "Cruza depois com Analytics e Relatórios Executivos para visão consolidada.",
                    ],
                    palavras_chave="finanças despesas custos definições financeiras",
                    rota="projetos:despesa_list_admin",
                ),
                _artigo_ajuda(
                    titulo="Analytics, AI e 3D",
                    categoria="Análise",
                    resumo="Explora dashboards, análises AI, modelos 3D e painéis avançados de leitura técnica.",
                    passos=[
                        "Usa Analytics para perceber produtividade, rentabilidade e alertas.",
                        "Usa AI para análise visual, biblioteca PDF e memória operacional.",
                        "Usa 3D para trajetória, wireframe, block model e implicit model quando aplicável.",
                    ],
                    palavras_chave="analytics ai 3d wireframe block model implicit gráficos",
                    rota="projetos:graficos_operacionais_dashboard",
                ),
                _artigo_ajuda(
                    titulo="Procurar",
                    categoria="Utilitários",
                    resumo="Usa a procura global para encontrar rapidamente projetos, furos, empregados, máquinas e outros registos da empresa.",
                    passos=[
                        "Abre Procurar no menu do utilizador da empresa.",
                        "Escreve um nome, código, referência ou parte do texto que procuras.",
                        "Abre o resultado certo para saltar diretamente para o detalhe da entidade.",
                    ],
                    palavras_chave="procurar pesquisa global localizar entidade projeto furo empregado máquina",
                    rota="projetos:procurar_dashboard",
                ),
                _artigo_ajuda(
                    titulo="Relatórios e Exportação",
                    categoria="Utilitários",
                    resumo="Centraliza exportações operacionais e ficheiros de apoio, além dos relatórios executivos e técnicos já existentes nos módulos próprios.",
                    passos=[
                        "Abre Relatórios a partir do menu do utilizador.",
                        "Escolhe o tipo de documento ou exportação que precisas.",
                        "Confirma filtros e descarrega apenas a informação necessária para o contexto.",
                    ],
                    palavras_chave="relatórios exportação documentos descarregar ficheiros empresa",
                    rota="projetos:relatorios_exportacao",
                ),
                _artigo_ajuda(
                    titulo="Definições da Empresa",
                    categoria="Configuração",
                    resumo="Ajusta preferências da conta, parâmetros globais e regras de funcionamento que influenciam vários módulos.",
                    passos=[
                        "Abre Definições no menu do utilizador.",
                        "Revê preferências, parâmetros e campos configuráveis por empresa.",
                        "Guarda apenas depois de confirmar o impacto da alteração nos fluxos operacionais.",
                    ],
                    palavras_chave="definições empresa preferências parâmetros configuração",
                    rota="projetos:definicoes_admin",
                ),
                _artigo_ajuda(
                    titulo="Sugestões e Melhoria Contínua",
                    categoria="Colaboração",
                    resumo="Usa esta área para enviar melhorias, ideias e observações sobre a plataforma, mantendo um canal de evolução contínua.",
                    passos=[
                        "Abre Sugestões no menu do utilizador.",
                        "Descreve o problema, melhoria ou ideia com contexto real de utilização.",
                        "Submete a sugestão para ficar registada e poder ser avaliada nas próximas fases.",
                    ],
                    palavras_chave="sugestões feedback melhoria plataforma ideias empresa",
                    rota="projetos:sugestoes_plataforma",
                ),
                _artigo_ajuda(
                    titulo="3D Avançado",
                    categoria="Análise",
                    resumo="Reúne os módulos de modelação 3D, como Wireframe, Block Model e Implicit Model, para leitura técnica mais profunda.",
                    passos=[
                        "Abre 3D Avançado para entrar no hub dos modelos.",
                        "Escolhe o tipo de análise: wireframe, block model ou implicit model.",
                        "Aplica filtros, compara resultados e exporta o que for útil para análise técnica.",
                    ],
                    palavras_chave="3d avançado wireframe block model implicit model análise técnica",
                    rota="projetos:modelos_3d_hub",
                ),
            ],
        },
        {
            "chave": "empregado",
            "titulo": "Empregados",
            "descricao": "Tutoriais para o dia a dia do trabalhador: turnos, registos, notificações, materiais e consultas técnicas.",
            "artigos": [
                _artigo_ajuda(
                    titulo="Minha Área",
                    categoria="Painel pessoal",
                    resumo="É o ponto de entrada do trabalhador para ver o turno de referência, o último turno no furo e os atalhos principais.",
                    passos=[
                        "Entra em Minha Área para ver logo o turno atual ou o próximo turno.",
                        "Consulta o bloco do último turno no mesmo furo antes de começares a trabalhar.",
                        "Usa os atalhos rápidos para Novo Registo, Calendário e Notificações.",
                    ],
                    palavras_chave="minha área painel trabalhador turno referência último turno furo",
                    rota="projetos:area_empregado",
                ),
                _artigo_ajuda(
                    titulo="Calendário de Turnos",
                    categoria="Turnos e férias",
                    resumo="Mostra dias trabalhados, turnos planeados e permite pedir férias em um ou vários dias do ano.",
                    passos=[
                        "Abre Calendário de Turnos e navega pelo ano.",
                        "Seleciona um ou vários dias futuros para pedir férias.",
                        "Submete o pedido e acompanha depois a resposta nas Notificações.",
                    ],
                    palavras_chave="calendário turnos férias pedido dias trabalhador",
                    rota="projetos:calendario_turnos_empregado",
                ),
                _artigo_ajuda(
                    titulo="Novo Registo Diário",
                    categoria="Registos",
                    resumo="Cria o registo do turno com informação operacional e técnica, usando planeamento, listas de furadas, ocorrências, polímeros e equipa.",
                    passos=[
                        "Seleciona o planeamento do turno para herdar projeto, furo, data e horas.",
                        "Preenche o registo operacional e depois a informação técnica do turno.",
                        "Guarda o registo depois de rever horas, metros, furadas, ocorrências e equipa.",
                    ],
                    palavras_chave="novo registo diário ficha técnica turno furadas ocorrências equipa",
                    rota="projetos:registo_diario_create",
                ),
                _artigo_ajuda(
                    titulo="Meus Registos",
                    categoria="Registos",
                    resumo="Consulta os registos já feitos, abre a ficha técnica integrada e corrige o que for necessário.",
                    passos=[
                        "Entra em Meus Registos para ver o histórico do teu trabalho.",
                        "Abre cada registo para rever a parte operacional e técnica.",
                        "Usa editar/corrigir quando precisares de atualizar o conteúdo.",
                    ],
                    palavras_chave="meus registos histórico ficha técnica consultar editar",
                    rota="projetos:registo_diario_list",
                ),
                _artigo_ajuda(
                    titulo="Notificações",
                    categoria="Comunicação",
                    resumo="Recebe respostas a férias, alertas úteis e outros avisos pessoais ligados ao teu trabalho diário.",
                    passos=[
                        "Abre Notificações para ver o que está aberto, em andamento ou resolvido.",
                        "Consulta o detalhe de cada alerta.",
                        "Muda o estado quando já leste ou trataste da situação.",
                    ],
                    palavras_chave="notificações férias alertas trabalhador mensagens",
                    rota="projetos:notificacoes_empregado",
                ),
                _artigo_ajuda(
                    titulo="Configurações de Perfuração",
                    categoria="Operação",
                    resumo="Guarda configurações técnicas usadas em furos e reaproveita esse histórico quando voltares ao mesmo contexto.",
                    passos=[
                        "Abre Minhas Configurações para criar ou rever parâmetros usados.",
                        "Consulta o histórico se precisares de recuperar uma configuração anterior.",
                        "Aplica a configuração correta ao contexto do furo e do turno.",
                    ],
                    palavras_chave="configurações perfuração histórico parâmetros operação",
                    rota="projetos:configuracao_perfuracao_list_empregado",
                ),
                _artigo_ajuda(
                    titulo="Meus Projetos e Meus Furos",
                    categoria="Consulta técnica",
                    resumo="Consulta os projetos e furos em que estás envolvido, com acesso rápido ao detalhe técnico e operacional.",
                    passos=[
                        "Abre Meus Projetos para perceber onde estás alocado.",
                        "Abre Meus Furos para consultar o detalhe técnico do furo.",
                        "Usa estes ecrãs para validar contexto antes de registar o turno.",
                    ],
                    palavras_chave="meus projetos meus furos detalhe técnico trabalhador",
                    rota="projetos:meus_projetos_empregado",
                ),
                _artigo_ajuda(
                    titulo="Medições",
                    categoria="Consulta técnica",
                    resumo="Consulta medições e acompanhamento técnico ligado ao teu trabalho nos furos e projetos.",
                    passos=[
                        "Abre Mediçōes para ver os registos técnicos disponíveis.",
                        "Filtra pelo contexto necessário.",
                        "Usa a leitura técnica para apoiar a decisão no turno seguinte.",
                    ],
                    palavras_chave="medições trabalhador consulta técnica",
                    rota="projetos:medicao_list_empregado",
                ),
                _artigo_ajuda(
                    titulo="Materiais, Levantamentos e Devoluções",
                    categoria="Materiais",
                    resumo="Consulta materiais disponíveis e acompanha o que já levantaste ou devolveste.",
                    passos=[
                        "Abre Materiais para ver o que está disponível.",
                        "Consulta os teus levantamentos e devoluções para manter rastreio.",
                        "Se fores conta individual, podes também criar novos materiais conforme permissões.",
                    ],
                    palavras_chave="materiais levantamentos devoluções stock trabalhador",
                    rota="projetos:materiais_disponiveis_empregado",
                ),
                _artigo_ajuda(
                    titulo="Avarias de Máquinas",
                    categoria="Ocorrências",
                    resumo="Permite registar avarias e acompanhar as avarias pelas quais foste responsável.",
                    passos=[
                        "Usa Registar Avaria Máquina quando acontecer uma falha.",
                        "Consulta Minhas Avarias para acompanhar o estado.",
                        "Atualiza a ocorrência quando houver progresso ou correção.",
                    ],
                    palavras_chave="avarias máquinas registar minhas avarias manutenção",
                    rota="projetos:avaria_maquina_create_empregado",
                ),
                _artigo_ajuda(
                    titulo="Meus Dados",
                    categoria="Conta",
                    resumo="Atualiza dados pessoais e consulta a informação associada à tua conta de trabalhador.",
                    passos=[
                        "Abre Meus Dados para rever os teus dados principais.",
                        "Atualiza o que estiver desatualizado.",
                        "Confirma sempre o contacto certo para receber alertas úteis.",
                    ],
                    palavras_chave="meus dados trabalhador conta perfil",
                    rota="projetos:meus_dados_empregado",
                ),
                _artigo_ajuda(
                    titulo="Diário Técnico",
                    categoria="Consulta técnica",
                    resumo="É um espaço de consulta rápida de informação técnica e operacional recente, útil para relembrar contexto antes de arrancar para o turno.",
                    passos=[
                        "Abre Diário Técnico a partir do menu do utilizador.",
                        "Consulta notas, contexto técnico e elementos operacionais recentes.",
                        "Usa esta leitura antes de iniciar o trabalho ou antes de preencher um novo registo.",
                    ],
                    palavras_chave="diário técnico notas contexto técnico trabalhador",
                    rota="projetos:diario_tecnico",
                ),
                _artigo_ajuda(
                    titulo="Definições",
                    categoria="Conta",
                    resumo="Permite ajustar preferências pessoais da conta do trabalhador e pequenos parâmetros de utilização da plataforma.",
                    passos=[
                        "Abre Definições no menu do utilizador.",
                        "Revê as preferências disponíveis para a tua conta.",
                        "Guarda as alterações para manter a experiência alinhada com o teu dia a dia.",
                    ],
                    palavras_chave="definições trabalhador preferências conta",
                    rota="projetos:definicoes",
                ),
                _artigo_ajuda(
                    titulo="Sugestões",
                    categoria="Colaboração",
                    resumo="Se algo te estiver a dificultar o trabalho, usa Sugestões para enviar melhorias diretamente com contexto real da operação.",
                    passos=[
                        "Abre Sugestões no menu do utilizador.",
                        "Descreve claramente a melhoria, erro ou dificuldade encontrada.",
                        "Submete para a sugestão ficar registada e poder ser avaliada.",
                    ],
                    palavras_chave="sugestões trabalhador melhorias feedback plataforma",
                    rota="projetos:sugestoes_plataforma",
                ),
            ],
        },
        {
            "chave": "individual",
            "titulo": "Individual",
            "descricao": "Tutoriais para contas individuais, com foco em autonomia operacional, registos e gestão pessoal dentro da plataforma.",
            "artigos": [
                _artigo_ajuda(
                    titulo="Área Individual",
                    categoria="Painel pessoal",
                    resumo="É o painel principal da conta individual, com resumo das horas, metros e registos já criados.",
                    passos=[
                        "Entra na tua área para ver o resumo pessoal.",
                        "Usa os atalhos rápidos para navegação do dia a dia.",
                        "Consulta totais de trabalho e atividade já acumulada.",
                    ],
                    palavras_chave="individual área painel pessoal resumo horas metros",
                    rota="projetos:area_empregado",
                ),
                _artigo_ajuda(
                    titulo="Novo Registo Diário",
                    categoria="Registos",
                    resumo="As contas individuais usam o mesmo registo diário para guardar trabalho, informação técnica e histórico.",
                    passos=[
                        "Abre Novo Registo Diário a partir do menu Registos.",
                        "Preenche o turno e a informação técnica relevante.",
                        "Guarda e depois consulta tudo em Meus Registos.",
                    ],
                    palavras_chave="individual novo registo diário ficha técnica",
                    rota="projetos:registo_diario_create",
                ),
                _artigo_ajuda(
                    titulo="Meus Registos",
                    categoria="Registos",
                    resumo="Consulta o teu histórico operacional e técnico e reabre registos sempre que precisares de corrigir dados.",
                    passos=[
                        "Abre Meus Registos para consultar o histórico.",
                        "Usa a ficha técnica dentro de cada registo.",
                        "Edita apenas quando precisas de corrigir informação real.",
                    ],
                    palavras_chave="individual meus registos histórico editar",
                    rota="projetos:registo_diario_list",
                ),
                _artigo_ajuda(
                    titulo="Calendário de Turnos",
                    categoria="Turnos e férias",
                    resumo="A conta individual também pode consultar dias trabalhados e, quando aplicável, gerir pedidos de férias.",
                    passos=[
                        "Abre o Calendário de Turnos para ver o planeamento e o histórico diário.",
                        "Seleciona dias para pedido de férias, se esse fluxo se aplicar à tua conta.",
                        "Acompanha o estado do pedido nas Notificações.",
                    ],
                    palavras_chave="individual calendário turnos férias",
                    rota="projetos:calendario_turnos_empregado",
                ),
                _artigo_ajuda(
                    titulo="Notificações",
                    categoria="Comunicação",
                    resumo="Reúne avisos pessoais, pedidos pendentes e respostas úteis para a tua conta individual.",
                    passos=[
                        "Abre Notificações para ver o que mudou.",
                        "Consulta cada alerta e usa o estado para organização pessoal.",
                        "Volta ao ecrã de origem se precisares de agir sobre o aviso.",
                    ],
                    palavras_chave="individual notificações alertas mensagens",
                    rota="projetos:notificacoes_empregado",
                ),
                _artigo_ajuda(
                    titulo="Minhas Despesas",
                    categoria="Finanças",
                    resumo="Consulta e gere as despesas criadas pela tua conta dentro da operação.",
                    passos=[
                        "Abre Minhas Despesas a partir do menu Operação.",
                        "Cria ou revê despesas conforme o teu trabalho.",
                        "Mantém categorias e valores corretos para leitura financeira posterior.",
                    ],
                    palavras_chave="individual despesas finanças gastos",
                    rota="projetos:despesa_list_empregado",
                ),
                _artigo_ajuda(
                    titulo="Materiais",
                    categoria="Materiais",
                    resumo="As contas individuais podem consultar materiais, levantar/devolver e, quando permitido, criar novos registos de material.",
                    passos=[
                        "Consulta materiais disponíveis antes do trabalho.",
                        "Regista levantamentos e devoluções para manter controlo.",
                        "Usa Novo Material apenas quando o fluxo da tua operação o justificar.",
                    ],
                    palavras_chave="individual materiais levantamentos devoluções novo material",
                    rota="projetos:materiais_disponiveis_empregado",
                ),
                _artigo_ajuda(
                    titulo="Meus Dados",
                    categoria="Conta",
                    resumo="Revê e atualiza os dados pessoais associados à tua conta individual.",
                    passos=[
                        "Abre Meus Dados a partir do menu de utilizador.",
                        "Atualiza nome, contacto e restantes dados permitidos.",
                        "Mantém a informação certa para evitar problemas de acesso e comunicação.",
                    ],
                    palavras_chave="individual meus dados conta perfil",
                    rota="projetos:meus_dados_empregado",
                ),
                _artigo_ajuda(
                    titulo="Diário Técnico",
                    categoria="Consulta técnica",
                    resumo="Ajuda-te a rever o teu contexto técnico recente, histórico e notas operacionais antes de criar novos registos ou retomar trabalho.",
                    passos=[
                        "Abre Diário Técnico no menu do utilizador.",
                        "Consulta o contexto recente e as notas relevantes para o teu trabalho.",
                        "Usa essa leitura para preparar melhor o registo ou o turno seguinte.",
                    ],
                    palavras_chave="individual diário técnico consulta contexto",
                    rota="projetos:diario_tecnico",
                ),
                _artigo_ajuda(
                    titulo="Definições",
                    categoria="Conta",
                    resumo="Permite ajustar preferências da tua conta individual e pequenos comportamentos da plataforma no uso do dia a dia.",
                    passos=[
                        "Abre Definições a partir do menu do utilizador.",
                        "Revê preferências pessoais e parâmetros disponíveis.",
                        "Guarda só depois de confirmar que a alteração faz sentido para o teu fluxo.",
                    ],
                    palavras_chave="individual definições preferências conta",
                    rota="projetos:definicoes",
                ),
                _artigo_ajuda(
                    titulo="Sugestões",
                    categoria="Colaboração",
                    resumo="Usa Sugestões para reportar melhorias e necessidades reais de utilização da plataforma a partir da tua conta individual.",
                    passos=[
                        "Abre Sugestões no menu do utilizador.",
                        "Descreve a necessidade ou melhoria com exemplos práticos.",
                        "Submete a ideia para ficar no histórico de evolução da plataforma.",
                    ],
                    palavras_chave="individual sugestões feedback melhoria",
                    rota="projetos:sugestoes_plataforma",
                ),
            ],
        },
    ]


def _guias_destaque_ajuda():
    return [
        {
            "titulo": "Planeamento em detalhe",
            "subtitulo": "Para empresas",
            "descricao": "Guia rápido para criar turnos, respeitar horários por máquina e validar cobertura diária da operação.",
            "passos": [
                "Criar o turno com projeto, furo, máquina e trabalhador.",
                "Confirmar horário oficial da máquina e resolver conflitos.",
                "Consultar o calendário semanal/mensal para garantir cobertura.",
            ],
            "rota": "projetos:planeamento_turno_list",
            "palavras_chave": "planeamento turnos máquina horário calendário cobertura",
        },
        {
            "titulo": "RH & Assiduidade em detalhe",
            "subtitulo": "Para empresas",
            "descricao": "Guia focado em férias, aprovações, saldos e leitura diária da equipa pelo calendário operacional.",
            "passos": [
                "Filtrar o período e abrir o calendário operacional da equipa.",
                "Ver quem trabalhou em cada dia e que ausências existem.",
                "Aprovar ou rejeitar pedidos e confirmar o saldo mensal por colaborador.",
            ],
            "rota": "projetos:assiduidade_list",
            "palavras_chave": "rh assiduidade férias aprovações saldo calendário equipa",
        },
        {
            "titulo": "Registos em detalhe",
            "subtitulo": "Para empregados e individuais",
            "descricao": "Guia para preencher turnos, furadas, ocorrências, equipa e rever a ficha técnica depois de guardar.",
            "passos": [
                "Selecionar o planeamento quando existir.",
                "Preencher o registo operacional e a informação técnica do turno.",
                "Consultar depois em Meus Registos ou Registos de Produção.",
            ],
            "rota": "projetos:registo_diario_create",
            "palavras_chave": "registos ficha técnica turno furadas ocorrências equipa",
        },
    ]


def _faq_ajuda():
    return [
        {
            "pergunta": "Não vejo uma opção no menu. O que devo confirmar?",
            "resposta": "Confirma primeiro o tipo de conta com que estás autenticado. Empresas, empregados e contas individuais veem menus diferentes e algumas funções dependem também da função operacional ou das permissões atribuídas.",
        },
        {
            "pergunta": "Como encontro rapidamente um tutorial específico?",
            "resposta": "Usa a caixa de procura no topo da Ajuda. Escreve palavras como férias, registo, compras, máquinas, planeamento ou relatórios. A página filtra os artigos e salta para o primeiro resultado encontrado.",
        },
        {
            "pergunta": "Onde acompanho pedidos de férias?",
            "resposta": "O trabalhador acompanha em Calendário de Turnos e Notificações. A empresa acompanha em Gestão > RH & Assiduidade, onde consegue aprovar, rejeitar e consultar o calendário operacional da equipa.",
        },
        {
            "pergunta": "Qual é a diferença entre Registo Diário e Ficha Técnica?",
            "resposta": "O Registo Diário é o registo principal do turno. A ficha técnica está integrada nesse mesmo registo e guarda o detalhe operacional e técnico, como furadas, ocorrências, polímeros, equipa e notas do turno.",
        },
        {
            "pergunta": "Quem pode exportar relatórios e ficheiros?",
            "resposta": "As exportações mais sensíveis ficam reservadas à empresa. O empregado consulta a informação técnica, mas a descarga de documentação formal e consolidada é feita a partir das áreas administrativas.",
        },
        {
            "pergunta": "O que faço se um dado foi lançado errado?",
            "resposta": "Sempre que possível, edita o registo existente em vez de apagar. Assim manténs melhor continuidade de histórico e reduzes o risco de perder contexto importante da operação.",
        },
    ]


def _classificar_contexto_ajuda(nome_rota):
    if not nome_rota:
        return "pagina"

    if any(
        marcador in nome_rota
        for marcador in (
            "_create",
            "_novo",
            "_nova",
            "adicionar",
        )
    ):
        return "novo"
    if any(marcador in nome_rota for marcador in ("_update", "_editar")):
        return "editar"
    if any(marcador in nome_rota for marcador in ("_delete", "_apagar", "_rejeitar")):
        return "apagar"
    if any(
        marcador in nome_rota
        for marcador in (
            "_detail",
            "_legacy",
            "_pdf",
            "_3d",
            "_comparar",
            "_historico",
        )
    ):
        return "detalhe"
    if any(
        marcador in nome_rota
        for marcador in (
            "_aprovar",
            "_executar",
            "_estado",
            "_selecionar",
            "_restaurar",
            "_terminar",
            "_reativar",
            "_resolver",
            "_ligar",
            "_gerar",
            "_entrada",
            "_saida",
            "_export",
            "_download",
            "_aplicar",
        )
    ):
        return "acao"
    return "lista"


def _enriquecer_contexto_ajuda(base):
    contexto = _classificar_contexto_ajuda(base["nome_rota_pedida"])
    contextualizacoes = {
        "lista": "Estás numa vista de consulta e acompanhamento. Este tutorial ajuda-te a perceber filtros, leitura e próximos passos mais úteis desta área.",
        "detalhe": "Estás a ver detalhe técnico ou comercial. Este tutorial ajuda-te a interpretar a informação desta área antes de editar, exportar ou avançar.",
        "novo": "Estás numa criação nova. Este tutorial mostra a ordem de preenchimento mais segura e o que vale a pena confirmar antes de gravar.",
        "editar": "Estás a atualizar um registo existente. Este tutorial ajuda-te a corrigir sem perder contexto e a rever os campos com mais impacto.",
        "apagar": "Estás numa ação sensível. Este tutorial ajuda-te a perceber quando apagar faz sentido e quando é preferível editar ou fechar o registo.",
        "acao": "Estás numa ação rápida desta área. Este tutorial dá-te contexto para executar a operação com mais segurança e perceber o efeito esperado.",
        "pagina": "Este tutorial explica o objetivo desta página e como navegar nela com mais confiança.",
    }
    etiquetas = {
        "lista": "Tutorial da lista",
        "detalhe": "Tutorial do detalhe",
        "novo": "Tutorial da criação",
        "editar": "Tutorial da edição",
        "apagar": "Tutorial da ação sensível",
        "acao": "Tutorial da ação",
        "pagina": "Tutorial desta página",
    }
    ctas = {
        "lista": "Ver tutorial desta lista",
        "detalhe": "Ver tutorial deste detalhe",
        "novo": "Ver tutorial desta criação",
        "editar": "Ver tutorial desta edição",
        "apagar": "Ver tutorial desta ação",
        "acao": "Ver tutorial desta ação",
        "pagina": "Ver tutorial desta página",
    }
    return {
        **base,
        "contexto_tipo": contexto,
        "contexto_label": etiquetas[contexto],
        "contextualizacao": contextualizacoes[contexto],
        "acao_label_contextual": ctas[contexto],
    }


def obter_ajuda_contextual(nome_rota):
    if not nome_rota or nome_rota == "projetos:ajuda":
        return None

    artigos_por_rota = {}
    for perfil in _ajuda_por_perfil():
        for artigo in perfil["artigos"]:
            rota = artigo.get("rota")
            if not rota:
                continue
            artigos_por_rota[rota] = {
                "anchor": artigo["id"],
                "titulo": artigo["titulo"],
                "descricao": artigo["resumo"],
                "perfil": perfil["titulo"],
                "categoria": artigo["categoria"],
            }

    aliases = {
        "projetos:dashboard": "projetos:gestao_hub",
        "projetos:gestao_clientes_contratos": "projetos:cliente_contrato_list",
        "projetos:gestao_planeamento": "projetos:planeamento_turno_list",
        "projetos:gestao_rh_assiduidade": "projetos:assiduidade_list",
        "projetos:assiduidade_create": "projetos:assiduidade_list",
        "projetos:assiduidade_update": "projetos:assiduidade_list",
        "projetos:assiduidade_delete": "projetos:assiduidade_list",
        "projetos:assiduidade_aprovar": "projetos:assiduidade_list",
        "projetos:assiduidade_rejeitar": "projetos:assiduidade_list",
        "projetos:registo_diario_update": "projetos:registo_diario_create",
        "projetos:registo_admin_create": "projetos:registos_admin_list",
        "projetos:registo_admin_update": "projetos:registos_admin_list",
        "projetos:relatorio_turno_list": "projetos:registo_diario_list",
        "projetos:relatorio_turno_detail": "projetos:registo_diario_list",
        "projetos:relatorio_turno_update": "projetos:registo_diario_list",
        "projetos:relatorio_turno_admin_list": "projetos:registos_admin_list",
        "projetos:relatorio_turno_admin_detail": "projetos:registos_admin_list",
        "projetos:relatorio_turno_admin_update": "projetos:registos_admin_list",
        "projetos:projeto_create": "projetos:projeto_list",
        "projetos:projeto_update": "projetos:projeto_list",
        "projetos:projeto_delete": "projetos:projeto_list",
        "projetos:projeto_detail": "projetos:projeto_list",
        "projetos:projeto_detail_legacy": "projetos:projeto_list",
        "projetos:projeto_3d": "projetos:projeto_list",
        "projetos:furo_create": "projetos:projeto_list",
        "projetos:furo_update": "projetos:projeto_list",
        "projetos:furo_delete": "projetos:projeto_list",
        "projetos:furo_detail_legacy": "projetos:projeto_list",
        "projetos:furo_detail": "projetos:projeto_list",
        "projetos:furo_3d": "projetos:projeto_list",
        "projetos:furo_3d_detail": "projetos:projeto_list",
        "projetos:furo_3d_importar_externo": "projetos:modelos_3d_hub",
        "projetos:medicao_update": "projetos:medicao_list",
        "projetos:medicao_delete": "projetos:medicao_list",
        "projetos:medicao_create": "projetos:medicao_list",
        "projetos:maquina_create": "projetos:empregado_list",
        "projetos:maquina_update": "projetos:empregado_list",
        "projetos:maquina_delete": "projetos:empregado_list",
        "projetos:maquina_detail": "projetos:empregado_list",
        "projetos:maquina_turno_create": "projetos:planeamento_turno_list",
        "projetos:maquina_turno_update": "projetos:planeamento_turno_list",
        "projetos:maquina_turno_delete": "projetos:planeamento_turno_list",
        "projetos:material_create": "projetos:material_list",
        "projetos:material_update": "projetos:material_list",
        "projetos:material_delete": "projetos:material_list",
        "projetos:material_detail": "projetos:material_list",
        "projetos:entrada_material": "projetos:material_list",
        "projetos:saida_material": "projetos:material_list",
        "projetos:despesa_create_admin": "projetos:despesa_list_admin",
        "projetos:despesa_update_admin": "projetos:despesa_list_admin",
        "projetos:despesa_delete_admin": "projetos:despesa_list_admin",
        "projetos:despesa_detail_admin": "projetos:despesa_list_admin",
        "projetos:despesa_create_empregado": "projetos:despesa_list_empregado",
        "projetos:cliente_contrato_painel_clientes": "projetos:cliente_contrato_list",
        "projetos:cliente_comercial_detail": "projetos:cliente_contrato_list",
        "projetos:cliente_comercial_update": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_create": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_detail": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_update": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_delete": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_anexo_create": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_anexo_delete": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_adenda_create": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_adenda_update": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_adenda_delete": "projetos:cliente_contrato_list",
        "projetos:cliente_contrato_aplicar_sugestao_workflow": "projetos:cliente_contrato_list",
        "projetos:planeamento_turno_create": "projetos:planeamento_turno_list",
        "projetos:planeamento_turno_update": "projetos:planeamento_turno_list",
        "projetos:planeamento_turno_delete": "projetos:planeamento_turno_list",
        "projetos:empregado_create": "projetos:empregado_list",
        "projetos:empregado_update": "projetos:empregado_list",
        "projetos:empregado_delete": "projetos:empregado_list",
        "projetos:empregado_detail": "projetos:empregado_list",
        "projetos:empregado_detail_legacy": "projetos:empregado_list",
        "projetos:empregado_pendentes": "projetos:empregado_list",
        "projetos:empregado_aprovar": "projetos:empregado_list",
        "projetos:empregado_rejeitar": "projetos:empregado_list",
        "projetos:empregado_ligar_utilizador": "projetos:empregado_list",
        "projetos:configuracao_list": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_create_empregado": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_detail_empregado": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_update_empregado": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_delete_empregado": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:historico_configuracao_list_empregado": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_list_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_create_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:historico_configuracao_list_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_detail_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_update_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:configuracao_perfuracao_delete_admin": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:historico_configuracao_detail": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:historico_configuracao_comparar": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:historico_configuracao_restaurar": "projetos:configuracao_perfuracao_list_empregado",
        "projetos:meus_furos_empregado": "projetos:meus_projetos_empregado",
        "projetos:furo_detail_empregado": "projetos:meus_projetos_empregado",
        "projetos:furo_3d_empregado": "projetos:meus_projetos_empregado",
        "projetos:projeto_detail_empregado": "projetos:meus_projetos_empregado",
        "projetos:material_create_empregado": "projetos:materiais_disponiveis_empregado",
        "projetos:levantamento_list": "projetos:materiais_disponiveis_empregado",
        "projetos:devolucao_material_list": "projetos:materiais_disponiveis_empregado",
        "projetos:medicao_detail_empregado": "projetos:medicao_list_empregado",
        "projetos:avaria_maquina_minhas_empregado": "projetos:avaria_maquina_create_empregado",
        "projetos:avaria_maquina_update_empregado": "projetos:avaria_maquina_create_empregado",
        "projetos:meus_dados_empregado_editar": "projetos:meus_dados_empregado",
        "plataforma:onboarding_empresa": "projetos:gestao_hub",
        "plataforma:plano_list": "projetos:gestao_hub",
        "plataforma:subscricao_list": "projetos:gestao_hub",
    }

    rota_base = aliases.get(nome_rota, nome_rota)
    contexto = artigos_por_rota.get(rota_base)
    if not contexto:
        return None

    return _enriquecer_contexto_ajuda({
        **contexto,
        "rota_origem": rota_base,
        "nome_rota_pedida": nome_rota,
    })


@login_required
def ajuda(request):
    ajuda_por_perfil = _ajuda_por_perfil()
    return render(
        request,
        "projetos/ajuda.html",
        {
            "titulo": "Ajuda",
            "ajuda_por_perfil": ajuda_por_perfil,
            "guias_destaque": _guias_destaque_ajuda(),
            "faq_ajuda": _faq_ajuda(),
        },
    )


@login_required
def sobre(request):
    return render(
        request,
        "projetos/sobre.html",
        {
            "titulo": "Sobre",
        },
    )


@login_required
def termos_condicoes(request):
    return render(
        request,
        "projetos/termos_condicoes.html",
        {
            "titulo": "Termos & Condições",
        },
    )


@login_required
def politica_privacidade(request):
    return render(
        request,
        "projetos/politica_privacidade.html",
        {
            "titulo": "Política de Privacidade",
        },
    )
