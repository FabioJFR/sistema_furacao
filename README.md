# Sistema Furação

Sistema web em **Django** para controlo de operações no terreno em projetos de **diamond drilling**.

O foco do MVP é a operação diária: projetos, furos, equipa, turnos, registos de produção, medições, máquinas, materiais, configuração de perfuração por furo e relatórios técnicos. As áreas comerciais/financeiras mais amplas continuam preservadas no código como módulos pós-MVP, mas não devem liderar a experiência principal enquanto o produto de campo não estiver validado.

---

## Estado atual

- Versão atual: **v0.9.8**
- Estado: **desenvolvimento ativo**
- Foco imediato: **MVP operacional de terreno**, **estabilização em servidor**, **correções de permissões/navegação** e **preparação de dados para IA futura**

### Stack principal

- **Backend:** Django 6 / Python 3.14
- **Frontend:** HTML, CSS, JavaScript
- **Mapas:** Leaflet
- **Gráficos:** Chart.js
- **Visualização 3D de furos:** Plotly
- **Base de dados:** PostgreSQL

---

## Release 0.9.8 (resumo)

Principais evoluções consolidadas nesta versão:

- foco de produto reformulado para **MVP operacional de terreno**, evitando que módulos de ERP/financeiro/comercial dominem a experiência principal
- nova flag `SF_MVP_OPERACIONAL_FOCUS`, ativa por defeito, para manter o menu da empresa focado em `Operação` e `Registos`
- `Planeamento` passa a estar acessível dentro de `Operação` quando o foco MVP está ativo
- módulos como `Gestão`, `Finanças`, `Analytics`, clientes/contratos, compras, compliance, salários e preço por metro ficam preservados como **pós-MVP/opcionais**
- correção defensiva da página `Subscrições` para evitar erro 500 quando o diagnóstico de email transacional falha ou quando existem dados incompletos
- `Features` passa a listar apenas contas individuais ativadas por email (`user.is_active=True`)
- reforço de testes de regressão para navegação MVP, dashboard da plataforma, features e subscrições
- configuração de perfuração por furo consolidada como elemento operacional partilhado por todos os empregados que trabalham no furo
- `Medida Morta` passa a viver na configuração de perfuração e fica preservada no histórico de configurações

## Release 0.9.7 (resumo)

Principais evoluções consolidadas nesta versão:

- endurecimento de segurança com `bridge keys` apenas por header, validação reforçada de URLs configuráveis e proteção básica contra abuso em `login` e `password reset`
- hardening de uploads com comportamento `fail closed` configurável para antivírus e melhor tratamento de falhas de scanner
- revisão de `open redirect` em fluxos operacionais com testes de regressão dedicados
- evolução da cartografia geológica interna com visualizador próprio, camadas oficiais LNEG, identificação por clique e gestão de fontes privadas por empresa
- preparação de deploy reforçada com checklist de produção, variáveis de ambiente de segurança e documentação atualizada
- expansão da cobertura de testes para segurança, assiduidade, notificações, contexto de menu e regressões de registos
- ajuda contextual, centro de ajuda por perfil e onboarding configurável diretamente nas definições
- área de empregado reforçada com calendário de turnos, notificações, férias e melhor contexto operacional do último turno/furo

- novo módulo `Gestão` para empresas com hub e áreas de `Clientes & Contratos`, `Planeamento`, `RH & Assiduidade`, `Compras & Fornecedores`, `Compliance & Segurança`, `Notificações` e `Relatórios Executivos`
- evolução de `Relatórios Executivos` com comparativo financeiro por projeto (metros, registos, custo, receita estimada e margem)
- exportação de relatórios executivos em CSV/XLSX alinhada com filtros de período
- envio manual por email do relatório executivo com anexos CSV/XLSX
- agendamento automático de envio (diário/semanal/mensal), com execução imediata manual e comando de processamento para servidor

- paridade de permissões para conta `individual` na área de trabalhador (fluxo equivalente ao empregado de empresa)
- criação automática de contexto interno de operação para contas individuais (evita bloqueios em menus operacionais)
- melhoria de `Conta > Meus Dados` com bloco de plano atual, fim de ciclo e próximo pagamento
- exibição da empresa associada para empregados de empresa em `Conta > Meus Dados`
- novo atalho `Sugestões` no submenu de utilizador (empresa, empregado e individual)
- nova página de sugestões com avaliação, opinião e propostas de melhoria
- envio automático das sugestões por email para o(s) superuser(s), com registo persistido em base de dados
- ativação de conta por confirmação de email no registo público (conta nasce inativa até validação)
- nova rota de confirmação de conta e integração de token seguro no fluxo de registo
- parametrização de SMTP por variáveis de ambiente (`DJANGO_EMAIL_*` e `SITE_BASE_URL`)
- reorganização da operação `Drone S_F` para ficar alinhada com o padrão visual da área `DJI`
- motor de missões programadas com repetição contínua por checkbox (ativar/desativar)
- quadro de estado com últimas missões disparadas e últimos comandos gerados
- evolução da página de detalhe da análise IA (layout, contexto, estado, leitura estimada e scroll por painel)
- `reprocessar` no histórico de análises para gerar nova análise com as melhorias mais recentes
- fluxo de análise em pré-visualização com botão explícito para `Guardar análise`
- ferramentas de seleção de área e zonas de análise com criação/nomeação de retângulos reutilizáveis
- melhoria de permissões para `superuser` no menu `Plataforma` e submenu `AI`
- secção `Úteis` com exportação/limpeza de dados AI e operacionais
- reforço de higiene técnica: redução de URLs hardcoded, migração contínua de CSS/JS para `static/`, e avanço na separação de `selectors/` e `services/`
- melhorias de prontidão para deploy: hardening de `settings` por variáveis de ambiente, `STATIC_ROOT`, e limpeza de configuração de static em URL de app
- fluxo de avarias de máquinas evoluído com atribuição de responsável, atualização de estado por responsável e notificações por email para intervenientes
- novo arquivo técnico de furos terminados na área de plataforma (`Úteis > Arquivo de Furos`) para consulta histórica por superuser
- lista de despesas da empresa com ações completas por registo: ver detalhe, editar e apagar
- formulário de despesa com opção explícita de voltar sem gravar
- uniformização visual progressiva de botões/listagens para paleta profissional em vez de cores vivas dispersas
- conector inicial MagCruiser com importação de ficheiros `CSV/LAS`, pré-visualização e gravação direta de medições
- deteção de nome de furo nas linhas importadas para mapeamento automático com furos da empresa
- modos de aplicação de importação: todas as medições, apenas última por furo, ou criação automática de furos em falta
- relatório de importação com totais (gravadas/ignoradas/criadas), detalhe por furo e exportação em CSV
- histórico de importações de dispositivo por empresa para rastreabilidade operacional
- proteção na captura de dispositivos para evitar erro 500 quando a migração do histórico ainda não foi aplicada

---

## Áreas principais

### MVP operacional de terreno

Este é o núcleo que deve orientar o piloto e a validação com utilizadores reais:

- projetos, furos e estado operacional
- equipa, empregados, turnos e planeamento
- registos diários de produção e ficha técnica do turno
- configuração de perfuração por furo, incluindo `Medida Morta`
- medições, desvios e importação MagCruiser
- máquinas, avarias e materiais essenciais
- geologia operacional quando aplicável ao trabalho do dia
- relatórios técnicos e exportações diretamente ligados ao furo/turno

### Pós-MVP / módulos opcionais

Estas áreas existem no código, mas devem ficar secundárias até o MVP de terreno estar validado:

- despesas detalhadas e definições financeiras
- salários, payroll e regras de custo interno
- preço por metro por cliente
- clientes, contratos e workflow comercial
- compras e fornecedores
- compliance avançado, auditorias e ações preventivas/corretivas
- relatórios executivos financeiros/comerciais
- dashboards de rentabilidade/analytics não essenciais ao campo

### Plataforma / multiempresa

- empresas, planos e perfis de acesso
- área administrativa por empresa
- área de trabalhador
- fluxo de aprovação de utilizadores ligados a empresa
- gestão de features por empresa e conta individual
- área `Úteis` para exportação, limpeza controlada e scripts operacionais de apoio

### Operação

- projetos com localização
- furos de fundo e superfície
- registos diários de produção
- medições e desvios
- associação de trabalhadores e máquinas a projetos e furos
- configuração de perfuração por furo

### Materiais e máquinas

- materiais por empresa, projeto e furo
- stock mínimo e alertas de stock baixo
- máquinas com estados operacionais e alertas

### Relatórios técnicos

- dashboards operacionais
- gráficos de produção e alertas
- relatórios em `CSV`, `XLSX`, `JSON` e `PDF`
- exportação em pacote `ZIP`

### Geologia

- hub geológico
- logs geológicos por intervalo
- anexos geológicos
- dashboard geológico por furo
- missões de drone por furo

### IA

- análise visual de fotografias
- estrutura para caixas de amostras e relatórios manuscritos
- chatbox com contexto real da empresa
- base documental para apoiar respostas futuras
- biblioteca documental com ficheiros textuais e PDFs com apoio por `.txt`

### Dispositivos (MagCruiser)

- suporte operacional inicial para fluxo MagCruiser por ficheiro (`CSV` e `LAS`)
- preview antes de gravar para validação de profundidade/inclinação/azimute
- reconhecimento de nome de furo por linha (`hole`, `hole_name`, `furo`, etc.)
- associação automática ao furo existente da empresa quando há correspondência
- opção de criação automática de furos em falta durante a importação
- gravação estruturada para leituras brutas, survey shots e medições associadas ao furo correto
- relatório final de importação e histórico persistido para auditoria
- fallback seguro na listagem de histórico para não interromper a página quando a tabela ainda não existe

Comando de correção quando faltar a tabela de histórico:

- `python manage.py migrate dispositivos`

---

## Funcionalidades implementadas

### Projetos e furos

- gestão completa de projetos
- detalhe de projeto com equipa envolvida
- criação e gestão de furos
- planeamento inicial, planeamento atual e estado real atual
- medições com inclinação, azimute, dogleg e desvios

### Visualização 3D do furo

- trajetória real
- trajetória planeada e comparação real vs planeado
- painel lateral com filtros
- filtros por profundidade, dogleg e estado
- modos de visualização
- ângulos de câmara rápidos
- quadro final de desvio, inclinação e azimute
- top 5 doglegs
- exportação rápida
- interoperabilidade 3D
- página própria para importação de trajetória externa 3D

### 3D avançado (Wireframe / Block / Implicit)

- módulo `Wireframe 3D` com preview local e histórico de modelos guardados
- módulo `Block Model 3D` com filtros por valor/Z, animações e exportação técnica (`CSV` da seleção + `JSON` técnico)
- módulo `Implicit Model 3D` com filtros por domínio, superfícies (`Delaunay`/`Convex Hull`), animações e exportação técnica (`CSV`/`JSON`)
- resumo analítico inicial no Implicit (extensões X/Y/Z, volume envolvente e estimativa por domínio)
- persistência de configuração visual por modelo no backend (Block/Implicit), guardada em `resumo_json["ui_config"]` e reaplicada ao `Reabrir preview`

### Tubos e detalhe visual do 3D

- segmentação visual dos tubos
- destaque do conjunto de fundo
- marcação das conexões entre tubos
- hover técnico por troço e por conexão
- botões rápidos de câmara no topo do gráfico

### Produção, empregados e máquinas

- registos diários por trabalhador
- produtividade por trabalhador, projeto e furo
- registo de trabalhador no site com aprovação pela empresa
- perfil `Individual` para utilizadores sem empresa
- gestão de máquinas com estados operacionais
- alertas de máquinas e stock

### Relatórios e exportação

- página própria de relatórios
- datasets de resumo, projetos, furos, máquinas, materiais, empregados, registos, medições, despesas e eventos
- filtros por projeto, furo, datas, tipo de registo e categoria de despesa
- ficheiros com nomes descritivos por filtros ativos

### Geologia e drones

- hub de geologia
- dashboard geológico por furo
- registo e edição de logs geológicos
- anexos por log
- importação pós-voo para `DJI`
- centro operacional `DJI Mini 4 Pro`
- interface própria `Drone S_F`

### IA visual

- fundação para um futuro modelo IA treinado com datasets do sistema, orientado a reconhecimento de padrões, previsão de resultados e decisão assistida
- estado atual: análise heurística e recolha de validações; ainda não existe modelo de machine learning treinado em produção
- correções manuais das análises geram exemplos rotulados versionados e exportáveis para preparação de datasets de treino
- upload de fotografia e análise visual
- deteção por zonas em caixas de amostra
- deteção por zonas em relatórios retangulares
- seleção inicial da área do relatório antes da análise
- seleção avançada de zonas com retângulos nomeáveis e guardáveis
- redimensionamento de retângulos de análise
- correção automática/manual de inclinação da imagem
- campo estruturado `campos_extraidos`
- histórico de análises por empresa
- reprocessamento de análises históricas
- modo pré-visualização e gravação manual da análise

### Chatbox AI

- chat contextual por empresa
- respostas sobre operação da plataforma
- consultas a furos, eventos, despesas, máquinas, materiais e alertas
- cálculo matemático seguro
- uso de base documental para contexto adicional
- apoio à memória operacional de zonas e furos relacionados

### Plataforma e utilitários

- submenu `AI` completo disponível para `superuser` na plataforma
- submenu `Úteis` disponível para `superuser`
- exportação de datasets AI e operacionais em `JSON`
- pacote completo em `ZIP`
- limpeza controlada de grupos de dados
- scripts operacionais executáveis pela interface
- catálogo visível de datasets configurados para exportação
- gestão de features por plano/conta com controlo por checkboxes
- maior consistência de acesso entre perfis empresa, empregado e superuser

### Arquitetura e qualidade de código

- padronização progressiva por app com pastas `selectors/` e `services/`
- redução de lógica dispersa em views/forms, com extração gradual para camadas próprias
- migração progressiva de CSS inline e blocos `<style>` para `static/css/`
- migração progressiva de JavaScript inline para `static/js/`
- reforço da política de URLs nomeadas e validação por gate de higiene

---

## DJI e Drone S_F

### Centro DJI Mini 4 Pro

Já está preparado com:

- estado de ligação
- live view / snapshot
- mapa operacional
- fila de comandos
- bridge externa
- histórico da bridge
- quadro de estado operacional
- fluxo pós-voo para importação de missões e ficheiros

Limitação atual:

- o `DJI RC 2` não permite uma integração nativa direta dentro do próprio comando
- a plataforma depende de uma ponte externa para telemetria em tempo real

Documento de continuidade:

- [knowledge_base/drone/dji_roadmap.md](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/drone/dji_roadmap.md:1)

### Interface Drone S_F

Já está preparada, separada da área `DJI`, com:

- modelos de drone, módulos, sensores e configuração
- operação em tempo real própria
- bridge S_F própria
- mapa operacional S_F
- fila de comandos S_F
- missões programadas
- motor automático de missões
- quadro de estado do motor com histórico e filtros

Estado atual:

- esta área fica documentada e pronta para retoma futura
- o foco imediato deixa de ser drone e passa para `Projetos` e `IA`

Documentos de continuidade:

- [knowledge_base/drone/drone_sf_roadmap.md](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/drone/drone_sf_roadmap.md:1)
- [knowledge_base/drone/drone_proprio_componentes.md](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/drone/drone_proprio_componentes.md:1)

---

## Base de conhecimento

Foi criada uma base documental na raiz do projeto:

- [knowledge_base/README.md](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/README.md:1)
- [knowledge_base/drone](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/drone:1)
- [knowledge_base/geologia](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/geologia:1)
- [knowledge_base/ia](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/ia:1)
- [knowledge_base/plataforma](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/plataforma:1)
- [knowledge_base/pdf](/Users/fabiorevez/Desktop/sistema_furacao/knowledge_base/pdf:1)

Objetivo:

- guardar documentos técnicos e funcionais
- permitir retoma futura sem perda de contexto
- servir de apoio à camada de IA
- permitir consulta documental futura na plataforma online

---

## Dados demo e seeds

Existem comandos para acelerar testes visuais e funcionais:

```bash
python3 manage.py gerar_dados_demo_operacao
python3 manage.py gerar_furos_demo_inclinacao_negativa
python3 manage.py reforcar_cenario_demo_multiempresa
python3 manage.py criar_drone_sf_demo
python3 manage.py preencher_furos_e_materiais_base
```

Também existem ferramentas de bridge e simulação em `geologia/management/commands/` para testes de `DJI` e `Drone S_F`.

O comando `preencher_furos_e_materiais_base` permite:

- preencher latitude/longitude dos furos com base na localização do projeto
- espalhar os furos com coordenadas próximas para testes mais realistas
- reforçar a base de materiais das empresas com itens de drilling, mecânica, serralharia, segurança e escritório
- correr em modo de simulação antes de gravar alterações

---

## Gate pré-release

Antes de publicar ou criar release, usar o gate único de validação:

```bash
make pre-release-gate
```

Ou diretamente:

```bash
./.venv/bin/python3 manage.py url_hygiene_gate --strict
```

Este gate valida:

- higiene de URLs (evitar hardcoded em templates/JS/redirects)
- `Django check` para consistência geral

Referência:

- [docs/url_hygiene_checklist.md](/Users/fabiorevez/Desktop/sistema_furacao/docs/url_hygiene_checklist.md:1)

---

## Arranque rápido

### Ambiente local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

### PostgreSQL com Docker

```bash
cp .env.example .env
docker compose up -d
python3 manage.py migrate
python3 manage.py runserver
```

---

## Preparação para servidor (Oracle Cloud)

Checklist recomendado antes do deploy:

```bash
cp .env.example .env
```

Definir no `.env` de produção (obrigatório):

- `DJANGO_SECRET_KEY` forte e única
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS` com domínio/IP real
- `DJANGO_CSRF_TRUSTED_ORIGINS` com URLs HTTPS reais
- `DJANGO_SECURE_SSL_REDIRECT=True`
- `DJANGO_SESSION_COOKIE_SECURE=True`
- `DJANGO_CSRF_COOKIE_SECURE=True`
- `DJANGO_SECURE_HSTS_SECONDS=31536000`
- `DJANGO_USE_X_FORWARDED_PROTO=True`
- `DJANGO_USE_X_FORWARDED_HOST=True`
- `RATE_LIMIT_TRUST_X_FORWARDED_FOR=True` apenas com reverse proxy que controle `X-Forwarded-For`
- `DJANGO_CACHE_BACKEND` e `DJANGO_CACHE_LOCATION` para cache partilhada de rate limiting entre workers
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

Comandos de validação e preparação:

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py check --deploy
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py collectstatic --noinput
```

Script operacional assistido:

```bash
DRY_RUN=1 bash deploy/deploy_operacional.sh
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt bash deploy/deploy_operacional.sh
```

Por defeito o script corre em `DRY_RUN=1`, mostrando os comandos sem os executar. Para produção, confirmar backup e variáveis de ambiente antes de usar `DRY_RUN=0`.
Rollback automático fica desligado por defeito; se for necessário, configurar `ROLLBACK_ON_ERROR=1` e `ROLLBACK_CMD` com um plano validado antes da janela de deploy.

Rotação de logs no servidor:

```bash
sudo cp deploy/logrotate/sistema_furacao /etc/logrotate.d/sistema_furacao
sudo logrotate -d /etc/logrotate.d/sistema_furacao
```

Backups operacionais e teste de restore:

```bash
DRY_RUN=1 bash deploy/backup_operacional.sh
DRY_RUN=0 BACKUP_DIR=/var/backups/sistema_furacao bash deploy/backup_operacional.sh
DRY_RUN=0 RESTORE_TEST_DB=sistema_furacao_restore_test bash deploy/restore_test_operacional.sh
sudo cp deploy/systemd/sf-backup-operacional.* deploy/systemd/sf-restore-test-operacional.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sf-backup-operacional.timer sf-restore-test-operacional.timer
```

Alertas de disponibilidade e erros 5xx:

```bash
DRY_RUN=1 bash deploy/monitor_disponibilidade.sh
DRY_RUN=0 BASE_URL=https://sistemafuracao.pt MAX_5XX_RESPONSES=5 bash deploy/monitor_disponibilidade.sh
sudo cp deploy/systemd/sf-monitor-disponibilidade.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sf-monitor-disponibilidade.timer
```

Para envio de alertas, configurar `SLACK_WEBHOOK_URL` e/ou `ALERT_EMAIL`; o timer corre a cada 5 minutos e respeita `ALERT_COOLDOWN_SECONDS`.

Notas importantes:

- em produção, usar `gunicorn` + reverse proxy (Nginx/Caddy), não `runserver`
- validar uploads, login e páginas críticas após deploy
- manter backup da base de dados antes de cada atualização
- ficheiros base para produção no repositório:
  - `deploy/systemd/sistema_furacao.service`
  - `deploy/nginx/sistema_furacao.conf.example`
  - `docs/deploy_producao.md`

---

## Estrutura funcional resumida

- `plataforma/`
  - empresas, planos, subscrições e perfis de acesso
- `projetos/`
  - operação principal, 3D, materiais, máquinas, analytics e relatórios
- `geologia/`
  - logs geológicos, drone DJI, Drone S_F e missões
- `inspecao_ai/`
  - análise visual, chatbox, preparação de datasets e evolução futura para modelos treinados/preditivos
- `knowledge_base/`
  - documentos técnicos e funcionais para continuidade
- `website/`
  - páginas públicas, autenticação e registo

---

## O que foi acrescentado nesta fase

- centro `DJI Mini 4 Pro` com bridge externa, live view, mapa e comandos
- interface própria `Drone S_F`
- modelos de drone próprio, sensores, módulos e configuração
- operação S_F com mapa, comandos, bridge e missões programadas
- motor automático de missões programadas
- análise visual AI
- chatbox AI com dados reais da empresa
- base documental para continuidade e consulta futura
- reforço dos relatórios, exportações e interoperabilidade 3D
- refinamento do 3D do furo, incluindo tubos, conexões e controlos

---

## Próximo foco

### Prioridade imediata

- evolução da área de `Projetos`
- evolução da camada de `IA`

### Para continuar mais tarde

- retoma da integração `DJI` com fonte real
- retoma do `Drone S_F` quando existir hardware real
- aprofundar a interoperabilidade 3D e análise automática

---

## Validação rápida

```bash
python3 manage.py check
```

---

## Autor

Desenvolvido por **Fabio Revez**  
Focado na ligação entre **tecnologia, operação, geologia, perfuração e IA**

---

## Contribuição

Sugestões, melhorias e integrações são bem-vindas.
