(() => {
    const wrapper = document.querySelector("[data-financeiro-preview]");
    if (!wrapper) {
        return;
    }

    const custoClienteInput = document.getElementById("id_financeiro-custo_por_metro_cliente");
    const outrosInput = document.getElementById("id_financeiro-outros_valores_gastos_associados");
    if (!custoClienteInput || !outrosInput) {
        return;
    }

    const totalMetros = Number(wrapper.dataset.totalMetros || 0);
    const totalDespesas = Number(wrapper.dataset.totalDespesas || 0);
    const totalMateriais = Number(wrapper.dataset.totalMateriais || 0);
    const gastoFuroBase = Number(wrapper.dataset.gastoFuroBase || 0);
    const gastoMaquinasBase = Number(wrapper.dataset.gastoMaquinasBase || 0);
    const custoEmpresaBase = Number(wrapper.dataset.custoEmpresaBase || 0);
    const cobradoBase = Number(wrapper.dataset.cobradoBase || 0);
    const ganhoFuroBase = Number(wrapper.dataset.ganhoFuroBase || 0);
    const outrosIniciais = Number(wrapper.dataset.outrosIniciais || 0);

    const custoEmpresaEl = wrapper.querySelector("[data-financeiro-custo-empresa]");
    const cobradoEl = wrapper.querySelector("[data-financeiro-cobrado]");
    const ganhoFuroEl = wrapper.querySelector("[data-financeiro-ganho-furo]");
    const gastoFuroEl = wrapper.querySelector("[data-financeiro-gasto-furo]");
    const gastoMateriaisEl = wrapper.querySelector("[data-financeiro-gasto-materiais]");
    const gastoMaquinasEl = wrapper.querySelector("[data-financeiro-gasto-maquinas]");
    const margemTotalEl = wrapper.querySelector("[data-financeiro-margem-total]");
    const margemMetroEl = wrapper.querySelector("[data-financeiro-margem-metro]");

    const formatEuro = (value) => `${Number(value || 0).toFixed(2)} €`;
    const parseInputNumber = (value) => {
        if (value === null || value === undefined || value === "") {
            return 0;
        }
        const normalized = String(value).replace(",", ".");
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const atualizarPreview = () => {
        const custoCliente = parseInputNumber(custoClienteInput.value);
        const outros = parseInputNumber(outrosInput.value);

        const valorCobrado = totalMetros * custoCliente;
        const valorGanhoFuro = valorCobrado;
        const custoEmpresa = totalMetros ? ((totalDespesas + totalMateriais + outros) / totalMetros) : 0;
        const gastoFuro = gastoFuroBase + (outros - outrosIniciais);
        const margemTotal = valorCobrado - gastoFuro;
        const margemMetro = totalMetros ? (margemTotal / totalMetros) : 0;

        if (custoEmpresaEl) custoEmpresaEl.textContent = formatEuro(totalMetros ? custoEmpresa : custoEmpresaBase);
        if (cobradoEl) cobradoEl.textContent = formatEuro(totalMetros ? valorCobrado : cobradoBase);
        if (ganhoFuroEl) ganhoFuroEl.textContent = formatEuro(totalMetros ? valorGanhoFuro : ganhoFuroBase);
        if (gastoFuroEl) gastoFuroEl.textContent = formatEuro(gastoFuro);
        if (gastoMateriaisEl) gastoMateriaisEl.textContent = formatEuro(totalMateriais);
        if (gastoMaquinasEl) gastoMaquinasEl.textContent = formatEuro(gastoMaquinasBase);
        if (margemTotalEl) {
            margemTotalEl.textContent = formatEuro(margemTotal);
            margemTotalEl.style.color = margemTotal < 0 ? "#b91c1c" : "#065f46";
        }
        if (margemMetroEl) {
            margemMetroEl.textContent = formatEuro(margemMetro);
            margemMetroEl.style.color = margemMetro < 0 ? "#b91c1c" : "#065f46";
        }
    };

    custoClienteInput.addEventListener("input", atualizarPreview);
    outrosInput.addEventListener("input", atualizarPreview);
    atualizarPreview();
})();
