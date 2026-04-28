(() => {
    const config = document.getElementById("furo-3d-config");
    if (!config || typeof window.Plotly === "undefined") {
        return;
    }

    let plot = null;
    const botaoRotacao = document.getElementById("rotacionarBtn");
    const botaoPrint = document.getElementById("furo-3d-print-btn");
    const aviso = document.getElementById("estadoAviso");
    const modal = document.getElementById("modal");
    const modalCloseButton = document.getElementById("furo-3d-modal-close");
    const toggleDogleg = document.getElementById("toggleDogleg");
    const toggleMarkers = document.getElementById("toggleMarkers");
    const doglegThreshold = document.getElementById("doglegThreshold");
    const doglegThresholdValue = document.getElementById("doglegThresholdValue");
    const alertFilter = document.getElementById("alertFilter");
    const depthMin = document.getElementById("depthMin");
    const depthMax = document.getElementById("depthMax");
    const depthMinValue = document.getElementById("depthMinValue");
    const depthMaxValue = document.getElementById("depthMaxValue");
    const viewMode = document.getElementById("viewMode");
    const finalOffsetValue = document.getElementById("finalOffsetValue");
    const finalIncDiffValue = document.getElementById("finalIncDiffValue");
    const finalAziDiffValue = document.getElementById("finalAziDiffValue");
    const topDoglegsList = document.getElementById("topDoglegsList");
    const quickExportSelect = document.getElementById("quickExportSelect");
    const quickExportBtn = document.getElementById("quickExportBtn");
    const interopSelect = document.getElementById("interopSelect");
    const interopActionBtn = document.getElementById("interopActionBtn");

    const plannedIncReference = parseFloat(config.dataset.plannedIncReference || "0") || 0;
    const plannedAziReference = parseFloat(config.dataset.plannedAziReference || "0") || 0;
    const filenamePrefix = config.dataset.filenamePrefix || "furo-3d";
    const reportPdfUrl = config.dataset.reportPdfUrl || "";
    const importUrl = config.dataset.importUrl || "";
    const exportBaseUrl = config.dataset.exportBaseUrl || "";
    const msgNoPointsVisible = config.dataset.msgNoPointsVisible || "Sem pontos visíveis no intervalo atual.";
    const msgDoglegCritical = config.dataset.msgDoglegCritical || "⚠️ Dogleg crítico neste ponto.";
    const msgDoglegWarning = config.dataset.msgDoglegWarning || "⚠️ Dogleg em atenção neste ponto.";
    const msgDoglegOk = config.dataset.msgDoglegOk || "✅ Ponto dentro dos limites esperados.";
    const msgRotationStart = config.dataset.msgRotationStart || "▶️ Rotação";
    const msgRotationStop = config.dataset.msgRotationStop || "⏸️ Parar rotação";
    const msgTopItemPrefix = config.dataset.msgTopItemPrefix || "MD";
    const msgTopItemDogleg = config.dataset.msgTopItemDogleg || "Dogleg";
    const msgTopItemInc = config.dataset.msgTopItemInc || "Inc";
    const msgTopItemAzi = config.dataset.msgTopItemAzi || "Azi";

    let rotacionando = false;
    let angulo = 0;
    let rotacaoInterval = null;
    let realTraceIndex = null;
    let originalDoglegColors = [];
    let originalCustomdata = [];
    let originalRealTrace = null;
    let plotInitialized = false;
    let lastSceneCamera = null;
    let restoringSceneCamera = false;
    const originalTraceStore = {};
    const originalTraceStoreByIndex = {};
    const cameraToggleState = {
        side: 1,
        front: 1,
        top: 1,
    };

    function toPlainArray(value) {
        if (Array.isArray(value)) return [...value];
        if (value && typeof value.length === "number") {
            try {
                return Array.from(value);
            } catch (error) {
                return [];
            }
        }
        return [];
    }

    function refreshPlotReference() {
        plot = document.querySelector("#grafico .js-plotly-plot, #grafico .plotly-graph-div");
        return !!(plot && Array.isArray(plot.data));
    }

    function cloneCamera(camera) {
        if (!camera || typeof camera !== "object") return null;
        try {
            return JSON.parse(JSON.stringify(camera));
        } catch (error) {
            return null;
        }
    }

    function readCurrentCamera() {
        if (!refreshPlotReference()) return null;
        const camera = plot?.layout?.scene?.camera;
        return cloneCamera(camera);
    }

    function restoreCameraIfNeeded() {
        if (!refreshPlotReference() || !lastSceneCamera || restoringSceneCamera) return;
        restoringSceneCamera = true;
        window.Plotly.relayout(plot, { "scene.camera": cloneCamera(lastSceneCamera) })
            .finally(() => {
                restoringSceneCamera = false;
            });
    }

    function findTraceIndexesByName(name) {
        if (!refreshPlotReference()) return [];
        const indexes = [];
        plot.data.forEach((trace, index) => {
            if (trace.name === name) {
                indexes.push(index);
            }
        });
        return indexes;
    }

    function toggleTrace(name, visible) {
        const indexes = findTraceIndexesByName(name);
        indexes.forEach((index) => {
            window.Plotly.restyle(plot, { visible: [visible] }, [index]);
        });
    }

    function setCheckboxValueByTrace(name, checked) {
        const input = document.querySelector(`input[data-trace-name="${name}"]`);
        if (input) {
            input.checked = checked;
        }
    }

    function getCheckboxValueByTrace(name) {
        const input = document.querySelector(`input[data-trace-name="${name}"]`);
        return input ? !!input.checked : true;
    }

    function syncTraceVisibilityFromControls() {
        if (!refreshPlotReference()) return;
        document.querySelectorAll("input[data-trace-name]").forEach((input) => {
            toggleTrace(input.dataset.traceName, !!input.checked);
        });
        toggleTrace("Planeado até última medição", true);
        toggleTrace("Planeado final", true);
    }

    function getDepthFromCustomdata(item) {
        if (!item) return 0;
        if (Array.isArray(item)) {
            return parseFloat(item[0] || 0);
        }
        return 0;
    }

    function filterStoredTraceByDepth(trace, minDepth, maxDepth) {
        if (!trace) return null;
        const filtered = {
            x: [],
            y: [],
            z: [],
            text: [],
            customdata: [],
        };
        (trace.x || []).forEach((_, idx) => {
            const depth = getDepthFromCustomdata((trace.customdata || [])[idx]);
            if (depth >= minDepth && depth <= maxDepth) {
                filtered.x.push(trace.x[idx]);
                filtered.y.push(trace.y[idx]);
                filtered.z.push(trace.z[idx]);
                if (trace.text) filtered.text.push(trace.text[idx]);
                if (trace.customdata) filtered.customdata.push(trace.customdata[idx]);
            }
        });
        return filtered;
    }

    function applyViewMode(mode) {
        const isReal = mode === "real";
        const isComparacao = mode === "comparacao";
        const visibilityMap = {
            "Trajetória real": isReal || isComparacao,
            "Tubo do furo": isReal || isComparacao,
            "Planeado até última medição": true,
            "Planeado final": true,
            "Origem": true,
            "Vetores de direção": isReal || isComparacao,
        };
        Object.entries(visibilityMap).forEach(([name, visible]) => {
            setCheckboxValueByTrace(name, visible);
        });
        syncTraceVisibilityFromControls();
    }

    function applyCamera(view) {
        if (!refreshPlotReference()) return;
        let camera = { eye: { x: 1.8, y: 1.8, z: 1.2 } };
        if (view === "top") {
            cameraToggleState.top *= -1;
            camera = { eye: { x: 0.01, y: 0.01, z: 2.8 * cameraToggleState.top } };
        } else if (view === "side") {
            cameraToggleState.side *= -1;
            camera = { eye: { x: 2.6 * cameraToggleState.side, y: 0.1, z: 0.5 } };
        } else if (view === "front") {
            cameraToggleState.front *= -1;
            camera = { eye: { x: 0.1, y: 2.6 * cameraToggleState.front, z: 0.5 } };
        }
        window.Plotly.relayout(plot, { "scene.camera": camera });
    }

    function getRealFilteredData() {
        const threshold = parseFloat(doglegThreshold?.value || "0");
        const mode = alertFilter?.value || "todos";
        const minDepth = parseFloat(depthMin?.value || "0");
        const maxDepth = parseFloat(depthMax?.value || "0");
        const markersVisible = toggleMarkers ? !!toggleMarkers.checked : true;
        const filteredX = [];
        const filteredY = [];
        const filteredZ = [];
        const filteredCustomdata = [];
        const filteredText = [];
        const filteredColors = [];
        const filteredOpacities = [];
        const filteredSizes = [];

        originalDoglegColors.forEach((dogleg, idx) => {
            const state = (originalCustomdata[idx] && originalCustomdata[idx][5]) || "OK";
            const depth = parseFloat((originalCustomdata[idx] && originalCustomdata[idx][0]) || 0);
            let visible = dogleg >= threshold && depth >= minDepth && depth <= maxDepth;
            if (mode === "atencao") visible = visible && (state === "ATENÇÃO" || state === "CRÍTICO");
            if (mode === "critico") visible = visible && state === "CRÍTICO";
            if (visible && originalRealTrace) {
                filteredX.push(originalRealTrace.x[idx]);
                filteredY.push(originalRealTrace.y[idx]);
                filteredZ.push(originalRealTrace.z[idx]);
                filteredCustomdata.push(originalCustomdata[idx]);
                filteredText.push(originalRealTrace.text[idx]);
                filteredColors.push(originalDoglegColors[idx]);
                filteredOpacities.push(markersVisible ? 1 : 0);
                filteredSizes.push(markersVisible ? 12 : 0.1);
            }
        });

        return {
            threshold,
            minDepth,
            maxDepth,
            x: filteredX,
            y: filteredY,
            z: filteredZ,
            customdata: filteredCustomdata,
            text: filteredText,
            colors: filteredColors,
            opacities: filteredOpacities,
            sizes: filteredSizes,
            lineMode: filteredX.length > 1 ? "lines+markers" : "markers",
        };
    }

    function applyDepthAndDataFilters() {
        if (!refreshPlotReference() || realTraceIndex === null) return null;
        const cameraBefore = readCurrentCamera();
        const filtered = getRealFilteredData();
        window.Plotly.restyle(plot, {
            x: [filtered.x],
            y: [filtered.y],
            z: [filtered.z],
            text: [filtered.text],
            customdata: [filtered.customdata],
            mode: filtered.lineMode,
            "marker.opacity": [filtered.opacities],
            "marker.size": [filtered.sizes]
        }, [realTraceIndex]);

        const tubeIndexes = findTraceIndexesByName("Tubo do furo");
        if (tubeIndexes.length) {
            tubeIndexes.forEach((tubeIndex) => {
                const tubeTrace = originalTraceStoreByIndex[tubeIndex];
                const filteredTube = filterStoredTraceByDepth(tubeTrace, filtered.minDepth, filtered.maxDepth);
                if (!filteredTube) return;
                window.Plotly.restyle(plot, {
                    x: [filteredTube.x],
                    y: [filteredTube.y],
                    z: [filteredTube.z],
                    customdata: [filteredTube.customdata],
                    text: [filteredTube.text],
                }, [tubeIndex]);
            });
        }

        toggleTrace("Planeado até última medição", true);
        toggleTrace("Planeado final", true);
        toggleTrace("Origem", getCheckboxValueByTrace("Origem"));
        if (cameraBefore) {
            lastSceneCamera = cloneCamera(cameraBefore);
            restoreCameraIfNeeded();
        }
        if (doglegThresholdValue) doglegThresholdValue.textContent = filtered.threshold.toFixed(2);
        if (depthMinValue) depthMinValue.textContent = filtered.minDepth.toFixed(2);
        if (depthMaxValue) depthMaxValue.textContent = filtered.maxDepth.toFixed(2);
        updateComparisonSummary(filtered.x, filtered.y, filtered.z, filtered.customdata);
        updateTopDoglegs(filtered.customdata);
        return filtered;
    }

    function applyDoglegAppearance(filtered = null) {
        if (!refreshPlotReference() || realTraceIndex === null) return;
        const enabled = !!toggleDogleg?.checked;
        const resolved = filtered || getRealFilteredData();
        if (enabled) {
            window.Plotly.restyle(plot, {
                "marker.color": [resolved.colors],
                "marker.colorscale": [[[0, "green"], [0.5, "yellow"], [1, "red"]]],
                "marker.showscale": false,
            }, [realTraceIndex]);
        } else {
            window.Plotly.restyle(plot, {
                "marker.color": ["#22c55e"],
                "marker.colorscale": [null],
                "marker.showscale": false,
            }, [realTraceIndex]);
        }
    }

    function applyDoglegStyles() {
        const filtered = applyDepthAndDataFilters();
        if (filtered) {
            applyDoglegAppearance(filtered);
        }
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

        const plannedIndexes = findTraceIndexesByName("Planeado até última medição");
        const plannedFinalIndexes = findTraceIndexesByName("Planeado final");
        let plannedTrace = plannedIndexes.length ? plot.data[plannedIndexes[0]] : null;
        if (!plannedTrace || !plannedTrace.x || !plannedTrace.x.length) {
            plannedTrace = plannedFinalIndexes.length ? plot.data[plannedFinalIndexes[0]] : null;
        }
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
            topDoglegsList.innerHTML = `<div class="text-sm text-slate-300">${msgNoPointsVisible}</div>`;
            return;
        }
        const topItems = filteredCustomdata
            .map((item) => ({
                md: parseFloat(item[0] || 0),
                inc: parseFloat(item[1] || 0),
                azi: parseFloat(item[2] || 0),
                dogleg: parseFloat(item[3] || 0),
                estado: item[5] || "OK",
            }))
            .sort((a, b) => b.dogleg - a.dogleg)
            .slice(0, 5);

        topDoglegsList.innerHTML = topItems.map((item, index) => `
            <div class="furo-3d-topdogleg-item">
                <div class="furo-3d-topdogleg-title">#${index + 1} · ${msgTopItemPrefix} ${item.md.toFixed(2)} m</div>
                <div class="furo-3d-topdogleg-sub">${msgTopItemDogleg} ${item.dogleg.toFixed(2)} °/30m · ${item.estado}</div>
                <div class="furo-3d-topdogleg-meta">${msgTopItemInc} ${item.inc.toFixed(2)}° · ${msgTopItemAzi} ${item.azi.toFixed(2)}°</div>
            </div>
        `).join("");
    }

    function initializePlotState() {
        if (plotInitialized) return true;
        if (!refreshPlotReference()) return false;
        lastSceneCamera = readCurrentCamera();

        // Defesa extra: garante que nenhum trace mostra colorbar lateral.
        const tracesWithMarker = [];
        plot.data.forEach((trace, index) => {
            if (trace && trace.marker) {
                tracesWithMarker.push(index);
            }
        });
        if (tracesWithMarker.length) {
            window.Plotly.restyle(plot, {
                "marker.showscale": false,
                "marker.colorbar": null
            }, tracesWithMarker);
        }

        realTraceIndex = plot.data.findIndex((trace) => trace.name === "Trajetória real");
        if (realTraceIndex >= 0) {
            originalRealTrace = {
                x: toPlainArray(plot.data[realTraceIndex].x),
                y: toPlainArray(plot.data[realTraceIndex].y),
                z: toPlainArray(plot.data[realTraceIndex].z),
                text: toPlainArray(plot.data[realTraceIndex].text)
            };
            originalDoglegColors = toPlainArray(plot.data[realTraceIndex].marker?.color);
            originalCustomdata = toPlainArray(plot.data[realTraceIndex].customdata);
            ["Origem", "Planeado até última medição", "Planeado final", "Trajetória real", "Tubo do furo"].forEach((traceName) => {
                const traceIndex = plot.data.findIndex((trace) => trace.name === traceName);
                if (traceIndex >= 0 && !originalTraceStore[traceName]) {
                    const trace = plot.data[traceIndex];
                    originalTraceStore[traceName] = {
                        x: toPlainArray(trace.x),
                        y: toPlainArray(trace.y),
                        z: toPlainArray(trace.z),
                        text: toPlainArray(trace.text),
                        customdata: toPlainArray(trace.customdata),
                    };
                }
            });
            plot.data.forEach((trace, traceIndex) => {
                originalTraceStoreByIndex[traceIndex] = {
                    x: toPlainArray(trace.x),
                    y: toPlainArray(trace.y),
                    z: toPlainArray(trace.z),
                    text: toPlainArray(trace.text),
                    customdata: toPlainArray(trace.customdata),
                };
            });
            applyDoglegStyles();
        }

        plot.on("plotly_relayouting", (eventData) => {
            if (eventData && eventData["scene.camera"]) {
                lastSceneCamera = cloneCamera(eventData["scene.camera"]);
            }
        });

        plot.on("plotly_relayout", (eventData) => {
            if (eventData && eventData["scene.camera"]) {
                lastSceneCamera = cloneCamera(eventData["scene.camera"]);
                return;
            }
            if (eventData && eventData["scene.dragmode"]) {
                restoreCameraIfNeeded();
            }
        });

        plot.on("plotly_click", (data) => {
            const ponto = data.points[0];
            const customdata = ponto.customdata || [];
            const imagem = customdata[4];
            const estado = customdata[5];
            if (imagem) {
                const imagemRocha = document.getElementById("imagem_rocha");
                if (imagemRocha) {
                    imagemRocha.src = imagem;
                    if (modal) modal.style.display = "block";
                }
            }
            if (!estado || !aviso) return;
            aviso.style.display = "block";
            if (estado === "CRÍTICO") {
                aviso.style.background = "#ef4444";
                aviso.style.color = "white";
                aviso.innerText = msgDoglegCritical;
            } else if (estado === "ATENÇÃO") {
                aviso.style.background = "#facc15";
                aviso.style.color = "#1e293b";
                aviso.innerText = msgDoglegWarning;
            } else {
                aviso.style.background = "#22c55e";
                aviso.style.color = "white";
                aviso.innerText = msgDoglegOk;
            }
        });

        plotInitialized = true;
        syncTraceVisibilityFromControls();
        return true;
    }

    function bootPlotInteractions(attempt = 0) {
        if (initializePlotState()) {
            applyViewMode(viewMode?.value || "comparacao");
            return;
        }
        if (attempt < 60) {
            window.setTimeout(() => bootPlotInteractions(attempt + 1), 150);
        }
    }

    document.querySelectorAll("input[data-trace-name]").forEach((input) => {
        input.addEventListener("change", (event) => {
            toggleTrace(event.target.dataset.traceName, event.target.checked);
        });
    });
    document.querySelectorAll("button[data-camera]").forEach((button) => {
        button.addEventListener("click", () => applyCamera(button.dataset.camera));
    });

    function downloadPlotPng() {
        if (!refreshPlotReference()) return;
        window.Plotly.downloadImage(plot, {
            format: "png",
            filename: filenamePrefix,
            width: 1600,
            height: 900,
            scale: 2
        });
    }

    quickExportBtn?.addEventListener("click", () => {
        const selected = quickExportSelect?.value || "png";
        if (selected === "png") {
            downloadPlotPng();
            return;
        }
        if (selected === "pdf" && reportPdfUrl) {
            window.location.href = reportPdfUrl;
        }
    });

    interopActionBtn?.addEventListener("click", () => {
        const selected = interopSelect?.value || "zip";
        if (selected === "importar" && importUrl) {
            window.location.href = importUrl;
            return;
        }
        if (exportBaseUrl) {
            window.location.href = exportBaseUrl.replace("/zip/", `/${selected}/`);
        }
    });

    viewMode?.addEventListener("change", (event) => applyViewMode(event.target.value));
    toggleDogleg?.addEventListener("change", applyDoglegStyles);
    toggleMarkers?.addEventListener("change", applyDoglegStyles);
    doglegThreshold?.addEventListener("input", applyDoglegStyles);
    alertFilter?.addEventListener("change", applyDoglegStyles);
    depthMin?.addEventListener("input", () => {
        if (parseFloat(depthMin.value) > parseFloat(depthMax.value)) {
            depthMax.value = depthMin.value;
        }
        applyDoglegStyles();
    });
    depthMax?.addEventListener("input", () => {
        if (parseFloat(depthMax.value) < parseFloat(depthMin.value)) {
            depthMin.value = depthMax.value;
        }
        applyDoglegStyles();
    });

    bootPlotInteractions();

    if (botaoRotacao) {
        botaoRotacao.addEventListener("click", () => {
            if (!refreshPlotReference()) return;
            rotacionando = !rotacionando;
            botaoRotacao.textContent = rotacionando ? msgRotationStop : msgRotationStart;
            if (rotacionando) {
                rotacaoInterval = window.setInterval(() => {
                    angulo += 1;
                    window.Plotly.relayout(plot, {
                        "scene.camera": {
                            eye: {
                                x: Math.cos(angulo * Math.PI / 180) * 2,
                                y: Math.sin(angulo * Math.PI / 180) * 2,
                                z: 1.25
                            }
                        }
                    });
                }, 50);
            } else if (rotacaoInterval) {
                window.clearInterval(rotacaoInterval);
                rotacaoInterval = null;
            }
        });
    }

    botaoPrint?.addEventListener("click", () => {
        window.print();
    });

    function fecharModal() {
        if (modal) modal.style.display = "none";
    }
    modalCloseButton?.addEventListener("click", fecharModal);
    modal?.addEventListener("click", (event) => {
        if (event.target === modal) {
            fecharModal();
        }
    });
})();
