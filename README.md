# Sistema de Gestão de Diamond Drilling

Sistema web em **Django** para gestão operacional de projetos de **diamond drilling**, com foco em operação multiempresa, produção, stock, finanças, geologia, IA, visualização 3D e integração com drones.

---

## Estado atual

- Versão atual: **v0.9.4**
- Estado: **desenvolvimento ativo**
- Foco imediato: **Projetos**, **IA** e **estabilização para produção**

### Stack principal

- **Backend:** Django 6 / Python 3.14
- **Frontend:** HTML, CSS, JavaScript
- **Mapas:** Leaflet
- **Gráficos:** Chart.js
- **Visualização 3D de furos:** Plotly
- **Base de dados:** PostgreSQL

---

## Release 0.9.4 (resumo)

Principais evoluções consolidadas nesta versão:

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

---

## Áreas principais

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

### Materiais, máquinas e finanças

- materiais por empresa, projeto e furo
- stock mínimo e alertas de stock baixo
- máquinas com estados operacionais e alertas
- despesas por empresa, projeto, furo e máquina
- indicadores financeiros e custo por metro

### Analytics e relatórios

- dashboards operacionais e financeiros
- gráficos de produção, despesas e eventos
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
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`

Comandos de validação e preparação:

```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py check --deploy
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py collectstatic --noinput
```

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
  - análise visual, chatbox e integração futura com OCR/AI
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
