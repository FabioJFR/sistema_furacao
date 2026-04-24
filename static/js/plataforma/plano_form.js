(() => {
    const form = document.querySelector(".card form");
    const tipoField = document.getElementById("id_tipo");
    const limiteEmpregados = document.getElementById("id_limite_empregados");
    const limiteProjetos = document.getElementById("id_limite_projetos");
    const permiteMultiplos = document.getElementById("id_permite_multiplos_utilizadores");
    const acessoDashboardEmpresa = document.getElementById("id_acesso_dashboard_empresa");
    const precoMensal = document.getElementById("id_preco_mensal");
    const precoAnual = document.getElementById("id_preco_anual");
    const periodo1 = document.getElementById("id_periodos_cobranca_disponiveis_0");
    const periodo3 = document.getElementById("id_periodos_cobranca_disponiveis_1");
    const periodo6 = document.getElementById("id_periodos_cobranca_disponiveis_2");
    const periodo12 = document.getElementById("id_periodos_cobranca_disponiveis_3");
    const companyOnlyContainers = document.querySelectorAll("[data-company-only-field]");
    const campoPrecoMensal = document.querySelector("[data-price-field='mensal']");
    const campoPrecoAnual = document.querySelector("[data-price-field='anual']");

    function atualizarCamposPorTipo() {
        const isIndividual = tipoField?.value === "individual";

        companyOnlyContainers.forEach((container) => {
            container.classList.toggle("field-disabled", isIndividual);
        });

        if (limiteEmpregados) {
            limiteEmpregados.disabled = isIndividual;
            if (isIndividual) {
                limiteEmpregados.value = 0;
            }
        }

        if (limiteProjetos) {
            limiteProjetos.disabled = isIndividual;
            if (isIndividual) {
                limiteProjetos.value = 0;
            }
        }

        if (permiteMultiplos) {
            permiteMultiplos.disabled = isIndividual;
            if (isIndividual) {
                permiteMultiplos.checked = false;
            }
        }

        if (acessoDashboardEmpresa) {
            acessoDashboardEmpresa.disabled = isIndividual;
            if (isIndividual) {
                acessoDashboardEmpresa.checked = false;
            }
        }
    }

    function atualizarCamposDeCobranca() {
        const mensalAtivo = !!(periodo1?.checked || periodo3?.checked || periodo6?.checked);
        const anualAtivo = !!periodo12?.checked;

        if (campoPrecoMensal) {
            campoPrecoMensal.classList.toggle("field-disabled", !mensalAtivo);
        }
        if (campoPrecoAnual) {
            campoPrecoAnual.classList.toggle("field-disabled", !anualAtivo);
        }

        if (precoMensal) {
            precoMensal.disabled = !mensalAtivo;
        }

        if (precoAnual) {
            precoAnual.disabled = !anualAtivo;
        }
    }

    tipoField?.addEventListener("change", atualizarCamposPorTipo);
    [periodo1, periodo3, periodo6, periodo12].forEach((elemento) => {
        elemento?.addEventListener("change", atualizarCamposDeCobranca);
    });

    form?.addEventListener("submit", () => {
        if (tipoField?.value === "individual") {
            if (limiteEmpregados) {
                limiteEmpregados.disabled = false;
                limiteEmpregados.value = 0;
            }
            if (limiteProjetos) {
                limiteProjetos.disabled = false;
                limiteProjetos.value = 0;
            }
            if (permiteMultiplos) {
                permiteMultiplos.disabled = false;
                permiteMultiplos.checked = false;
            }
            if (acessoDashboardEmpresa) {
                acessoDashboardEmpresa.disabled = false;
                acessoDashboardEmpresa.checked = false;
            }
        }

        if (precoMensal) {
            precoMensal.disabled = false;
        }
        if (precoAnual) {
            precoAnual.disabled = false;
        }
    });

    atualizarCamposPorTipo();
    atualizarCamposDeCobranca();
})();
