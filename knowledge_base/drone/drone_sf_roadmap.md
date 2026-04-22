# Drone S_F - Estado Atual e Retoma Futura

## Estado desta frente

Esta área fica preparada para continuar mais tarde, mas o foco imediato da plataforma passa para:

- Projetos
- IA

O desenvolvimento do `Drone S_F` não está abandonado. Fica apenas em pausa estratégica até voltarmos a ter hardware real, tempo para testes e prioridade operacional para esta frente.

## O que já ficou construído

- Interface própria `Drone S_F`, separada da área `DJI`
- Modelos base do drone, módulos, sensores e configuração
- Operação em tempo real própria
- Bridge S_F separada da bridge DJI
- Mapa operacional S_F
- Fila de comandos S_F
- Missões programadas S_F com:
  - frequência diária, semanal e pontual
  - checklist de ações
  - repetição automática
  - execução manual
  - edição e remoção
- Motor de processamento de missões programadas
- Quadro de estado do motor com histórico e filtros

## O que falta para uma retoma séria

- Drone físico próprio
- Sensores reais ligados a hardware
- Telemetria real do Drone S_F
- Validação de segurança da execução automática
- Integração com fluxo real de vídeo/live view
- Ensaios no terreno

## Próximo caminho quando retomarmos esta área

1. Validar arquitetura final do hardware do Drone S_F
2. Definir controladora de voo, companion computer e sensores reais
3. Ligar telemetria real à bridge S_F
4. Ligar vídeo/snapshot reais
5. Testar missões automáticas com hardware
6. Integrar AI com sensores e leitura embarcada

## Melhorias futuras já identificadas

- Histórico mais rico das missões executadas
- Relatórios automáticos por missão
- Estados de missão mais detalhados
- Simulação offline de voo e sensores
- Planeador visual de missões no mapa
- Regras de segurança e geofencing próprio
- Integração com análises AI geológicas e deteção de eventos

## Nota estratégica

Até existir hardware próprio e janela real de testes, o desenvolvimento principal deve concentrar-se em:

- melhorar a gestão de projetos
- reforçar a camada de IA
- preparar a plataforma para receber dados técnicos no futuro

## Ponto de retoma

Quando voltarmos a esta frente, o ponto natural de continuação é:

`Interface Drone S_F` -> `Operação S_F` -> `bridge S_F` -> telemetria e sensores reais.
