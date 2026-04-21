document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("[data-geologia-log-form]");
    if (!form) {
        return;
    }

    const intervaloDe = form.querySelector("#id_intervalo_de");
    const intervaloAte = form.querySelector("#id_intervalo_ate");
    const titulo = form.querySelector("#id_titulo");
    const preview = form.querySelector("[data-intervalo-preview]");

    function atualizarPreview() {
        if (!intervaloDe || !intervaloAte || !preview) {
            return;
        }

        const inicio = intervaloDe.value || "-";
        const fim = intervaloAte.value || "-";
        preview.textContent = `${inicio} m -> ${fim} m`;

        if (intervaloDe.value && intervaloAte.value && Number(intervaloAte.value) < Number(intervaloDe.value)) {
            preview.dataset.estado = "erro";
            preview.textContent = "Fim do intervalo inferior ao inicio.";
            return;
        }

        preview.dataset.estado = "ok";
    }

    function preencherTituloSeVazio() {
        if (!titulo || titulo.value.trim() || !intervaloDe || !intervaloAte) {
            return;
        }

        if (intervaloDe.value && intervaloAte.value) {
            titulo.value = `Intervalo ${intervaloDe.value}m - ${intervaloAte.value}m`;
        }
    }

    [intervaloDe, intervaloAte].forEach(function (campo) {
        if (!campo) {
            return;
        }

        campo.addEventListener("input", function () {
            atualizarPreview();
            preencherTituloSeVazio();
        });
    });

    atualizarPreview();
});

