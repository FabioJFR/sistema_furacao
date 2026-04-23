# Primeiros Passos no Linear

Este guia assume que nunca trabalhaste com o `Linear`.

## 1. Estrutura mínima recomendada

Cria apenas:

- `1 workspace`
- `1 team`

Nome sugerido da team:

- `S_F Platform`

Não compliques já com várias equipas. Para esta fase, uma equipa única é o melhor caminho.

## 2. Labels recomendadas

Cria estas labels:

- `deploy`
- `mvp`
- `ai`
- `ocr`
- `geologia`
- `drone`
- `plataforma`
- `permissions`
- `data`
- `ux`
- `bug`
- `research`
- `standby`

## 3. Projetos recomendados

Cria estes projetos:

1. `Go Live MVP`
2. `Projetos e Operação`
3. `AI e OCR`
4. `Geologia e Drones`
5. `Plataforma e Permissões`

## 4. Workflow simples

Usa estados simples no início:

- `Backlog`
- `Todo`
- `In Progress`
- `In Review`
- `Done`
- `Paused`

Se não quiseres mexer muito, podes usar o workflow default do Linear e só acrescentar `Paused`.

## 5. Como usar os ficheiros deste diretório

### Opção mais simples

Abre o `linear_backlog_inicial.csv` e cria os tickets manualmente no Linear, um a um, copiando:

- `Title`
- `Description`
- `Priority`
- `Labels`
- `Project`

### Opção mais avançada

Usa o CSV como base para importação através do processo de importação do Linear.

## 6. Prioridade real nesta fase

O foco atual do projeto é:

1. colocar online o que já está utilizável
2. testar com utilizadores reais
3. estabilizar permissões, dados e operação
4. deixar `OCR de relatórios` e `drone próprio` em standby controlado

## 7. O que não deve ser prioridade agora

Não vale a pena gastar demasiado tempo já em:

- automações complexas do Linear
- múltiplas equipas
- ciclos muito rígidos
- dashboards demasiado detalhados

Primeiro precisamos de tração e uso real.

## 8. Rotina semanal recomendada

Uma rotina simples para ti:

1. abrir `Go Live MVP`
2. escolher 3 a 5 issues prioritárias
3. mover para `In Progress`
4. no fim da semana, rever o que ficou em `Done`
5. mover para `Paused` tudo o que ficou conscientemente em espera

## 9. Como tratar áreas em standby

Para frentes como:

- `OCR de relatórios`
- `Drone S_F`
- `integrações DJI mais profundas`

usa:

- label `standby`
- estado `Paused`

Assim não perdes contexto, mas também não poluis o foco principal.
