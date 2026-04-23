# Base Funcional da Plataforma

Este documento resume a estrutura funcional atual da plataforma para consulta interna e pela AI.

## Núcleo atual

A plataforma já tem várias frentes utilizáveis:

- `Plataforma`
  - gestão global de empresas
  - planos
  - subscrições
  - finanças
  - exports técnicos
  - gestão de features por entidade
- `Projetos`
  - projetos
  - furos
  - medições
  - registos diários
  - fotos de amostra
  - despesas
  - dashboards operacionais
- `Geologia`
  - hub geológico
  - logs geológicos
  - integração DJI
  - interface Drone S_F
- `AI`
  - AI visual
  - chatbox
  - memória operacional
  - OCR experimental
- `Dispositivos`
  - dashboard de dispositivos
  - sessões
  - leituras brutas
  - survey shots

## Estado do produto

O estado atual do produto está orientado para:

- colocar online o que já está estável
- testar operação real
- recolher feedback e dados
- manter em standby controlado o que ainda não tem hardware ou OCR suficientemente robusto

## Áreas já maduras o suficiente para uso real

- gestão multiempresa
- gestão de projetos e furos
- dashboards base
- exportação de dados
- memória operacional da AI
- permissões principais
- gestão superuser

## Áreas que exigem prudência

- OCR de relatórios manuscritos
- leitura profunda de documentos complexos
- integração viva com drones
- automações dependentes de hardware externo

## Permissões e controlo

Atualmente a plataforma já distingue:

- `superuser`
- `platform_owner`
- `platform_admin`
- `empresa_admin`
- `empresa_gestor`
- `empregado`
- `individual`

Existe também uma camada nova de `features` para ativar ou desativar módulos por:

- empresa
- conta individual

## Direção imediata

O foco imediato recomendado para a plataforma é:

1. estabilizar o que já existe
2. preparar ambiente online
3. validar permissões reais por perfil
4. testar dados e fluxos principais
5. recolher feedback antes de abrir novas frentes complexas
