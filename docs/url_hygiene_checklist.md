# URL Hygiene Checklist

Checklist rapido para evitar regressao de URLs hardcoded no projeto.

## 1) Templates Django
- Usar sempre `{% url 'namespace:nome_rota' ... %}` em `href` e `action`.
- Evitar paths literais como `/app/...`, `/plataforma/...`, `/admin/...`.
- Para objetos com URL canónica, preferir `{{ objeto.get_absolute_url }}`.

## 2) Views e Redirects
- Preferir `redirect("namespace:nome_rota", ...)` em vez de `redirect("/path/")`.
- Quando existir objeto com `get_absolute_url`, preferir `redirect(objeto)`.
- Em rotas antigas, criar rota legacy que redireciona para a canónica.

## 3) JavaScript de frontend
- Nao montar URLs de API na mao no JS.
- Injetar endpoints via `data-*` no template e ler no script.
- Se endpoint nao existir, falhar de forma segura (desativar botoes e mostrar erro).

## 4) URLs canónicas por entidade
- Estrutura recomendada: `<uuid>/<slug>/`.
- Manter rota legacy `<uuid>/` com redirecionamento para nao quebrar links antigos.
- Validar slug na view e redirecionar para URL correta quando necessario.

## 5) Rotina de validacao antes de merge
1. Procurar hardcoded:
   - `rg -n "href=\"/(app|plataforma|projetos|admin|logout)|action=\"/(app|plataforma|projetos)" projetos plataforma geologia inspecao_ai static -S`
2. Procurar redirects absolutos:
   - `rg -n "redirect\\(\\s*['\"]/\" projetos plataforma geologia inspecao_ai -S`
3. Correr verificacao Django:
   - `./.venv/bin/python3 manage.py check`
4. Gate unico (recomendado):
   - `make pre-release-gate`
   - ou `./.venv/bin/python3 manage.py url_hygiene_gate --strict`

## 6) Regra de ouro
- Path real pode mudar.
- Nome da rota e `get_absolute_url` devem ser a unica fonte de verdade.
