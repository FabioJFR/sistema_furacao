(() => {
    if (typeof window.Plotly === "undefined") {
        return;
    }
    const config = document.getElementById("furo-3d-empregado-config");
    if (!config) {
        return;
    }

    const medicoes = JSON.parse(document.getElementById("medicoes-data")?.textContent || "[]");
    const trajetoriaPlaneada = JSON.parse(document.getElementById("trajetoria-planeada-data")?.textContent || "{}");
    const configuracaoVisual = JSON.parse(document.getElementById("configuracao-visual-data")?.textContent || "{}");
    const toggleDogleg = document.getElementById("toggleDogleg");
    const doglegThreshold = document.getElementById("doglegThreshold");
    const doglegThresholdValue = document.getElementById("doglegThresholdValue");
    const alertFilter = document.getElementById("alertFilter");
    const depthMin = document.getElementById("depthMin");
    const depthMax = document.getElementById("depthMax");
    const depthMinValue = document.getElementById("depthMinValue");
    const depthMaxValue = document.getElementById("depthMaxValue");
    const estadoAviso = document.getElementById("estadoAviso");
    const viewMode = document.getElementById("viewMode");
    const finalOffsetValue = document.getElementById("finalOffsetValue");
    const finalIncDiffValue = document.getElementById("finalIncDiffValue");
    const finalAziDiffValue = document.getElementById("finalAziDiffValue");
    const topDoglegsList = document.getElementById("topDoglegsList");
    const exportPngBtn = document.getElementById("exportPngBtn");
    const printSummaryBtn = document.getElementById("printSummaryBtn");
    const plannedIncReference = parseFloat(config.dataset.plannedIncReference || "0") || 0;
    const plannedAziReference = parseFloat(config.dataset.plannedAziReference || "0") || 0;
    const filenamePrefix = config.dataset.filenamePrefix || "furo-3d";
    const emptyVisibleText = config.dataset.emptyVisibleText || "Sem pontos visíveis no intervalo atual.";

    const x = [];
    const y = [];
    const z = [];
    const text = [];
    const customdata = [];
    const doglegValues = [];

    function interpolarPontoPorProfundidade(targetDepth) {
        if (!customdata.length || !x.length) return null;
        if (targetDepth <= parseFloat(customdata[0]?.[0] || 0)) {
            return [x[0], y[0], z[0]];
        }
        const lastDepth = parseFloat(customdata[customdata.length - 1]?.[0] || 0);
        if (targetDepth >= lastDepth) {
            return [x[x.length - 1], y[y.length - 1], z[z.length - 1]];
        }
        for (let idx = 1; idx < customdata.length; idx += 1) {
            const d1 = parseFloat(customdata[idx - 1]?.[0] || 0);
            const d2 = parseFloat(customdata[idx]?.[0] || 0);
            if (d2 <= d1) continue;
            if (targetDepth <= d2) {
                const ratio = (targetDepth - d1) / (d2 - d1);
                return [
                    x[idx - 1] + ((x[idx] - x[idx - 1]) * ratio),
                    y[idx - 1] + ((y[idx] - y[idx - 1]) * ratio),
                    z[idx - 1] + ((z[idx] - z[idx - 1]) * ratio),
                ];
            }
        }
        return [x[x.length - 1], y[y.length - 1], z[z.length - 1]];
    }

    function construirTracesTubo() {
        if (!medicoes.length || !x.length) return [];
        const comprimentoPadrao = parseFloat(configuracaoVisual.comprimento_tubo || 3.0) || 3.0;
        const comprimentoFrontal = parseFloat(configuracaoVisual.comprimento_frontal || 0.0) || 0.0;
        const profundidadeFinal = parseFloat(customdata[customdata.length - 1]?.[0] || 0);
        if (profundidadeFinal <= 0) return [];

        const limites = [0];
        if (comprimentoFrontal > 0) limites.push(Math.min(comprimentoFrontal, profundidadeFinal));
        let cursor = limites[limites.length - 1];
        while (cursor < profundidadeFinal) {
            cursor = Math.min(cursor + comprimentoPadrao, profundidadeFinal);
            if (cursor > limites[limites.length - 1]) limites.push(cursor);
        }

        const tracesTubo = [];
        const juntas = [];
        let tuboRegularNumero = 0;

        for (let idx = 1; idx < limites.length; idx += 1) {
            const mdInicio = limites[idx - 1];
            const mdFim = limites[idx];
            const inicio = interpolarPontoPorProfundidade(mdInicio);
            const fim = interpolarPontoPorProfundidade(mdFim);
            if (!inicio || !fim) continue;

            const frontal = idx === 1 && comprimentoFrontal > 0;
            const tuboNumero = frontal ? null : (tuboRegularNumero += 1);
            const rotulo = frontal ? "Conjunto de fundo" : `Tubo número ${tuboNumero}`;
            tracesTubo.push({
                x: [inicio[0], fim[0]],
                y: [inicio[1], fim[1]],
                z: [inicio[2], fim[2]],
                mode: "lines",
                type: "scatter3d",
                name: "Tubo do furo",
                line: {
                    width: frontal ? 12 : 9,
                    color: frontal ? "#f59e0b" : (idx % 2 === 0 ? "#38bdf8" : "#0ea5e9")
                },
                customdata: [[mdInicio, tuboNumero || 0], [mdFim, tuboNumero || 0]],
                hovertemplate:
                    `${rotulo}<br>` +
                    (frontal
                        ? `Comprimento do conjunto de fundo: ${(mdFim - mdInicio).toFixed(2)} m<br>`
                        : `Troço do tubo: ${mdInicio.toFixed(2)} m → ${mdFim.toFixed(2)} m<br>`) +
                    "Medida do furo neste ponto: %{customdata[0]:.2f} m<br>" +
                    "Este: %{x:.2f} m<br>" +
                    "Norte: %{y:.2f} m<br>" +
                    "TVD: %{z:.2f} m<br>" +
                    "<extra></extra>",
                showlegend: idx === 1,
            });

            if (idx < limites.length - 1) {
                juntas.push({
                    ponto: fim,
                    md: mdFim,
                    tuboNumero,
                    proximoTubo: frontal ? 1 : tuboNumero + 1,
                    rotuloAtual: rotulo,
                    rotuloProximo: frontal ? "Tubo número 1" : `Tubo número ${tuboNumero + 1}`,
                    inicio,
                    fim,
                });
            }
        }

        if (juntas.length) {
            juntas.forEach((junta) => {
                const [x0, y0, z0] = junta.inicio;
                const [x1, y1, z1] = junta.fim;
                const [px, py, pz] = junta.ponto;
                const dx = x1 - x0;
                const dy = y1 - y0;
                const dz = z1 - z0;
                let perpX = dy;
                let perpY = -dx;
                let perpZ = 0;
                let perpNorm = Math.sqrt((perpX ** 2) + (perpY ** 2) + (perpZ ** 2));
                if (perpNorm < 1e-6) {
                    perpX = -dz;
                    perpY = 0;
                    perpZ = dx;
                    perpNorm = Math.sqrt((perpX ** 2) + (perpY ** 2) + (perpZ ** 2));
                }
                if (perpNorm < 1e-6) {
                    perpX = 1;
                    perpY = 0;
                    perpZ = 0;
                    perpNorm = 1;
                }
                const factor = 1.25 / perpNorm;
                const offX = perpX * factor * 0.5;
                const offY = perpY * factor * 0.5;
                const offZ = perpZ * factor * 0.5;
                const data = [junta.md];
                tracesTubo.push({
                    x: [px - offX, px + offX],
                    y: [py - offY, py + offY],
                    z: [pz - offZ, pz + offZ],
                    mode: "lines",
                    type: "scatter3d",
                    name: "Tubo do furo",
                    line: { width: 9, color: "#ffffff" },
                    customdata: [data, data],
                    hovertemplate:
                        "Conexão entre tubos<br>" +
                        `Medida do furo neste ponto: ${junta.md.toFixed(2)} m<br>` +
                        `Conexão entre ${junta.rotuloAtual} e ${junta.rotuloProximo}<br>` +
                        "Este: %{x:.2f} m<br>" +
                        "Norte: %{y:.2f} m<br>" +
                        "TVD: %{z:.2f} m<br>" +
                        "<extra></extra>",
                    showlegend: false,
                });
            });
        }
        return tracesTubo;
    }

    function classificarDogleg(valor) {
        if (valor >= 6) return "CRÍTICO";
        if (valor >= 3) return "ATENÇÃO";
        return "OK";
    }

    function calcularDogleg(prev, current) {
        if (!prev) return 0;
        const inc1 = (parseFloat(prev.inclinacao_real_medida || 0) * Math.PI) / 180;
        const inc2 = (parseFloat(current.inclinacao_real_medida || 0) * Math.PI) / 180;
        const azi1 = (parseFloat(prev.azimute_real_medido || 0) * Math.PI) / 180;
        const azi2 = (parseFloat(current.azimute_real_medido || 0) * Math.PI) / 180;
        const md1 = parseFloat(prev.profundidade_medida || 0);
        const md2 = parseFloat(current.profundidade_medida || 0);
        const deltaMd = Math.max(Math.abs(md2 - md1), 0.0001);
        const cosDogleg = (Math.sin(inc1) * Math.sin(inc2) * Math.cos(azi2 - azi1)) + (Math.cos(inc1) * Math.cos(inc2));
        const angulo = Math.acos(Math.min(1, Math.max(-1, cosDogleg)));
        return (angulo * 180 / Math.PI) * (30 / deltaMd);
    }

    medicoes.forEach((medicao, index) => {
        const profundidade = parseFloat(medicao.profundidade_medida || 0);
        const inclinacao = parseFloat(medicao.inclinacao_real_medida || 0);
        const azimute = parseFloat(medicao.azimute_real_medido || 0);
        const radInc = inclinacao * Math.PI / 180;
        const radAzi = azimute * Math.PI / 180;
        const dx = profundidade * Math.cos(radInc) * Math.sin(radAzi);
        const dy = profundidade * Math.cos(radInc) * Math.cos(radAzi);
        const dz = -profundidade * Math.sin(radInc);
        const dogleg = calcularDogleg(medicoes[index - 1], medicao);
        const estado = classificarDogleg(dogleg);
        x.push(dx);
        y.push(dy);
        z.push(dz);
        doglegValues.push(dogleg);
        customdata.push([profundidade, inclinacao, azimute, dogleg, estado]);
        text.push(`Prof: ${profundidade}m | Inc: ${inclinacao} | Azi: ${azimute} | Dogleg: ${dogleg.toFixed(2)}`);
    });

    const maxDogleg = doglegValues.length ? Math.max(...doglegValues) : 0;
    if (doglegThreshold) {
        doglegThreshold.max = Math.max(maxDogleg, 0).toFixed(2);
    }

    const traces = [];
    if (Array.isArray(trajetoriaPlaneada.x) && trajetoriaPlaneada.x.length) {
        traces.push({
            x: trajetoriaPlaneada.x,
            y: trajetoriaPlaneada.y,
            z: trajetoriaPlaneada.z,
            mode: "lines",
            type: "scatter3d",
            name: "Trajetória planeada",
            line: { width: 6, color: "#f59e0b", dash: "dash" },
            hovertemplate: "Trajetória planeada<extra></extra>"
        });
    }
    if (medicoes.length) {
        traces.push(...construirTracesTubo());
        traces.push({
            x,
            y,
            z,
            text,
            customdata,
            mode: "lines+markers",
            type: "scatter3d",
            name: "Trajetória real",
            line: { width: 6, color: "#2563eb" },
            marker: {
                size: 6,
                color: doglegValues,
                colorscale: [[0, "green"], [0.5, "yellow"], [1, "red"]],
                showscale: true,
                colorbar: { title: "Dogleg", len: 0.65, thickness: 12 }
            },
            hovertemplate: "%{text}<extra></extra>"
        });
    }

    const layout = {
        margin: { l: 0, r: 0, b: 0, t: 10 },
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        scene: {
            bgcolor: "#f8fafc",
            xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            dragmode: "orbit",
            camera: { eye: { x: 1.35, y: 1.35, z: 0.95 } }
        }
    };

    window.Plotly.newPlot("plot-3d", traces, layout, {
        responsive: true,
        displaylogo: false,
        scrollZoom: true,
        plotGlPixelRatio: 2,
    }).then((plot) => {
        const realTraceIndex = plot.data.findIndex((trace) => trace.name === "Trajetória real");
        const originalDoglegColors = realTraceIndex >= 0 ? [...plot.data[realTraceIndex].marker.color] : [];
        const originalCustomdata = realTraceIndex >= 0 ? [...plot.data[realTraceIndex].customdata] : [];
        const originalTrace = realTraceIndex >= 0 ? {
            x: [...plot.data[realTraceIndex].x],
            y: [...plot.data[realTraceIndex].y],
            z: [...plot.data[realTraceIndex].z],
            text: [...plot.data[realTraceIndex].text]
        } : null;

        function applyCamera(view) {
            const cameras = {
                iso: { eye: { x: 1.5, y: 1.5, z: 1.2 } },
                top: { eye: { x: 0.01, y: 0.01, z: 2.8 } },
                side: { eye: { x: 2.5, y: 0.1, z: 0.5 } },
                front: { eye: { x: 0.1, y: 2.5, z: 0.5 } }
            };
            window.Plotly.relayout(plot, { "scene.camera": cameras[view] || cameras.iso });
        }

        function toggleTrace(name, visible) {
            plot.data.forEach((trace, index) => {
                if (trace.name === name) {
                    window.Plotly.restyle(plot, { visible: visible ? true : "legendonly" }, [index]);
                }
            });
        }

        function setCheckboxValueByTrace(name, checked) {
            const input = document.querySelector(`input[data-trace-name="${name}"]`);
            if (input) input.checked = checked;
        }

        function applyViewMode(mode) {
            const isReal = mode === "real";
            const isPlaneado = mode === "planeado";
            const isComparacao = mode === "comparacao";
            const visibilityMap = {
                "Trajetória real": isReal || isComparacao,
                "Trajetória planeada": isPlaneado || isComparacao,
            };
            Object.entries(visibilityMap).forEach(([name, visible]) => {
                toggleTrace(name, visible);
                setCheckboxValueByTrace(name, visible);
            });
        }

        function applyDoglegStyles() {
            if (realTraceIndex < 0) return;
            const enabled = !!toggleDogleg?.checked;
            const threshold = parseFloat(doglegThreshold?.value || "0");
            const mode = alertFilter?.value || "todos";
            const minDepth = parseFloat(depthMin?.value || "0");
            const maxDepth = parseFloat(depthMax?.value || "0");
            const filteredX = [];
            const filteredY = [];
            const filteredZ = [];
            const filteredText = [];
            const filteredCustomdata = [];
            const filteredColors = [];
            const filteredOpacities = [];
            const filteredSizes = [];

            originalDoglegColors.forEach((dogleg, idx) => {
                const state = (originalCustomdata[idx] && originalCustomdata[idx][4]) || "OK";
                const depth = parseFloat((originalCustomdata[idx] && originalCustomdata[idx][0]) || 0);
                let visible = dogleg >= threshold && depth >= minDepth && depth <= maxDepth;
                if (mode === "atencao") visible = visible && (state === "ATENÇÃO" || state === "CRÍTICO");
                if (mode === "critico") visible = visible && state === "CRÍTICO";
                if (visible && originalTrace) {
                    filteredX.push(originalTrace.x[idx]);
                    filteredY.push(originalTrace.y[idx]);
                    filteredZ.push(originalTrace.z[idx]);
                    filteredText.push(originalTrace.text[idx]);
                    filteredCustomdata.push(originalCustomdata[idx]);
                    filteredColors.push(originalDoglegColors[idx]);
                    filteredOpacities.push(1);
                    filteredSizes.push(7);
                }
            });

            const lineMode = filteredX.length > 1 ? "lines+markers" : "markers";
            if (enabled) {
                window.Plotly.restyle(plot, {
                    x: [filteredX],
                    y: [filteredY],
                    z: [filteredZ],
                    text: [filteredText],
                    customdata: [filteredCustomdata],
                    mode: lineMode,
                    "marker.color": [filteredColors],
                    "marker.colorscale": [[0, "green"], [0.5, "yellow"], [1, "red"]],
                    "marker.showscale": true,
                    "marker.opacity": [filteredOpacities],
                    "marker.size": [filteredSizes]
                }, [realTraceIndex]);
            } else {
                window.Plotly.restyle(plot, {
                    x: [filteredX],
                    y: [filteredY],
                    z: [filteredZ],
                    text: [filteredText],
                    customdata: [filteredCustomdata],
                    mode: lineMode,
                    "marker.color": "#16a34a",
                    "marker.colorscale": null,
                    "marker.showscale": false,
                    "marker.opacity": [filteredOpacities],
                    "marker.size": [filteredSizes]
                }, [realTraceIndex]);
            }

            if (doglegThresholdValue) doglegThresholdValue.textContent = threshold.toFixed(2);
            if (depthMinValue) depthMinValue.textContent = minDepth.toFixed(2);
            if (depthMaxValue) depthMaxValue.textContent = maxDepth.toFixed(2);
            updateComparisonSummary(filteredX, filteredY, filteredZ, filteredCustomdata);
            updateTopDoglegs(filteredCustomdata);
        }

        function updateComparisonSummary(filteredX, filteredY, filteredZ, filteredCustomdata) {
            if (!finalOffsetValue || !finalIncDiffValue || !finalAziDiffValue) return;
            if (!filteredX.length) {
                finalOffsetValue.textContent = "-";
                finalIncDiffValue.textContent = "-";
                finalAziDiffValue.textContent = "-";
                return;
            }

            const lastIndex = filteredX.length - 1;
            const realX = filteredX[lastIndex];
            const realY = filteredY[lastIndex];
            const realZ = filteredZ[lastIndex];
            const realData = filteredCustomdata[lastIndex] || [];
            const realMd = parseFloat(realData[0] || 0);
            const realInc = parseFloat(realData[1] || 0);
            const realAzi = parseFloat(realData[2] || 0);

            const plannedTraceIndex = plot.data.findIndex((trace) => trace.name === "Trajetória planeada");
            const plannedTrace = plannedTraceIndex >= 0 ? plot.data[plannedTraceIndex] : null;
            if (!plannedTrace || !plannedTrace.x || !plannedTrace.x.length) {
                finalOffsetValue.textContent = "-";
                finalIncDiffValue.textContent = `${Math.abs(realInc - plannedIncReference).toFixed(2)}°`;
                finalAziDiffValue.textContent = `${Math.abs(realAzi - plannedAziReference).toFixed(2)}°`;
                return;
            }

            let bestIndex = 0;
            let bestDistanceMd = Infinity;
            plannedTrace.x.forEach((_, idx) => {
                const mdEstimate = idx * (realMd / Math.max(plannedTrace.x.length - 1, 1));
                const distanceMd = Math.abs(mdEstimate - realMd);
                if (distanceMd < bestDistanceMd) {
                    bestDistanceMd = distanceMd;
                    bestIndex = idx;
                }
            });

            const planX = plannedTrace.x[bestIndex];
            const planY = plannedTrace.y[bestIndex];
            const planZ = plannedTrace.z[bestIndex];
            const offset = Math.sqrt(((realX - planX) ** 2) + ((realY - planY) ** 2) + ((realZ - planZ) ** 2));
            finalOffsetValue.textContent = `${offset.toFixed(2)} m`;
            finalIncDiffValue.textContent = `${Math.abs(realInc - plannedIncReference).toFixed(2)}°`;
            finalAziDiffValue.textContent = `${Math.abs(realAzi - plannedAziReference).toFixed(2)}°`;
        }

        function updateTopDoglegs(filteredCustomdata) {
            if (!topDoglegsList) return;
            if (!filteredCustomdata.length) {
                topDoglegsList.innerHTML = emptyVisibleText;
                return;
            }
            const topItems = filteredCustomdata
                .map((item) => ({
                    md: parseFloat(item[0] || 0),
                    inc: parseFloat(item[1] || 0),
                    azi: parseFloat(item[2] || 0),
                    dogleg: parseFloat(item[3] || 0),
                    estado: item[4] || "OK",
                }))
                .sort((a, b) => b.dogleg - a.dogleg)
                .slice(0, 5);

            topDoglegsList.innerHTML = topItems.map((item, index) => `
                <div class="emp3d-topdogleg-item">
                    <div class="emp3d-topdogleg-title">#${index + 1} · MD ${item.md.toFixed(2)} m</div>
                    <div class="emp3d-topdogleg-sub">Dogleg ${item.dogleg.toFixed(2)} °/30m · ${item.estado}</div>
                    <div class="emp3d-topdogleg-meta">Inc ${item.inc.toFixed(2)}° · Azi ${item.azi.toFixed(2)}°</div>
                </div>
            `).join("");
        }

        document.querySelectorAll("input[data-trace-name]").forEach((input) => {
            input.addEventListener("change", (event) => toggleTrace(event.target.dataset.traceName, event.target.checked));
        });
        document.querySelectorAll("button[data-camera]").forEach((button) => {
            button.addEventListener("click", () => applyCamera(button.dataset.camera));
        });

        exportPngBtn?.addEventListener("click", () => {
            window.Plotly.downloadImage(plot, {
                format: "png",
                filename: filenamePrefix,
                width: 1600,
                height: 900,
                scale: 2
            });
        });
        printSummaryBtn?.addEventListener("click", () => window.print());
        viewMode?.addEventListener("change", (event) => applyViewMode(event.target.value));
        toggleDogleg?.addEventListener("change", applyDoglegStyles);
        doglegThreshold?.addEventListener("input", applyDoglegStyles);
        alertFilter?.addEventListener("change", applyDoglegStyles);
        depthMin?.addEventListener("input", () => {
            if (parseFloat(depthMin.value) > parseFloat(depthMax.value)) depthMax.value = depthMin.value;
            applyDoglegStyles();
        });
        depthMax?.addEventListener("input", () => {
            if (parseFloat(depthMax.value) < parseFloat(depthMin.value)) depthMin.value = depthMax.value;
            applyDoglegStyles();
        });
        applyDoglegStyles();
        applyViewMode(viewMode?.value || "comparacao");

        plot.on("plotly_click", (data) => {
            const ponto = data.points[0];
            const custom = ponto.customdata || [];
            const estado = custom[4];
            if (!estado || !estadoAviso) return;
            estadoAviso.style.display = "block";
            if (estado === "CRÍTICO") {
                estadoAviso.style.background = "#ef4444";
                estadoAviso.style.color = "#fff";
                estadoAviso.innerText = "⚠️ Dogleg crítico neste ponto.";
            } else if (estado === "ATENÇÃO") {
                estadoAviso.style.background = "#facc15";
                estadoAviso.style.color = "#1e293b";
                estadoAviso.innerText = "⚠️ Dogleg em atenção neste ponto.";
            } else {
                estadoAviso.style.background = "#22c55e";
                estadoAviso.style.color = "#fff";
                estadoAviso.innerText = "✅ Ponto dentro dos limites esperados.";
            }
        });
    });
})();
