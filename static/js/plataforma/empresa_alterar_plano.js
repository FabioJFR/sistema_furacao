(() => {
    const planoSelect = document.querySelector("select[name='plano']");
    const periodoSelect = document.getElementById("ciclo_subscricao");

    function atualizarPeriodosDisponiveis() {
        const option = planoSelect?.selectedOptions?.[0];
        const periodos = (option?.dataset.periodos || "1,12").split(",").filter(Boolean);

        Array.from(periodoSelect.options).forEach((periodoOption) => {
            const permitido = periodos.includes(periodoOption.value);
            periodoOption.hidden = !permitido;
            periodoOption.disabled = !permitido;
        });

        const atual = periodoSelect.value;
        const atualPermitido = periodos.includes(atual);
        if (!atualPermitido && periodos.length) {
            periodoSelect.value = periodos[0];
        }
    }

    planoSelect?.addEventListener("change", atualizarPeriodosDisponiveis);
    atualizarPeriodosDisponiveis();
})();
