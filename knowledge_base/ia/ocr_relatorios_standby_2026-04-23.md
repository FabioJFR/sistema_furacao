# OCR Relatórios AI: ponto de retoma

Estado atual: `standby`
Data de pausa: `2026-04-23`
Foco imediato do projeto: `colocar online o que já está utilizável e testar`

## Objetivo desta frente

Melhorar a análise AI de relatórios de trabalhador e caixas de amostra, com especial foco em:
- segmentação correta do relatório
- leitura de texto impresso e manuscrito
- associação futura do relatório ao furo certo
- criação de uma base progressiva para aprendizagem e validação humana

## O que já estava a ser feito

### 1. Análise estrutural dos relatórios

A AI deixou de tratar o relatório como um bloco único e passou a segmentar por zonas mais próximas do impresso real:
- `Faixa superior impressa`
- `Área superior esquerda - Cliente`
- `Área superior esquerda - Estaleiro`
- `Área superior esquerda - Sondagem Nº`
- `Área superior esquerda - Inclinação`
- `Área superior esquerda - Perfil no turno`
- `Área superior direita - Data`
- `Área superior direita - Turno`
- `Área superior direita - No início`
- `Área superior direita - No final`
- `Área superior direita - Avanço do turno`
- `Área superior direita - Testemunho recuperado`
- `Área superior direita - % de recuperação`
- `Área central - coluna Tempos`
- `Área central - coluna Parâmetros`
- `Área central - Furação - Início`
- `Área central - Furação - Fim`
- `Área central - Furação - Avanço`
- `Área central - Furação - Tarolo / descrição`
- `Área central do relatório - Bloco 1`
- `Zona inferior do relatório - nomes e assinatura`
- `Rodapé impresso do relatório`

### 2. Trabalho em cima dos metadados

Fomos analisando várias execuções através dos `metadados` da análise, em especial:
- `ocr_aceite`
- `ocr_motivo`
- `ocr_variant`
- `ocr_confianca`
- `ocr_componentes`
- `ocr_linhas`
- `campo_semantico`
- `campo_impresso`
- `valor_preenchido_trabalhador`
- `texto_ocr_estimado`

Isto permitiu perceber a diferença entre:
- segmentação correta da zona
- leitura heurística com ruído
- falso positivo
- rejeição honesta quando a leitura ainda não é fiável

## Resultados que estávamos a obter

### Ganhos claros

- a estrutura do relatório já ficou muito melhor identificada
- o motor já localiza muito melhor topo esquerdo, topo direito e área central
- os subcampos de `Furação` passaram a estar separados
- deixámos de aceitar muito lixo como texto válido em vários campos
- a análise ficou mais honesta: melhor rejeitar do que inventar leitura

### Problemas ainda ativos

- a leitura literal do manuscrito continua fraca
- muitos campos curtos ainda devolvem ruído visual
- `Tempos`, `Parâmetros` e `Observações` continuam difíceis
- o OCR heurístico ainda não está forte para:
  - horas tipo `19:30`
  - métricas com vírgula tipo `198,50`
  - códigos tipo `SS23456`
  - percentagens tipo `82%`
  - manuscrito corrido na área central

### Metadados e evolução recente

Em fases anteriores havia muitos falsos positivos, por exemplo:
- texto ruidoso aceite como `Estaleiro`
- texto ruidoso aceite como `Furação - Início`
- campos curtos com `M`, `N`, `%`, `º` a passar como leitura válida

Depois das últimas melhorias:
- `Estaleiro` deixou de ser aceite falsamente
- `Furação - Início` deixou de ser aceite falsamente
- a validação de campos curtos ficou mais dura
- a AI está mais prudente e mais correta na rejeição

## Melhorias que estávamos a implementar

### Motor OCR / heurísticas

- rejeição forte de falsos positivos em campos curtos
- normalização semântica por campo:
  - `data`
  - `inclinação`
  - `sondagem`
  - profundidades
  - `% recuperação`
  - `perfil`
- OCR por variantes de pré-processamento:
  - `claro`
  - `base`
  - `forte`
  - `contraste`
- leitura por linhas nas observações manuscritas
- validação semântica mais rígida para:
  - campos textuais
  - campos numéricos
  - subcampos de furação

### Interface de detalhe da análise

- reorganização da página
- imagens mais perto do topo
- `Estado` e `Contexto` lado a lado
- `Texto extraído / leitura estimada` por baixo
- explicação curta junto de cada secção
- controlos visuais locais:
  - zoom
  - contraste
  - brilho
- `Resumo AI do relatório`
- associação visível ao `furo` para futura ligação operacional

### Reprocessamento

- o botão de reprocessar passou a criar uma análise nova
- a análise antiga fica intacta
- isto permite comparar a evolução do motor sobre a mesma foto

### Validação humana

- campos podem ser corrigidos manualmente
- a interface mostra:
  - `AI acertou`
  - `AI falhou`
  - `Sem validação`
- existe dashboard de aprendizagem com:
  - taxa global
  - taxa por tipo de documento
  - taxa por campo
  - ranking de campos problemáticos

## O que fizemos agora antes da pausa

### Seleção em duas fases na criação da análise

Ao criar uma nova análise, a interface passou a permitir:

1. `Fase 1`
- selecionar a zona total do relatório na foto

2. `Fase 2`
- criar vários retângulos onde a AI vai tentar interpretar texto
- cada retângulo pode ser:
  - criado
  - nomeado
  - guardado

Também foi acrescentado:
- lista dos retângulos guardados por baixo da foto
- possibilidade de editar um retângulo guardado
- possibilidade de remover um retângulo guardado

### Retângulos / zonas personalizadas

As zonas personalizadas ficam guardadas nos `metadados` da análise e o motor já as usa como:
- áreas nomeadas de leitura
- zonas adicionais para OCR
- contexto explícito no resultado

### Redimensionamento

Foi acrescentada a base para redimensionar retângulos diretamente na imagem com pegas nos cantos.

Nota importante:
- `o redimensionamento dos retângulos ainda não foi testado em uso real`

### Memória de zonas

Foi também criada a base para guardar presets reutilizáveis de zonas:
- por empresa
- por tipo de documento

Esses presets permitem:
- guardar a moldura do relatório
- guardar as zonas nomeadas
- reutilizar mais tarde noutras análises

## Estado real desta frente no momento da pausa

### Já está razoavelmente bem

- estrutura da análise
- segmentação por zonas
- interface de revisão
- validação humana
- reprocessamento
- associação futura ao furo
- desenho de retângulos personalizados
- presets de zonas guardáveis

### Ainda precisa de trabalho antes de ser “forte”

- OCR de horas
- OCR de números com vírgula
- leitura real da tabela de furação
- leitura de manuscrito na área central
- deteção fiável de texto impresso + valor manuscrito no mesmo campo
- teste real do redimensionamento dos retângulos
- teste real dos presets de zonas guardadas

## Melhor próximo passo quando retomarmos

Sequência sugerida:

1. validar em uso real:
- redimensionamento dos retângulos
- guardar/aplicar presets

2. melhorar OCR especializado para:
- horas
- profundidades
- percentagens
- códigos curtos

3. evoluir leitura da tabela de furação por linhas

4. melhorar associação final do relatório ao furo e gerar resumo estruturado pronto a guardar

## Decisão atual

Esta frente fica deliberadamente em `standby`.

Motivo:
- já existe base técnica suficiente para retomar mais tarde sem perder contexto
- agora o foco do projeto deve passar para:
  - colocar a plataforma online
  - testar o que já está utilizável
  - consolidar `Projetos` e `IA` disponível
