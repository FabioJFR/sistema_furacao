(function () {
    "use strict";

    const fileInput = document.querySelector('input[name="block_file"]');
    const plotEl = document.getElementById("block-3d-plot");
    const statusEl = document.getElementById("block-3d-status");
    const reopenButtons = document.querySelectorAll("[data-reopen-block-url]");
    const uploadForm = document.getElementById("block-upload-form");

    const voxelToggle = document.getElementById("blockAsVoxelsToggle");
    const animRotateToggle = document.getElementById("blockAnimRotateToggle");
    const animPulseToggle = document.getElementById("blockAnimPulseToggle");
    const valueMinRange = document.getElementById("blockValueMinRange");
    const valueMaxRange = document.getElementById("blockValueMaxRange");
    const zMinRange = document.getElementById("blockZMinRange");
    const zMaxRange = document.getElementById("blockZMaxRange");
    const valueMinLabel = document.getElementById("blockValueMinLabel");
    const valueMaxLabel = document.getElementById("blockValueMaxLabel");
    const zMinLabel = document.getElementById("blockZMinLabel");
    const zMaxLabel = document.getElementById("blockZMaxLabel");
    const exportCsvBtn = document.getElementById("blockExportCsvBtn");
    const exportJsonBtn = document.getElementById("blockExportJsonBtn");

    const STORAGE_KEY = "block_3d_preview_state_v1";
    const UI_STORAGE_PREFIX = "block_3d_ui_state_v1:";
    let currentPlot = null;
    let currentPoints = [];
    let currentStateScope = "temp";
    let currentConfigUrl = "";
    let pendingServerUiConfig = null;
    let serverSyncTimer = null;
    let valueDomain = { min: 0, max: 100 };
    let zDomain = { min: 0, max: 100 };
    let estimatedVoxelSize = 1;
    let rotateTimer = null;
    let pulseTimer = null;
    let rotateAngle = 0;
    let pulseT = 0;

    if (!fileInput || !plotEl || !statusEl || typeof window.Plotly === "undefined") {
        return;
    }

    function setStatus(message, isError) {
        statusEl.textContent = message || "";
        statusEl.className = isError ? "text-sm text-red-600" : "text-sm text-slate-600";
    }

    function currentUiStorageKey() {
        return `${UI_STORAGE_PREFIX}${currentStateScope || "temp"}`;
    }

    function getCsrfToken() {
        const value = `; ${document.cookie || ""}`;
        const parts = value.split("; csrftoken=");
        if (parts.length === 2) return parts.pop().split(";").shift() || "";
        return "";
    }

    function readUiConfig() {
        const vMin = Number(valueMinRange ? valueMinRange.value : valueDomain.min);
        const vMax = Number(valueMaxRange ? valueMaxRange.value : valueDomain.max);
        const zMin = Number(zMinRange ? zMinRange.value : zDomain.min);
        const zMax = Number(zMaxRange ? zMaxRange.value : zDomain.max);
        return {
            mostrar_como_voxels: !voxelToggle || !!voxelToggle.checked,
            valor_min: Math.min(vMin, vMax),
            valor_max: Math.max(vMin, vMax),
            z_min: Math.min(zMin, zMax),
            z_max: Math.max(zMin, zMax),
            animacao_rotacao: !!(animRotateToggle && animRotateToggle.checked),
            animacao_pulso: !!(animPulseToggle && animPulseToggle.checked),
        };
    }

    function persistUiConfig() {
        try {
            window.localStorage.setItem(currentUiStorageKey(), JSON.stringify(readUiConfig()));
        } catch (_) {}
    }

    function loadUiConfig() {
        try {
            const raw = window.localStorage.getItem(currentUiStorageKey());
            if (!raw) return null;
            return JSON.parse(raw);
        } catch (_) {
            return null;
        }
    }

    function scheduleServerUiConfigSync() {
        if (!currentConfigUrl || !currentStateScope.startsWith("model:")) return;
        if (serverSyncTimer) window.clearTimeout(serverSyncTimer);
        serverSyncTimer = window.setTimeout(async () => {
            try {
                await window.fetch(currentConfigUrl, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: JSON.stringify({ ui_config: readUiConfig() }),
                });
            } catch (_) {}
        }, 300);
    }

    function applyUiConfig(config) {
        if (!config || typeof config !== "object") return;
        if (voxelToggle && typeof config.mostrar_como_voxels === "boolean") voxelToggle.checked = config.mostrar_como_voxels;
        if (animRotateToggle && typeof config.animacao_rotacao === "boolean") animRotateToggle.checked = config.animacao_rotacao;
        if (animPulseToggle && typeof config.animacao_pulso === "boolean") animPulseToggle.checked = config.animacao_pulso;

        const setRange = (el, value, fallback) => {
            if (!el) return;
            const min = Number(el.min);
            const max = Number(el.max);
            const num = Number.isFinite(Number(value)) ? Number(value) : fallback;
            const clamped = Number.isFinite(min) && Number.isFinite(max) ? Math.max(min, Math.min(max, num)) : num;
            el.value = String(clamped);
        };
        setRange(valueMinRange, config.valor_min, valueDomain.min);
        setRange(valueMaxRange, config.valor_max, valueDomain.max);
        setRange(zMinRange, config.z_min, zDomain.min);
        setRange(zMaxRange, config.z_max, zDomain.max);
        refreshRangeLabels();
    }

    function stopRotateAnimation() {
        if (rotateTimer) {
            window.clearInterval(rotateTimer);
            rotateTimer = null;
        }
    }

    function stopPulseAnimation() {
        if (pulseTimer) {
            window.clearInterval(pulseTimer);
            pulseTimer = null;
        }
    }

    function startRotateAnimation() {
        if (!currentPlot || rotateTimer) return;
        const scene = currentPlot.layout && currentPlot.layout.scene ? currentPlot.layout.scene : null;
        const eye = scene && scene.camera && scene.camera.eye ? scene.camera.eye : { x: 1.35, y: 1.35, z: 0.9 };
        const radius = Math.max(Math.hypot(Number(eye.x) || 1, Number(eye.y) || 1), 0.05);
        const z = Number(eye.z) || 0.9;
        rotateAngle = Math.atan2(Number(eye.y) || 0, Number(eye.x) || 1);
        rotateTimer = window.setInterval(() => {
            rotateAngle += 0.04;
            window.Plotly.relayout(currentPlot, {
                "scene.camera": {
                    eye: { x: Math.cos(rotateAngle) * radius, y: Math.sin(rotateAngle) * radius, z },
                    up: { x: 0, y: 0, z: 1 },
                    center: { x: 0, y: 0, z: 0 },
                },
            });
        }, 60);
    }

    function startPulseAnimation() {
        if (!currentPlot || pulseTimer) return;
        pulseT = 0;
        pulseTimer = window.setInterval(() => {
            pulseT += 0.2;
            const markerSize = 4.5 + Math.sin(pulseT) * 1.4;
            const meshOpacity = 0.8 + (Math.sin(pulseT + 0.5) + 1) * 0.08;
            (currentPlot.data || []).forEach((trace, idx) => {
                if (trace.type === "scatter3d") {
                    window.Plotly.restyle(currentPlot, { "marker.size": markerSize }, [idx]);
                } else if (trace.type === "mesh3d") {
                    window.Plotly.restyle(currentPlot, { opacity: meshOpacity }, [idx]);
                }
            });
        }, 90);
    }

    function syncAnimations() {
        if (animRotateToggle && animRotateToggle.checked) startRotateAnimation();
        else stopRotateAnimation();
        if (animPulseToggle && animPulseToggle.checked) startPulseAnimation();
        else stopPulseAnimation();
    }

    function parseCsv(text) {
        const lines = text.split(/\r?\n/).filter(Boolean);
        if (!lines.length) return [];
        const header = lines[0].split(",").map((h) => h.trim().toLowerCase());
        const idxX = header.indexOf("x");
        const idxY = header.indexOf("y");
        const idxZ = header.indexOf("z");
        const idxV = header.indexOf("valor");
        if (idxX < 0 || idxY < 0 || idxZ < 0) return [];

        const points = [];
        for (let i = 1; i < lines.length; i += 1) {
            const cols = lines[i].split(",").map((c) => c.trim());
            const x = Number(cols[idxX]);
            const y = Number(cols[idxY]);
            const z = Number(cols[idxZ]);
            const valor = idxV >= 0 ? Number(cols[idxV]) : z;
            if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
                points.push({ x, y, z, valor: Number.isFinite(valor) ? valor : z });
            }
        }
        return points;
    }

    function parseJson(text) {
        try {
            const payload = JSON.parse(text || "[]");
            if (!Array.isArray(payload)) return [];
            return payload
                .map((it) => {
                    const x = Number(it.x);
                    const y = Number(it.y);
                    const z = Number(it.z);
                    const valor = Number.isFinite(Number(it.valor)) ? Number(it.valor) : z;
                    return { x, y, z, valor };
                })
                .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z));
        } catch (_) {
            return [];
        }
    }

    function percentile(arr, p) {
        if (!arr.length) return null;
        const sorted = [...arr].sort((a, b) => a - b);
        const idx = Math.min(sorted.length - 1, Math.max(0, Math.round((p / 100) * (sorted.length - 1))));
        return sorted[idx];
    }

    function estimateVoxelSize(points) {
        if (points.length < 2) return 1;
        const xs = [...new Set(points.map((p) => p.x))].sort((a, b) => a - b);
        const ys = [...new Set(points.map((p) => p.y))].sort((a, b) => a - b);
        const zs = [...new Set(points.map((p) => p.z))].sort((a, b) => a - b);
        const diffs = [];
        function collectDiffs(values) {
            for (let i = 1; i < values.length; i += 1) {
                const d = Math.abs(values[i] - values[i - 1]);
                if (d > 0) diffs.push(d);
            }
        }
        collectDiffs(xs);
        collectDiffs(ys);
        collectDiffs(zs);
        const median = percentile(diffs, 50);
        return median && Number.isFinite(median) ? Math.max(0.1, median) : 1;
    }

    function configureRangeInputs(points) {
        const values = points.map((p) => p.valor);
        const zs = points.map((p) => p.z);

        const vMin = Math.min(...values);
        const vMax = Math.max(...values);
        const zMin = Math.min(...zs);
        const zMax = Math.max(...zs);

        valueDomain = { min: vMin, max: vMax };
        zDomain = { min: zMin, max: zMax };
        estimatedVoxelSize = estimateVoxelSize(points);

        const controls = [
            [valueMinRange, vMin, vMax, vMin],
            [valueMaxRange, vMin, vMax, vMax],
            [zMinRange, zMin, zMax, zMin],
            [zMaxRange, zMin, zMax, zMax],
        ];

        controls.forEach(([el, min, max, value]) => {
            if (!el) return;
            el.min = String(min);
            el.max = String(max);
            el.step = String(Math.max((max - min) / 500, 0.01));
            el.value = String(value);
        });

        refreshRangeLabels();
    }

    function refreshRangeLabels() {
        if (valueMinLabel) valueMinLabel.textContent = Number(valueMinRange.value || 0).toFixed(2);
        if (valueMaxLabel) valueMaxLabel.textContent = Number(valueMaxRange.value || 0).toFixed(2);
        if (zMinLabel) zMinLabel.textContent = Number(zMinRange.value || 0).toFixed(2);
        if (zMaxLabel) zMaxLabel.textContent = Number(zMaxRange.value || 0).toFixed(2);
    }

    function getFilteredPoints() {
        if (!currentPoints.length) return [];
        const vMin = Number(valueMinRange ? valueMinRange.value : valueDomain.min);
        const vMax = Number(valueMaxRange ? valueMaxRange.value : valueDomain.max);
        const zMin = Number(zMinRange ? zMinRange.value : zDomain.min);
        const zMax = Number(zMaxRange ? zMaxRange.value : zDomain.max);

        const minV = Math.min(vMin, vMax);
        const maxV = Math.max(vMin, vMax);
        const minZ = Math.min(zMin, zMax);
        const maxZ = Math.max(zMin, zMax);

        return currentPoints.filter((p) => p.valor >= minV && p.valor <= maxV && p.z >= minZ && p.z <= maxZ);
    }

    function getActiveFilters() {
        const vMin = Number(valueMinRange ? valueMinRange.value : valueDomain.min);
        const vMax = Number(valueMaxRange ? valueMaxRange.value : valueDomain.max);
        const zMin = Number(zMinRange ? zMinRange.value : zDomain.min);
        const zMax = Number(zMaxRange ? zMaxRange.value : zDomain.max);
        return {
            mostrar_como_voxels: !voxelToggle || !!voxelToggle.checked,
            valor_min: Math.min(vMin, vMax),
            valor_max: Math.max(vMin, vMax),
            z_min: Math.min(zMin, zMax),
            z_max: Math.max(zMin, zMax),
            animacao_rotacao: !!(animRotateToggle && animRotateToggle.checked),
            animacao_pulso: !!(animPulseToggle && animPulseToggle.checked),
        };
    }

    function computeSummary(points) {
        if (!points.length) {
            return {
                pontos: 0,
                extensao_x_m: 0,
                extensao_y_m: 0,
                extensao_z_m: 0,
                volume_envolvente_m3_estimado: 0,
                valor_min: 0,
                valor_max: 0,
                valor_medio: 0,
            };
        }
        const xs = points.map((p) => p.x);
        const ys = points.map((p) => p.y);
        const zs = points.map((p) => p.z);
        const vals = points.map((p) => p.valor);
        const dx = Math.max(...xs) - Math.min(...xs);
        const dy = Math.max(...ys) - Math.min(...ys);
        const dz = Math.max(...zs) - Math.min(...zs);
        const vol = Math.max(dx, 0) * Math.max(dy, 0) * Math.max(dz, 0);
        const minVal = Math.min(...vals);
        const maxVal = Math.max(...vals);
        const meanVal = vals.reduce((acc, v) => acc + v, 0) / vals.length;
        return {
            pontos: points.length,
            extensao_x_m: Number(dx.toFixed(4)),
            extensao_y_m: Number(dy.toFixed(4)),
            extensao_z_m: Number(dz.toFixed(4)),
            volume_envolvente_m3_estimado: Number(vol.toFixed(4)),
            valor_min: Number(minVal.toFixed(4)),
            valor_max: Number(maxVal.toFixed(4)),
            valor_medio: Number(meanVal.toFixed(4)),
        };
    }

    function exportCsvSelecao() {
        const points = getFilteredPoints();
        if (!points.length) {
            setStatus("Não há blocos filtrados para exportar.", true);
            return;
        }
        const summary = computeSummary(points);
        const filters = getActiveFilters();
        const header = "x,y,z,valor";
        const rows = points.map((p) => `${p.x},${p.y},${p.z},${p.valor}`);
        const summaryLines = [
            "# resumo",
            "pontos,extensao_x_m,extensao_y_m,extensao_z_m,volume_envolvente_m3_estimado,valor_min,valor_max,valor_medio",
            `${summary.pontos},${summary.extensao_x_m},${summary.extensao_y_m},${summary.extensao_z_m},${summary.volume_envolvente_m3_estimado},${summary.valor_min},${summary.valor_max},${summary.valor_medio}`,
            "",
            "# filtros_ativos",
            "mostrar_como_voxels,valor_min,valor_max,z_min,z_max,animacao_rotacao,animacao_pulso",
            `${filters.mostrar_como_voxels},${filters.valor_min},${filters.valor_max},${filters.z_min},${filters.z_max},${filters.animacao_rotacao},${filters.animacao_pulso}`,
        ];
        const csv = ["# blocos_filtrados", header, ...rows, "", ...summaryLines].join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        a.href = url;
        a.download = `block-model-filtrado-${ts}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setStatus(`CSV exportado com ${points.length} bloco(s).`, false);
    }

    function exportJsonTecnico() {
        const points = getFilteredPoints();
        if (!points.length) {
            setStatus("Não há blocos filtrados para exportar.", true);
            return;
        }
        const payload = {
            tipo: "block_model_export",
            versao: "1.0",
            exportado_em: new Date().toISOString(),
            filtros_ativos: getActiveFilters(),
            resumo: computeSummary(points),
            blocos_filtrados: points.map((p) => ({ x: p.x, y: p.y, z: p.z, valor: p.valor })),
        };
        const json = JSON.stringify(payload, null, 2);
        const blob = new Blob([json], { type: "application/json;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        a.href = url;
        a.download = `block-model-tecnico-${ts}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setStatus(`JSON técnico exportado com ${points.length} bloco(s).`, false);
    }

    function buildVoxelMesh(points) {
        const x = [];
        const y = [];
        const z = [];
        const i = [];
        const j = [];
        const k = [];
        const intensity = [];

        const half = estimatedVoxelSize / 2;
        const faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4],
            [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6],
            [3, 0, 4], [3, 4, 7],
        ];

        points.forEach((p) => {
            const base = x.length;
            const verts = [
                [p.x - half, p.y - half, p.z - half],
                [p.x + half, p.y - half, p.z - half],
                [p.x + half, p.y + half, p.z - half],
                [p.x - half, p.y + half, p.z - half],
                [p.x - half, p.y - half, p.z + half],
                [p.x + half, p.y - half, p.z + half],
                [p.x + half, p.y + half, p.z + half],
                [p.x - half, p.y + half, p.z + half],
            ];
            verts.forEach((v) => {
                x.push(v[0]); y.push(v[1]); z.push(v[2]); intensity.push(p.valor);
            });
            faces.forEach((f) => {
                i.push(base + f[0]);
                j.push(base + f[1]);
                k.push(base + f[2]);
            });
        });

        return { x, y, z, i, j, k, intensity };
    }

    function renderCurrent() {
        if (!currentPoints.length) {
            setStatus("Sem dados para renderizar.", true);
            return;
        }

        refreshRangeLabels();
        const points = getFilteredPoints();
        if (!points.length) {
            setStatus("Nenhum bloco dentro dos filtros atuais.", true);
            window.Plotly.purge(plotEl);
            plotEl.innerHTML = "";
            currentPlot = null;
            stopRotateAnimation();
            stopPulseAnimation();
            return;
        }

        const asVoxels = !voxelToggle || voxelToggle.checked;
        let traces;

        if (asVoxels) {
            const mesh = buildVoxelMesh(points);
            traces = [{
                type: "mesh3d",
                x: mesh.x,
                y: mesh.y,
                z: mesh.z,
                i: mesh.i,
                j: mesh.j,
                k: mesh.k,
                intensity: mesh.intensity,
                intensitymode: "vertex",
                colorscale: "Earth",
                opacity: 0.95,
                flatshading: true,
                name: "Voxels",
                showscale: true,
                colorbar: { title: "Valor" },
            }];
        } else {
            traces = [{
                type: "scatter3d",
                mode: "markers",
                x: points.map((p) => p.x),
                y: points.map((p) => p.y),
                z: points.map((p) => p.z),
                marker: {
                    size: 5,
                    symbol: "square",
                    color: points.map((p) => p.valor),
                    colorscale: "Earth",
                    opacity: 0.9,
                    colorbar: { title: "Valor" },
                },
                name: "Blocos",
                hovertemplate: "X=%{x:.2f}<br>Y=%{y:.2f}<br>Z=%{z:.2f}<br>V=%{marker.color:.2f}<extra></extra>",
            }];
        }

        const layout = {
            margin: { l: 0, r: 0, t: 30, b: 0 },
            paper_bgcolor: "#ffffff",
            plot_bgcolor: "#ffffff",
            title: { text: `Block Model (${asVoxels ? "voxels" : "pontos"})`, x: 0.02, xanchor: "left", font: { size: 14 } },
            scene: {
                xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                aspectmode: "data",
                camera: { eye: { x: 1.35, y: 1.35, z: 0.9 } },
            },
        };

        window.Plotly.newPlot(plotEl, traces, layout, { responsive: true, displaylogo: false });
        currentPlot = plotEl;
        setStatus(`Renderização concluída: ${points.length} blocos visíveis.`, false);
        syncAnimations();
        persistUiConfig();
        scheduleServerUiConfigSync();
    }

    function savePlotState() {
        try {
            if (!currentPlot || !currentPlot.data || !currentPlot.layout) return;
            window.sessionStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    data: currentPlot.data,
                    layout: currentPlot.layout,
                    status: statusEl.textContent || "",
                    statusClass: statusEl.className || "",
                }),
            );
        } catch (_) {}
    }

    function restorePlotState() {
        try {
            const raw = window.sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            const payload = JSON.parse(raw);
            if (!payload || !Array.isArray(payload.data) || !payload.layout) return;
            window.Plotly.newPlot(plotEl, payload.data, payload.layout, { responsive: true, displaylogo: false });
            currentPlot = plotEl;
            if (payload.status) {
                statusEl.textContent = payload.status;
                statusEl.className = payload.statusClass || "text-sm text-slate-600";
            }
            window.sessionStorage.removeItem(STORAGE_KEY);
        } catch (_) {}
    }

    function loadPoints(points) {
        currentPoints = points || [];
        if (!currentPoints.length) {
            setStatus("Sem blocos válidos para renderizar (esperado: x,y,z).", true);
            return;
        }
        configureRangeInputs(currentPoints);
        if (pendingServerUiConfig) {
            applyUiConfig(pendingServerUiConfig);
            pendingServerUiConfig = null;
        } else {
            applyUiConfig(loadUiConfig());
        }
        renderCurrent();
    }

    if (uploadForm) {
        uploadForm.addEventListener("submit", savePlotState);
    }
    restorePlotState();
    syncAnimations();

    [valueMinRange, valueMaxRange, zMinRange, zMaxRange].forEach((el) => {
        if (!el) return;
        el.addEventListener("input", renderCurrent);
    });
    if (voxelToggle) voxelToggle.addEventListener("change", renderCurrent);
    if (animRotateToggle) animRotateToggle.addEventListener("change", syncAnimations);
    if (animPulseToggle) animPulseToggle.addEventListener("change", syncAnimations);
    if (exportCsvBtn) exportCsvBtn.addEventListener("click", exportCsvSelecao);
    if (exportJsonBtn) exportJsonBtn.addEventListener("click", exportJsonTecnico);

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        currentStateScope = "temp";
        currentConfigUrl = "";
        pendingServerUiConfig = null;
        const name = file.name || "";
        const extension = name.includes(".") ? `.${name.split(".").pop().toLowerCase()}` : "";
        setStatus("A processar ficheiro de blocos…", false);
        const reader = new FileReader();
        reader.onload = () => {
            const text = String(reader.result || "");
            let points = [];
            if (extension === ".csv") points = parseCsv(text);
            else if (extension === ".json") points = parseJson(text);
            else {
                setStatus("Formato não suportado (usa .csv ou .json).", true);
                return;
            }
            loadPoints(points);
            if (name) {
                document.title = `Block Model - ${name}`;
            }
        };
        reader.onerror = () => setStatus("Não foi possível ler o ficheiro.", true);
        reader.readAsText(file);
    });

    reopenButtons.forEach((button) => {
        button.addEventListener("click", async () => {
            const url = button.dataset.reopenBlockUrl || "";
            const modelId = button.dataset.reopenBlockId || "";
            const configUrl = button.dataset.reopenBlockConfigUrl || "";
            const formato = (button.dataset.reopenBlockFormato || "").toLowerCase();
            if (!url || (formato !== "csv" && formato !== "json")) {
                setStatus("Não foi possível reabrir este block model.", true);
                return;
            }
            try {
                currentStateScope = modelId ? `model:${modelId}` : "temp";
                currentConfigUrl = configUrl;
                pendingServerUiConfig = null;
                if (configUrl) {
                    try {
                        const configResponse = await window.fetch(configUrl, { credentials: "same-origin" });
                        const payload = await configResponse.json();
                        if (configResponse.ok && payload && payload.ui_config) {
                            pendingServerUiConfig = payload.ui_config;
                        }
                    } catch (_) {}
                }
                const response = await window.fetch(url, { credentials: "same-origin" });
                const text = await response.text();
                if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
                const points = formato === "csv" ? parseCsv(text) : parseJson(text);
                loadPoints(points);
            } catch (error) {
                setStatus(`Erro ao reabrir block model: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        });
    });
})();
