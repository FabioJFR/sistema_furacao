# Inventário de CSS Inline

Levantamento inicial de templates com maior volume de CSS inline (blocos de estilo e `style=""`).

## Top templates por volume (prioridade)

1. `projetos/templates/projetos/graficos_dashboard.html` (`208`)
2. `projetos/templates/projetos/dashboard.html` (`84`)
3. `projetos/templates/projetos/material_detail.html` (`57`)
4. `projetos/templates/projetos/analytics_eventos.html` (`49`)
5. `projetos/templates/projetos/maquina_detail.html` (`27`)
6. `projetos/templates/projetos/furo_3d.html` (`24`)
7. `plataforma/templates/plataforma/onboarding_empresa.html` (`23`)
8. `projetos/templates/projetos/material_list.html` (`20`)
9. `projetos/templates/projetos/form.html` (`18`)
10. `plataforma/templates/plataforma/empresa_alterar_plano.html` (`17`)

## Já migrado nesta fase

- `website/templates/website/home.html` -> `static/css/website/home.css`
- `website/templates/website/login.html` -> `static/css/website/login.css`
- `website/templates/website/registo.html` -> `static/css/website/registo.css`
- `website/templates/website/planos.html` -> `static/css/website/planos.css`
- `plataforma/templates/plataforma/features_dashboard.html` -> `static/css/plataforma/features_dashboard.css`

## Critério de migração

- mover estilos globais para `static/css/<app>/...`
- substituir `style=""` por classes sem alterar layout
- manter nomes previsíveis por página (`dashboard.css`, `*_detail.css`, etc.)

## Comando de levantamento rápido

```bash
rg -n "<[s]tyle|style=\"" projetos/templates plataforma/templates geologia/templates inspecao_ai/templates website/templates -S
```
