(function () {
    const form = document.querySelector("[data-geologia-drone-import-form]");
    if (!form) {
        return;
    }

    const summary = form.querySelector("[data-drone-import-summary]");
    const furoField = form.querySelector("#id_furo");
    const fileField = form.querySelector("#id_ficheiro_metadados");
    const titleField = form.querySelector("#id_titulo");

    function updateSummary() {
        const partes = [];

        if (furoField && furoField.selectedOptions.length > 0) {
            const selected = furoField.selectedOptions[0];
            if (selected.value) {
                partes.push("Furo: " + selected.textContent.trim());
            }
        }

        if (fileField && fileField.files.length > 0) {
            partes.push("Ficheiro: " + fileField.files[0].name);
        }

        if (titleField && titleField.value.trim()) {
            partes.push("Titulo: " + titleField.value.trim());
        }

        summary.textContent = partes.length ? partes.join(" | ") : "Aguardando selecao de furo e ficheiro.";
    }

    [furoField, fileField, titleField].forEach(function (field) {
        if (!field) {
            return;
        }
        field.addEventListener("change", updateSummary);
        field.addEventListener("input", updateSummary);
    });

    updateSummary();
})();
