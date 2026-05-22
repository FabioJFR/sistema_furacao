(() => {
    const planoSelect = document.getElementById("id_plano");
    const periodoSelect = document.getElementById("id_ciclo_subscricao");
    const valorSubscricaoInput = document.getElementById("id_valor_subscricao");
    const criarSubscricaoCheckbox = document.getElementById("id_criar_subscricao_inicial");
    const trialBox = document.getElementById("onb-trial-box");
    const trialTitle = document.getElementById("onb-trial-title");
    const trialMessage = document.getElementById("onb-trial-message");

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

    function atualizarLeituraPlano() {
        if (!trialBox || !trialTitle || !trialMessage) {
            return;
        }

        const planoId = planoSelect.value;
        const precos = planosPrecos[planoId];

        if (!planoId || !precos) {
            trialBox.classList.remove("is-trial", "is-paid");
            trialTitle.textContent = "Plano comercial";
            trialMessage.textContent = "Seleciona um plano para veres aqui se a conta arranca em modo trial/prova ou já em subscrição comercial.";
            return;
        }

        const isTrial = Boolean(precos.is_trial);
        trialBox.classList.toggle("is-trial", isTrial);
        trialBox.classList.toggle("is-paid", !isTrial);
        trialTitle.textContent = isTrial ? "Trial / prova" : "Plano comercial";
        trialMessage.textContent = precos.mensagem_trial;
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
        atualizarLeituraPlano();
    }

    planoSelect.addEventListener("change", atualizarPeriodosDisponiveis);
    periodoSelect.addEventListener("change", atualizarValorSubscricao);

    if (criarSubscricaoCheckbox) {
        criarSubscricaoCheckbox.addEventListener("change", atualizarValorSubscricao);
    }

    atualizarPeriodosDisponiveis();
})();
