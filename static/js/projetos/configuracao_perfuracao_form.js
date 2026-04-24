(() => {
    const numero = (name) => {
        const el = document.querySelector(`[name="${name}"]`);
        if (!el || el.value === "") {
            return 0;
        }
        const value = parseFloat(el.value);
        return Number.isFinite(value) ? value : 0;
    };

    const inteiro = (name) => {
        const el = document.querySelector(`[name="${name}"]`);
        if (!el || el.value === "") {
            return 0;
        }
        const value = parseInt(el.value, 10);
        return Number.isFinite(value) ? value : 0;
    };

    const atualizarTotal = () => {
        const totalConjuntoFundo =
            (numero("comprimento_karoutier") * inteiro("quantidade_karoutier")) +
            (numero("comprimento_acrescento") * inteiro("quantidade_acrescento")) +
            (numero("comprimento_calibrador") * inteiro("quantidade_calibrador")) +
            (numero("comprimento_record") * inteiro("quantidade_record")) +
            numero("comprimento_bit");

        const totalTuboInterior =
            numero("comprimento_caixa_mola") +
            (numero("comprimento_tubo_interior") * inteiro("quantidade_tubo_interior")) +
            (numero("comprimento_acrescento_tubo_interior") * inteiro("quantidade_acrescento_tubo_interior")) +
            numero("comprimento_cabeca_interior");

        const alvoConjuntoFundo = document.getElementById("total-conjunto-fundo-preview");
        if (alvoConjuntoFundo) {
            alvoConjuntoFundo.textContent = `${totalConjuntoFundo.toFixed(2)} m`;
        }

        const alvoTuboInterior = document.getElementById("total-tubo-interior-preview");
        if (alvoTuboInterior) {
            alvoTuboInterior.textContent = `${totalTuboInterior.toFixed(2)} m`;
        }
    };

    document.querySelectorAll("input, select").forEach((el) => {
        el.addEventListener("input", atualizarTotal);
        el.addEventListener("change", atualizarTotal);
    });

    atualizarTotal();
})();
