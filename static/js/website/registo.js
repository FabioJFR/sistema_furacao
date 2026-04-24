(() => {
    document.querySelectorAll("[data-message-close]").forEach((button) => {
        button.addEventListener("click", () => {
            const message = button.closest("[data-message]");
            if (message) {
                message.remove();
            }
        });
    });

    const tipoContaSelect = document.getElementById("id_tipo_conta");
    const empresaRow = document.getElementById("empresa_row");
    const nomeEmpresaInput = document.getElementById("id_nome_empresa");
    const planoSelect = document.getElementById("id_plano");
    const periodoSelect = document.getElementById("id_ciclo_subscricao");
    const valorSubscricaoInput = document.getElementById("id_valor_subscricao");
    const planosContexto = JSON.parse(document.getElementById("planos-contexto-data")?.textContent || "{}");

    function atualizarFormulario() {
        if (!tipoContaSelect || !empresaRow || !nomeEmpresaInput) {
            return;
        }

        const isEmpresa = tipoContaSelect.value === "empresa";
        empresaRow.style.display = isEmpresa ? "block" : "none";
        nomeEmpresaInput.required = isEmpresa;

        if (!isEmpresa) {
            nomeEmpresaInput.value = "";
        }
    }

    function formatarValor(valor) {
        return Number(valor || 0).toFixed(2);
    }

    function atualizarPeriodosDisponiveis() {
        if (!planoSelect || !periodoSelect) {
            return;
        }

        const plano = planosContexto[planoSelect.value];
        const periodos = (plano?.periodos || [1, 12]).map(String);

        Array.from(periodoSelect.options).forEach((option) => {
            const permitido = periodos.includes(option.value);
            option.hidden = !permitido;
            option.disabled = !permitido;
        });

        if (!periodos.includes(periodoSelect.value) && periodos.length) {
            periodoSelect.value = periodos[0];
        }
    }

    function atualizarValorSubscricao() {
        if (!planoSelect || !periodoSelect || !valorSubscricaoInput) {
            return;
        }

        const plano = planosContexto[planoSelect.value];
        if (!plano) {
            valorSubscricaoInput.value = "";
            return;
        }

        const periodo = Number(periodoSelect.value || 1);
        const precoMensal = Number(plano.preco_mensal || 0);
        const precoAnual = Number(plano.preco_anual || 0);
        const valor = periodo === 12 ? (precoAnual || (precoMensal * 12)) : (precoMensal * periodo);
        valorSubscricaoInput.value = formatarValor(valor);
    }

    tipoContaSelect?.addEventListener("change", atualizarFormulario);
    planoSelect?.addEventListener("change", () => {
        atualizarPeriodosDisponiveis();
        atualizarValorSubscricao();
    });
    periodoSelect?.addEventListener("change", atualizarValorSubscricao);

    atualizarFormulario();
    atualizarPeriodosDisponiveis();
    atualizarValorSubscricao();
})();
