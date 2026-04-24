(() => {
    const planoSelect = document.getElementById("id_plano");
    const periodoSelect = document.getElementById("id_ciclo_subscricao");
    const valorSubscricaoInput = document.getElementById("id_valor_subscricao");
    const criarSubscricaoCheckbox = document.getElementById("id_criar_subscricao_inicial");

    if (!planoSelect || !periodoSelect || !valorSubscricaoInput) {
        return;
    }

    const planosPeriodos = JSON.parse(document.getElementById("planos-periodos-data")?.textContent || "{}");
    const planosPrecos = JSON.parse(document.getElementById("planos-precos-data")?.textContent || "{}");

    function formatarValor(valor) {
        return Number(valor || 0).toFixed(2);
    }

    function obterValorCalculado() {
        const planoId = planoSelect.value;
        const periodo = Number(periodoSelect.value || 1);
        const precos = planosPrecos[planoId];

        if (!planoId || !precos) {
            return "";
        }

        const precoMensal = Number(precos.preco_mensal || 0);
        const precoAnual = Number(precos.preco_anual || 0);

        if (periodo === 12) {
            return formatarValor(precoAnual || (precoMensal * 12));
        }

        return formatarValor(precoMensal * periodo);
    }

    function atualizarValorSubscricao() {
        if (criarSubscricaoCheckbox && !criarSubscricaoCheckbox.checked) {
            valorSubscricaoInput.value = "";
            valorSubscricaoInput.setAttribute("aria-disabled", "true");
            return;
        }

        valorSubscricaoInput.value = obterValorCalculado();
        valorSubscricaoInput.removeAttribute("aria-disabled");
    }

    function atualizarPeriodosDisponiveis() {
        const option = planoSelect.selectedOptions?.[0];
        const periodos = (planosPeriodos[option?.value] || [1, 12]).map(String);

        Array.from(periodoSelect.options).forEach((periodoOption) => {
            const permitido = periodos.includes(periodoOption.value);
            periodoOption.hidden = !permitido;
            periodoOption.disabled = !permitido;
        });

        if (!periodos.includes(periodoSelect.value) && periodos.length) {
            periodoSelect.value = periodos[0];
        }

        atualizarValorSubscricao();
    }

    planoSelect.addEventListener("change", atualizarPeriodosDisponiveis);
    periodoSelect.addEventListener("change", atualizarValorSubscricao);

    if (criarSubscricaoCheckbox) {
        criarSubscricaoCheckbox.addEventListener("change", atualizarValorSubscricao);
    }

    atualizarPeriodosDisponiveis();
})();
