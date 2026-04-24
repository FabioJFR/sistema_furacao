(() => {
    const tipoConta = document.getElementById("id_tipo_conta");
    const empresaWrap = document.getElementById("empresaNomeWrap");
    const funcaoWrap = document.getElementById("funcaoWrap");
    const especialidadeWrap = document.getElementById("especialidadeWrap");

    function atualizarCampos() {
        const isIndividual = tipoConta && tipoConta.value === "individual";
        if (empresaWrap) empresaWrap.style.display = isIndividual ? "none" : "";
        if (funcaoWrap) funcaoWrap.style.display = isIndividual ? "none" : "";
        if (especialidadeWrap) especialidadeWrap.style.display = isIndividual ? "" : "none";
    }

    if (tipoConta) {
        tipoConta.addEventListener("change", atualizarCampos);
        atualizarCampos();
    }
})();
