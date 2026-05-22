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
    const tiposContaContexto = JSON.parse(document.getElementById("tipos-conta-contexto-data")?.textContent || "{}");
    const accountCards = document.querySelectorAll("[data-account-card]");
    const accountGuideTitle = document.getElementById("account-guide-title");
    const accountGuideLabel = document.getElementById("account-guide-label");
    const accountGuideDescription = document.getElementById("account-guide-description");
    const accountGuideChecklist = document.getElementById("account-guide-checklist");
    const planGuideBox = document.getElementById("plan-guide-box");
    const planGuideTitle = document.getElementById("plan-guide-title");
    const planGuideMessage = document.getElementById("plan-guide-message");

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

        atualizarGuiaTipoConta();
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

    function atualizarGuiaTipoConta() {
        const tipo = tipoContaSelect?.value || "empresa";
        const contexto = tiposContaContexto[tipo];
        if (!contexto) {
            return;
        }

        accountCards.forEach((card) => {
            card.classList.toggle("is-active", card.dataset.accountCard === tipo);
        });

        if (accountGuideTitle) {
            accountGuideTitle.textContent = contexto.titulo;
        }
        if (accountGuideLabel) {
            accountGuideLabel.textContent = contexto.label;
        }
        if (accountGuideDescription) {
            accountGuideDescription.textContent = contexto.descricao;
        }
        if (accountGuideChecklist) {
            accountGuideChecklist.innerHTML = "";
            (contexto.checklist || []).forEach((item) => {
                const li = document.createElement("li");
                li.textContent = item;
                accountGuideChecklist.appendChild(li);
            });
        }
    }

    function atualizarGuiaPlano() {
        if (!planoGuideBox || !planGuideTitle || !planGuideMessage || !planoSelect) {
            return;
        }

        const plano = planosContexto[planoSelect.value];
        if (!plano) {
            planGuideBox.classList.remove("is-trial", "is-paid");
            planGuideTitle.textContent = "Plano selecionado";
            planGuideMessage.textContent = "Seleciona um plano para veres aqui o enquadramento comercial e o comportamento inicial da conta.";
            return;
        }

        const isTrial = (plano.preco_mensal === "0" || plano.preco_mensal === "0.00")
            && (plano.preco_anual === "0" || plano.preco_anual === "0.00");

        planGuideBox.classList.toggle("is-trial", isTrial);
        planGuideBox.classList.toggle("is-paid", !isTrial);
        planGuideTitle.textContent = `${plano.nome} · ${plano.trial_badge || (isTrial ? "Trial / prova" : "Plano comercial")}`;
        planGuideMessage.textContent = plano.trial_message || "Plano selecionado.";
    }

    tipoContaSelect?.addEventListener("change", atualizarFormulario);
    accountCards.forEach((card) => {
        card.addEventListener("click", () => {
            if (!tipoContaSelect) {
                return;
            }
            tipoContaSelect.value = card.dataset.accountCard;
            atualizarFormulario();
        });
    });
    planoSelect?.addEventListener("change", () => {
        atualizarPeriodosDisponiveis();
        atualizarValorSubscricao();
        atualizarGuiaPlano();
    });
    periodoSelect?.addEventListener("change", atualizarValorSubscricao);

    atualizarFormulario();
    atualizarPeriodosDisponiveis();
    atualizarValorSubscricao();
    atualizarGuiaPlano();
})();
