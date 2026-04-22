# Relatorio Tecnico

## Drone proprio integrado com a plataforma

Data: 22/04/2026

Este documento resume a especificacao recomendada para um drone proprio pensado para:
- geologia e levantamento de campo
- fotogrametria e captacao visual
- integracao com a plataforma interna
- crescimento futuro para sensores adicionais
- instalacao de software e sensores especializados para operacoes geologicas

## Objetivo do sistema

O drone deve ser concebido como uma plataforma aberta, modular e integravel com o software da empresa. O foco principal nao e apenas voar e captar imagem, mas permitir:
- telemetria aberta
- missões e waypoints
- captacao de imagem e video com metadados
- importacao pos-voo e, mais tarde, integracao em tempo real
- manutencao simples em campo
- instalacao de software proprio
- integracao com sensores extra sem redesenhar o drone de raiz

## Requisitos base

- arquitetura aberta, preferencialmente baseada em ArduPilot ou PX4
- telemetria em protocolo aberto, idealmente MAVLink
- autonomia real alvo entre 25 e 40 minutos
- payload util entre 600 g e 1.5 kg
- gimbal estabilizado
- camera principal real 4K ou superior
- GPS confiavel, bussola, barometro e fail-safe
- capacidade de registo de missao, log de voo e retorno seguro
- possibilidade de adicionar RTK, termica, multiespectral ou LiDAR leve
- barramento e energia disponiveis para sensores de proximidade, som e modulos geologicos adicionais
- companion computer com capacidade para correr software proprio da plataforma

## Requisito adicional obrigatorio

O drone deve ter capacidade de expansao para:
- sensores de proximidade
- sensores acusticos / som
- sensores ambientais e geologicos adicionais
- software proprio instalado localmente no sistema embarcado

Isto significa que o projeto deve prever logo de inicio:
- volume interno para eletronica adicional
- margem de energia
- portas de comunicacao livres
- companion computer suficientemente forte
- arquitetura modular para montagem e substituicao de sensores

## Versoes recomendadas

### 1. Versao economica de prototipo

Indicada para:
- testes de integracao com a plataforma
- validacao de telemetria
- treino operacional
- primeiras capturas RGB

Limites:
- menor robustez em vento
- menor autonomia com payload
- menor margem para sensores adicionais

### 2. Versao robusta operacional

Indicada para:
- operacao regular em campo
- missões de geologia e levantamento visual
- maior confiabilidade mecanica e eletrica

Vantagens:
- melhor estabilidade
- maior autonomia real
- melhor capacidade de manutencao e substituicao modular

### 3. Versao fotogrametria/geologia

Indicada para:
- mapeamento
- ortomosaicos
- modelos 3D
- integracao com sensores especificos

Vantagens:
- camera superior
- melhor gimbal
- possibilidade de RTK e computacao embarcada mais forte

## Lista de componentes recomendada

### A. Estrutura e propulsao

1. Frame quadcopter 450 a 650 mm
- preferencia por frame em carbono
- bracos substituiveis
- espaco para companion computer e distribuicao limpa de cabos

2. Motores brushless compativeis com o frame e payload
- escolher por par motor/helice/ESC, nao isoladamente
- preferencia por motores com boa disponibilidade de pecas

3. ESCs de qualidade
- preferencia por ESCs 4-em-1 ou individuais conforme manutencao pretendida
- margem termica adequada para operacao com carga

4. Helices
- pelo menos dois jogos completos suplentes
- helices equilibradas e de dimensao adequada ao frame

5. Sistema de distribuicao de energia
- PDB ou equivalente
- protecao e organizacao para bateria, ESCs e modulos auxiliares

### B. Controlo de voo

6. Controlador de voo
- recomendacao: Pixhawk ou equivalente compativel com ArduPilot/PX4
- IMU estavel
- suporte forte da comunidade

7. GPS + bussola
- modulo externo de qualidade
- montagem afastada de interferencia eletromagnetica

8. Barometro e sensores internos do FC
- proteger de turbulencia e vibracao

9. Modulo de telemetria
- idealmente MAVLink por radio, Wi-Fi ou outro meio compatível com a bridge

10. Radio controlo
- sistema fiavel e com boa latencia
- fail-safe configuravel

### C. Energia

11. Baterias LiPo ou Li-Ion adequadas ao perfil do drone
- numero minimo recomendado: 3 a 6 baterias
- registo de ciclos e manutencao preventiva

12. Carregador balanceado
- carregamento seguro
- suporte para o tipo de bateria escolhido

13. Medicao de tensao e corrente
- essencial para autonomia real e seguranca

### D. Captacao e imagem

14. Gimbal de 3 eixos
- importante para video estavel e fotogrametria consistente

15. Camera principal RGB
- minimo realista: 4K real
- ideal: sensor 1/2 polegada ou superior
- boa nitidez, bitrate util e controlo de exposicao

16. Armazenamento local
- cartoes/memoria fiavel
- fluxo claro para descarregar media e logs

17. Camera secundaria ou expansao futura
- opcional para termica, multiespectral ou inspeccao

### E. Computacao embarcada

18. Companion computer
- Raspberry Pi 5, Jetson Orin Nano ou equivalente
- funcao: ponte entre drone e plataforma
- capaz de correr software proprio de aquisicao, integracao e automacao geologica

19. Sistema operativo e servicos
- Linux
- servico local para:
  - recolha de telemetria
  - logs
  - frames
  - envio para a bridge/plataforma
- instalacao de software adicional para:
  - leitura de sensores
  - deteccao de proximidade
  - captacao e analise de som
  - automacoes geologicas futuras

20. Armazenamento local de logs e cache
- importante para recuperar dados se a ligacao falhar

### F. Comunicacoes e integracao

21. Protocolo de telemetria aberta
- recomendacao: MAVLink

22. Modulo de rede
- Wi-Fi, LTE/5G ou radio dedicado conforme o caso

23. Bridge de integracao com a plataforma
- envio de:
  - posicao
  - altitude
  - velocidade
  - heading
  - bateria
  - estado de missao
  - imagem/snapshot

24. Fluxo pos-voo
- importacao de:
  - log de voo
  - ortomosaico
  - modelo 3D
  - relatorio

25. Barramentos e portas para expansao
- UART
- USB
- I2C
- SPI, se necessario
- GPIOs protegidos e organizados

### G. Sensores e crescimento futuro

26. Sensores de proximidade
- para apoio a navegacao, seguranca e operacao perto de estruturas
- ultrassonicos, lidar de proximidade ou sensores equivalentes

27. Sensores de som
- microfones ou modulos acusticos para recolha e analise de eventos sonoros
- uteis se no futuro houver deteccao de anomalias, ambiente ou operacao assistida

28. Sensores geologicos adicionais
- espaço e interface para acoplar sensores especificos definidos mais tarde
- por exemplo ambientais, termicos ou outros modulos cientificos

29. RTK opcional
- util para missões de maior precisao

30. Sensor termico opcional
- util em certos cenarios de inspeccao

31. Sensor multiespectral opcional
- util se houver evolucao para analise mais tecnica de superficie

32. LiDAR leve opcional
- apenas em configuracoes superiores

### H. Seguranca e manutencao

33. Fail-safe e return-to-home
- obrigatorio

34. Protecao de cablagem e vibracoes
- essencial para fiabilidade

35. Inventario de pecas sobressalentes
- helices
- motores
- ESCs
- landing gear
- parafusos
- conectores

36. Mala de transporte e organizacao de campo
- importante para operacao diaria

## Stack de software recomendada

- ArduPilot ou PX4
- MAVLink
- companion service em Python/Go/Node
- bridge local para a plataforma
- importacao pos-voo diretamente para geologia

## Comparacao com drones fechados baratos

Um drone barato de marketplace pode servir como:
- brinquedo
- treino
- prototipo muito inicial de voo

Mas nao e a melhor base para:
- integracao profunda com a plataforma
- manutencao profissional
- fiabilidade de campo
- telemetria aberta
- escalabilidade para sensores

## Requisitos regulatorios e operacionais

Em Portugal/UE, o sistema deve ser pensado considerando:
- regras da EASA para categoria open ou especifica
- registo do operador na ANAC quando aplicavel
- limites de altura e operacao visual
- conformidade futura se o sistema crescer para operacoes mais exigentes

## Recomendacao final

Recomendacao principal:
- nao comprar um drone fechado barato como base central do projeto
- desenhar um drone proprio modular com stack aberta
- comecar por uma versao robusta operacional
- manter o fluxo pos-voo e preparar integracao em tempo real para a fase seguinte

## Lista curta de compra recomendada para primeiro prototipo

- frame em carbono 450 a 650 mm
- 4 motores brushless adequados
- 4 ESCs ou 1 ESC 4-em-1 de qualidade
- conjunto de helices principal + suplentes
- Pixhawk ou equivalente
- GPS + bussola externos
- radio controlo fiavel
- modulo telemetria
- 3 a 6 baterias
- carregador balanceado
- gimbal 3 eixos
- camera RGB 4K real
- companion computer
- portas e cablagem para expansao de sensores
- sensor de proximidade base
- modulo acustico base, se a carga util o permitir
- armazenamento local
- kit de sobressalentes

## Proximo passo tecnico

O proximo passo recomendado e produzir uma BOM completa em tres variantes:
- economica
- robusta
- fotogrametria/geologia

e depois mapear:
- componentes
- peso total
- autonomia prevista
- custo estimado
- integracao com a plataforma
