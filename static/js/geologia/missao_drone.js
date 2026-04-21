document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("[data-geologia-missao-form]");
    if (!form) {
        return;
    }

    const metadados = form.querySelector("#id_metadados_json");
    const ficheiroMetadados = form.querySelector("#id_ficheiro_metadados");
    const titulo = form.querySelector("#id_titulo");
    const tipoMissao = form.querySelector("#id_tipo_missao");
    const modoCaptura = form.querySelector("#id_modo_captura");
    const fotos = form.querySelector("#id_numero_fotos");
    const videos = form.querySelector("#id_numero_videos");
    const resumo = form.querySelector("[data-missao-resumo]");

    function aplicarDados(dados) {
        if (titulo && !titulo.value.trim() && dados.titulo) {
            titulo.value = dados.titulo;
        }
        if (tipoMissao && !tipoMissao.value.trim() && dados.tipo_missao) {
            tipoMissao.value = dados.tipo_missao;
        }
        if (modoCaptura && !modoCaptura.value.trim() && dados.modo_captura) {
            modoCaptura.value = dados.modo_captura;
        }
        if (fotos && !fotos.value && dados.numero_fotos !== undefined) {
            fotos.value = dados.numero_fotos;
        }
        if (videos && !videos.value && dados.numero_videos !== undefined) {
            videos.value = dados.numero_videos;
        }
    }

    function atualizarResumo() {
        if (!resumo) {
            return;
        }

        const partes = [];
        if (tipoMissao && tipoMissao.value) {
            partes.push(tipoMissao.value);
        }
        if (modoCaptura && modoCaptura.value) {
            partes.push(modoCaptura.value);
        }
        if (fotos && fotos.value) {
            partes.push(`${fotos.value} fotos`);
        }
        if (videos && videos.value) {
            partes.push(`${videos.value} videos`);
        }

        resumo.textContent = partes.join(" · ") || "Sem resumo operacional ainda.";
    }

    if (metadados) {
        metadados.addEventListener("blur", function () {
            if (!metadados.value.trim()) {
                return;
            }

            try {
                const dados = JSON.parse(metadados.value);
                aplicarDados(dados);
            } catch (error) {
                return;
            }

            atualizarResumo();
        });
    }

    if (ficheiroMetadados) {
        ficheiroMetadados.addEventListener("change", function () {
            const ficheiro = ficheiroMetadados.files && ficheiroMetadados.files[0];
            if (!ficheiro) {
                return;
            }

            const reader = new FileReader();
            reader.onload = function () {
                try {
                    const dados = JSON.parse(String(reader.result || ""));
                    aplicarDados(dados);
                    atualizarResumo();
                } catch (error) {
                    return;
                }
            };
            reader.readAsText(ficheiro, "utf-8");
        });
    }

    [tipoMissao, modoCaptura, fotos, videos].forEach(function (campo) {
        if (!campo) {
            return;
        }
        campo.addEventListener("input", atualizarResumo);
    });

    atualizarResumo();
});
