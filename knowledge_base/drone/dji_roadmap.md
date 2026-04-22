# DJI - Estado Atual e Retoma Futura

## Estado desta frente

Esta área fica documentada e pronta para retoma futura, mas o foco imediato da plataforma passa para:

- Projetos
- IA

A integração `DJI` não fica abandonada. Fica estabilizada no ponto atual e pausada até existir necessidade operacional real para voltar a desenvolvê-la.

## O que já ficou construído

- Interface `DJI Mini 4 Pro` própria em `Geologia`
- Estado de ligação, live view, mapa operacional e fila de comandos
- Bridge externa para ingestão de heartbeat, logs e comandos
- Histórico da bridge
- Quadro de estado operacional
- Fluxo pós-voo para importação de missões e ficheiros
- Simuladores e ferramentas de bridge/mock/webhook para teste

## Limitação técnica principal

O setup atual com `DJI RC 2` não permite uma integração nativa direta dentro do próprio comando.

Na prática:

- o controlo real continua no `DJI RC 2`
- a plataforma recebe dados através de uma bridge externa
- sem essa ponte intermédia, não existe telemetria real em tempo real dentro do sistema

## O que falta para avançar mais nesta frente

- fonte externa real de telemetria/vídeo
- bridge operacional ligada a fluxo real DJI
- validação de dados reais no terreno
- testes consistentes com missões reais

## Próximo caminho quando retomarmos esta área

1. Confirmar qual será a fonte externa real para dados DJI
2. Ligar essa fonte à bridge existente
3. Validar heartbeat, feed, posição e comandos reais
4. Refinar a operação em campo

## Melhorias futuras já identificadas

- histórico mais completo de voos e comandos
- relatórios automáticos de missão DJI
- melhor ligação entre pós-voo e geologia
- maior automação da importação de ficheiros
- mais diagnósticos visuais da bridge e da fonte externa

## Nota estratégica

Até existir uma ponte real estável para o ecossistema DJI, a plataforma deve concentrar o esforço principal em:

- melhorar a gestão de projetos
- reforçar a camada de IA
- preparar workflows de análise e operação com mais valor imediato

## Ponto de retoma

Quando voltarmos a esta frente, o ponto natural de continuação é:

`Centro Drone DJI Mini 4 Pro` -> bridge externa -> fonte real de dados DJI -> validação operacional em campo.
