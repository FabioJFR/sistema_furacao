# Pasta PDF

Esta pasta serve como biblioteca documental de apoio para ficheiros que a AI deve conhecer.

## Regra recomendada

Formatos textuais podem ser lidos diretamente.

Exemplos de leitura direta neste ambiente:

- `.md`
- `.txt`
- `.json`
- `.csv`
- `.log`
- `.yaml`
- `.yml`
- `.xml`
- `.html`
- `.ini`
- `.cfg`

Para formatos não textuais, guardar também um `.txt` com o mesmo nome.

Exemplo:

- `relatorio_geotecnico.pdf`
- `relatorio_geotecnico.txt`

## Motivo

Neste ambiente, a AI consegue:

- listar documentos existentes
- usar diretamente ficheiros textuais suportados
- usar um `.txt` auxiliar de formatos não textuais como base de consulta textual

Isto significa que, para perguntas detalhadas sobre um PDF, o melhor caminho atual é:

1. colocar o documento
2. se for não textual, colocar um `TXT` com o texto extraído ou resumo fiel

Assim a AI pode consultar esse conteúdo de forma muito mais útil e estável.
