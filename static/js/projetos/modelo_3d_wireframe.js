(function () {
    "use strict";

    const fileInput = document.querySelector('input[name="wireframe_file"]');
    const plotEl = document.getElementById("wireframe-3d-plot");
    const statusEl = document.getElementById("wireframe-3d-status");
    const cameraButtons = document.querySelectorAll("[data-wireframe-camera]");
    const reopenButtons = document.querySelectorAll("[data-reopen-wireframe-url]");
    const uploadForm = document.getElementById("wireframe-upload-form");
    const terrainToggle = document.getElementById("wireframeTerrainToggle");
    const rotateToggle = document.getElementById("wireframeRotateToggle");
    const opacityRange = document.getElementById("wireframeOpacityRange");
    const opacityValue = document.getElementById("wireframeOpacityValue");
    const zScaleRange = document.getElementById("wireframeZScaleRange");
    const zScaleValue = document.getElementById("wireframeZScaleValue");
    let currentPlot = null;
    let autoRotateTimer = null;
    let autoRotateAngle = 0;
    let autoRotateRadius = 1.75;
    let autoRotateEyeZ = 0.95;
    let autoRotateCenter = { x: 0, y: 0, z: 0 };
    let autoRotateUp = { x: 0, y: 0, z: 1 };
    const STORAGE_KEY = "wireframe_3d_preview_state_v1";

    if (!fileInput || !plotEl || !statusEl) {
        return;
    }

    if (typeof window.Plotly === "undefined") {
        statusEl.textContent = "Plotly não foi carregado. Recarrega a página e tenta novamente.";
        statusEl.className = "text-sm text-red-600";
        return;
    }

    function setStatus(message, isError) {
        statusEl.textContent = message || "";
        statusEl.className = isError ? "text-sm text-red-600" : "text-sm text-slate-600";
    }

    function parseObj(text) {
        const vertices = [];
        const faces = [];
        const lines = text.split(/\r?\n/);

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line || line.startsWith("#")) {
                continue;
            }

            if (line.startsWith("v ")) {
                const parts = line.split(/\s+/);
                if (parts.length >= 4) {
                    const x = Number(parts[1]);
                    const y = Number(parts[2]);
                    const z = Number(parts[3]);
                    if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
                        vertices.push([x, y, z]);
                    }
                }
                continue;
            }

            if (line.startsWith("f ")) {
                const parts = line.split(/\s+/).slice(1);
                const idx = parts
                    .map((p) => Number(String(p).split("/")[0]))
                    .filter((n) => Number.isInteger(n) && n > 0)
                    .map((n) => n - 1);

                if (idx.length >= 3) {
                    for (let k = 1; k < idx.length - 1; k += 1) {
                        faces.push([idx[0], idx[k], idx[k + 1]]);
                    }
                }
            }
        }

        return { vertices, faces };
    }

    function parseDxf(text) {
        const linesRaw = text.split(/\r?\n/);
        const pairs = [];
        for (let i = 0; i < linesRaw.length - 1; i += 2) {
            pairs.push([String(linesRaw[i] || "").trim(), String(linesRaw[i + 1] || "").trim()]);
        }

        const vertices = [];
        const faces = [];
        const lineSegments = [];
        const vertexMap = new Map();

        function keyFor(x, y, z) {
            return `${x.toFixed(6)}|${y.toFixed(6)}|${z.toFixed(6)}`;
        }

        function getOrCreateVertex(x, y, z) {
            if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
                return -1;
            }
            const key = keyFor(x, y, z);
            const existing = vertexMap.get(key);
            if (typeof existing === "number") {
                return existing;
            }
            const idx = vertices.length;
            vertices.push([x, y, z]);
            vertexMap.set(key, idx);
            return idx;
        }

        let i = 0;
        while (i < pairs.length) {
            const [groupCode, value] = pairs[i];
            if (groupCode === "0") {
                const entity = value.toUpperCase();

                if (entity === "LINE") {
                    let x1 = null; let y1 = null; let z1 = 0;
                    let x2 = null; let y2 = null; let z2 = 0;
                    i += 1;
                    while (i < pairs.length && pairs[i][0] !== "0") {
                        const [gc, val] = pairs[i];
                        if (gc === "10") x1 = Number(val);
                        else if (gc === "20") y1 = Number(val);
                        else if (gc === "30") z1 = Number(val);
                        else if (gc === "11") x2 = Number(val);
                        else if (gc === "21") y2 = Number(val);
                        else if (gc === "31") z2 = Number(val);
                        i += 1;
                    }

                    if (
                        Number.isFinite(x1) && Number.isFinite(y1) &&
                        Number.isFinite(x2) && Number.isFinite(y2)
                    ) {
                        const a = getOrCreateVertex(x1, y1, z1);
                        const b = getOrCreateVertex(x2, y2, z2);
                        if (a >= 0 && b >= 0) {
                            lineSegments.push([a, b]);
                        }
                    }
                    continue;
                }

                if (entity === "3DFACE") {
                    const p = {
                        p1: [null, null, null],
                        p2: [null, null, null],
                        p3: [null, null, null],
                        p4: [null, null, null],
                    };
                    i += 1;
                    while (i < pairs.length && pairs[i][0] !== "0") {
                        const [gc, val] = pairs[i];
                        const n = Number(val);
                        if (gc === "10") p.p1[0] = n;
                        else if (gc === "20") p.p1[1] = n;
                        else if (gc === "30") p.p1[2] = n;
                        else if (gc === "11") p.p2[0] = n;
                        else if (gc === "21") p.p2[1] = n;
                        else if (gc === "31") p.p2[2] = n;
                        else if (gc === "12") p.p3[0] = n;
                        else if (gc === "22") p.p3[1] = n;
                        else if (gc === "32") p.p3[2] = n;
                        else if (gc === "13") p.p4[0] = n;
                        else if (gc === "23") p.p4[1] = n;
                        else if (gc === "33") p.p4[2] = n;
                        i += 1;
                    }

                    const idx1 = getOrCreateVertex(p.p1[0], p.p1[1], Number.isFinite(p.p1[2]) ? p.p1[2] : 0);
                    const idx2 = getOrCreateVertex(p.p2[0], p.p2[1], Number.isFinite(p.p2[2]) ? p.p2[2] : 0);
                    const idx3 = getOrCreateVertex(p.p3[0], p.p3[1], Number.isFinite(p.p3[2]) ? p.p3[2] : 0);
                    const idx4 = getOrCreateVertex(p.p4[0], p.p4[1], Number.isFinite(p.p4[2]) ? p.p4[2] : 0);
                    if (idx1 >= 0 && idx2 >= 0 && idx3 >= 0) {
                        faces.push([idx1, idx2, idx3]);
                    }
                    if (idx1 >= 0 && idx3 >= 0 && idx4 >= 0 && idx4 !== idx3) {
                        faces.push([idx1, idx3, idx4]);
                    }
                    continue;
                }
            }
            i += 1;
        }

        return { vertices, faces, lineSegments };
    }

    function renderObjModel(model, fileName) {
        const vertices = model.vertices;
        const faces = model.faces;
        if (!vertices.length) {
            setStatus("OBJ sem vértices válidos para renderizar.", true);
            return;
        }

        const x = vertices.map((p) => p[0]);
        const y = vertices.map((p) => p[1]);
        const z = vertices.map((p) => p[2]);

        const traces = [];
        if (faces.length) {
            traces.push({
                type: "mesh3d",
                x,
                y,
                z,
                i: faces.map((f) => f[0]),
                j: faces.map((f) => f[1]),
                k: faces.map((f) => f[2]),
                color: "#3b82f6",
                opacity: 0.55,
                flatshading: true,
                name: "Superfície",
                hoverinfo: "skip",
            });
        }

        traces.push({
            type: "scatter3d",
            mode: "markers",
            x,
            y,
            z,
            marker: { size: 2, color: "#0f172a", opacity: 0.7 },
            name: "Vértices",
            hovertemplate: "X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}<extra></extra>",
        });

        const layout = {
            margin: { l: 0, r: 0, t: 30, b: 0 },
            paper_bgcolor: "#ffffff",
            plot_bgcolor: "#ffffff",
            title: { text: `Wireframe: ${fileName}`, x: 0.02, xanchor: "left", font: { size: 14 } },
            scene: {
                xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                aspectmode: "data",
                camera: { eye: { x: 1.35, y: 1.35, z: 0.9 } },
            },
            legend: { orientation: "h", y: 1.05, x: 0 },
        };

        window.Plotly.newPlot(plotEl, traces, layout, {
            responsive: true,
            displaylogo: false,
        });
        currentPlot = plotEl;

        setStatus(
            `Renderização local concluída: ${vertices.length} vértices e ${faces.length} faces trianguladas.`,
            false,
        );
    }

    function renderDxfModel(model, fileName) {
        const vertices = model.vertices;
        const faces = model.faces;
        const lineSegments = model.lineSegments || [];
        if (!vertices.length) {
            setStatus("DXF sem geometria compatível (LINE/3DFACE) para renderizar.", true);
            return;
        }

        const x = vertices.map((p) => p[0]);
        const y = vertices.map((p) => p[1]);
        const z = vertices.map((p) => p[2]);

        const traces = [];
        if (faces.length) {
            traces.push({
                type: "mesh3d",
                x,
                y,
                z,
                i: faces.map((f) => f[0]),
                j: faces.map((f) => f[1]),
                k: faces.map((f) => f[2]),
                color: "#22c55e",
                opacity: 0.45,
                flatshading: true,
                name: "3DFACE",
                hoverinfo: "skip",
            });
        }

        if (lineSegments.length) {
            const lx = [];
            const ly = [];
            const lz = [];
            for (const [a, b] of lineSegments) {
                const va = vertices[a];
                const vb = vertices[b];
                if (!va || !vb) continue;
                lx.push(va[0], vb[0], null);
                ly.push(va[1], vb[1], null);
                lz.push(va[2], vb[2], null);
            }
            traces.push({
                type: "scatter3d",
                mode: "lines",
                x: lx,
                y: ly,
                z: lz,
                line: { width: 3, color: "#0ea5e9" },
                name: "LINE",
                hoverinfo: "skip",
            });
        }

        traces.push({
            type: "scatter3d",
            mode: "markers",
            x,
            y,
            z,
            marker: { size: 2, color: "#0f172a", opacity: 0.65 },
            name: "Vértices",
            hovertemplate: "X=%{x:.3f}<br>Y=%{y:.3f}<br>Z=%{z:.3f}<extra></extra>",
        });

        const layout = {
            margin: { l: 0, r: 0, t: 30, b: 0 },
            paper_bgcolor: "#ffffff",
            plot_bgcolor: "#ffffff",
            title: { text: `Wireframe: ${fileName}`, x: 0.02, xanchor: "left", font: { size: 14 } },
            scene: {
                xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                aspectmode: "data",
                camera: { eye: { x: 1.35, y: 1.35, z: 0.9 } },
            },
            legend: { orientation: "h", y: 1.05, x: 0 },
        };

        window.Plotly.newPlot(plotEl, traces, layout, {
            responsive: true,
            displaylogo: false,
        });
        currentPlot = plotEl;

        setStatus(
            `Renderização local concluída: ${vertices.length} vértices, ${faces.length} faces 3DFACE e ${lineSegments.length} linhas.`,
            false,
        );
    }

    function clearPlot() {
        stopAutoRotate();
        window.Plotly.purge(plotEl);
        plotEl.innerHTML = "";
        currentPlot = null;
    }

    function savePlotState() {
        try {
            if (!currentPlot || !currentPlot.data || !currentPlot.layout) {
                return;
            }
            const payload = {
                data: currentPlot.data,
                layout: currentPlot.layout,
                status: statusEl.textContent || "",
                statusClass: statusEl.className || "",
            };
            window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        } catch (_) {
            // ignore storage failures
        }
    }

    function restorePlotState() {
        try {
            const raw = window.sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            const payload = JSON.parse(raw);
            if (!payload || !Array.isArray(payload.data) || !payload.layout) return;
            window.Plotly.newPlot(plotEl, payload.data, payload.layout, {
                responsive: true,
                displaylogo: false,
            });
            currentPlot = plotEl;
            if (payload.status) {
                statusEl.textContent = payload.status;
                statusEl.className = payload.statusClass || "text-sm text-slate-600";
            }
            window.sessionStorage.removeItem(STORAGE_KEY);
        } catch (_) {
            // ignore restore failures
        }
    }

    function applyCamera(view) {
        if (!currentPlot || typeof window.Plotly === "undefined") {
            return;
        }
        const cameras = {
            iso: { eye: { x: 1.35, y: 1.35, z: 0.9 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
            top: { eye: { x: 0.001, y: 0.001, z: 2.4 }, up: { x: 0, y: 1, z: 0 }, center: { x: 0, y: 0, z: 0 } },
            side: { eye: { x: 2.4, y: 0.001, z: 0.001 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
            front: { eye: { x: 0.001, y: 2.4, z: 0.001 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
        };
        window.Plotly.relayout(currentPlot, { "scene.camera": cameras[view] || cameras.iso });
    }

    function getSurfaceTraceIndexes() {
        if (!currentPlot || !Array.isArray(currentPlot.data)) return [];
        const indexes = [];
        currentPlot.data.forEach((trace, idx) => {
            if (trace && trace.type === "mesh3d") {
                indexes.push(idx);
            }
        });
        return indexes;
    }

    function applyTerrainStyle() {
        if (!currentPlot || typeof window.Plotly === "undefined") {
            return;
        }
        const surfaceIndexes = getSurfaceTraceIndexes();
        if (!surfaceIndexes.length) {
            return;
        }

        const terrainOn = terrainToggle && terrainToggle.checked;
        const opacity = opacityRange ? Number(opacityRange.value || "0.55") : 0.55;
        const zScale = zScaleRange ? Number(zScaleRange.value || "1") : 1;

        if (opacityValue) opacityValue.textContent = opacity.toFixed(2);
        if (zScaleValue) zScaleValue.textContent = zScale.toFixed(2);

        for (const idx of surfaceIndexes) {
            const trace = currentPlot.data[idx];
            const zArr = Array.isArray(trace.z) ? trace.z : [];
            if (!Array.isArray(trace.__baseZ) || trace.__baseZ.length !== zArr.length) {
                trace.__baseZ = zArr.map((v) => Number(v));
            }
            const zScaled = trace.__baseZ.map((v) => Number(v) * zScale);
            const patch = {
                opacity,
                z: [zScaled],
                flatshading: terrainOn ? false : true,
                lighting: [terrainOn
                    ? { ambient: 0.45, diffuse: 0.75, specular: 0.2, roughness: 0.8, fresnel: 0.05 }
                    : { ambient: 0.3, diffuse: 0.8, specular: 0.05, roughness: 1, fresnel: 0 }],
            };
            if (terrainOn) {
                patch.intensity = [zScaled];
                patch.intensitymode = ["vertex"];
                patch.colorscale = [[
                    0.0, "#3b2f1f",
                ], [
                    0.2, "#6b4f2a",
                ], [
                    0.4, "#8d6e3b",
                ], [
                    0.6, "#a88f5a",
                ], [
                    0.8, "#7f8c4d",
                ], [
                    1.0, "#e5d8a8",
                ]];
                patch.showscale = [false];
            } else {
                patch.intensity = [null];
                patch.intensitymode = [null];
                patch.colorscale = [null];
                patch.color = [idx === 0 ? "#3b82f6" : "#22c55e"];
                patch.showscale = [false];
            }
            window.Plotly.restyle(currentPlot, patch, [idx]);
        }
    }

    function stopAutoRotate() {
        if (autoRotateTimer) {
            window.clearInterval(autoRotateTimer);
            autoRotateTimer = null;
        }
    }

    function startAutoRotate() {
        if (!currentPlot || autoRotateTimer) {
            return;
        }
        const scene = currentPlot.layout && currentPlot.layout.scene ? currentPlot.layout.scene : null;
        const camera = scene && scene.camera ? scene.camera : null;
        const eye = camera && camera.eye ? camera.eye : { x: 1.35, y: 1.35, z: 0.9 };
        const center = camera && camera.center ? camera.center : { x: 0, y: 0, z: 0 };
        const up = camera && camera.up ? camera.up : { x: 0, y: 0, z: 1 };

        const ex = Number(eye.x) || 0.001;
        const ey = Number(eye.y) || 0.001;
        const ez = Number(eye.z) || 0.9;
        autoRotateAngle = Math.atan2(ey, ex);
        autoRotateRadius = Math.max(Math.hypot(ex, ey), 0.05);
        autoRotateEyeZ = ez;
        autoRotateCenter = {
            x: Number(center.x) || 0,
            y: Number(center.y) || 0,
            z: Number(center.z) || 0,
        };
        autoRotateUp = {
            x: Number(up.x) || 0,
            y: Number(up.y) || 0,
            z: Number(up.z) || 1,
        };

        autoRotateTimer = window.setInterval(() => {
            autoRotateAngle += 0.045;
            const eyeX = Math.cos(autoRotateAngle) * autoRotateRadius;
            const eyeY = Math.sin(autoRotateAngle) * autoRotateRadius;
            window.Plotly.relayout(currentPlot, {
                "scene.camera": {
                    eye: { x: eyeX, y: eyeY, z: autoRotateEyeZ },
                    up: autoRotateUp,
                    center: autoRotateCenter,
                },
            });
        }, 60);
    }

    function updateAutoRotateState() {
        if (rotateToggle && rotateToggle.checked) {
            startAutoRotate();
        } else {
            stopAutoRotate();
        }
    }

    cameraButtons.forEach((button) => {
        button.addEventListener("click", () => {
            applyCamera(button.dataset.wireframeCamera || "iso");
        });
    });

    if (uploadForm) {
        uploadForm.addEventListener("submit", () => {
            savePlotState();
        });
    }

    if (terrainToggle) {
        terrainToggle.addEventListener("change", applyTerrainStyle);
    }
    if (opacityRange) {
        opacityRange.addEventListener("input", applyTerrainStyle);
    }
    if (zScaleRange) {
        zScaleRange.addEventListener("input", applyTerrainStyle);
    }
    if (rotateToggle) {
        rotateToggle.addEventListener("change", updateAutoRotateState);
    }

    restorePlotState();

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        clearPlot();

        if (!file) {
            setStatus("");
            return;
        }

        const name = file.name || "";
        const extension = name.includes(".") ? `.${name.split(".").pop().toLowerCase()}` : "";
        if (extension !== ".obj" && extension !== ".dxf") {
            setStatus("Pré-visualização 3D local disponível apenas para ficheiros .obj e .dxf.", false);
            return;
        }

        setStatus(`A processar ficheiro ${extension.toUpperCase()} no browser…`, false);
        const reader = new FileReader();
        reader.onload = () => {
            try {
                const text = String(reader.result || "");
                if (extension === ".obj") {
                    const model = parseObj(text);
                    renderObjModel(model, name);
                } else {
                    const model = parseDxf(text);
                    renderDxfModel(model, name);
                }
                applyTerrainStyle();
                updateAutoRotateState();
            } catch (error) {
                setStatus(`Erro ao processar ficheiro: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        };
        reader.onerror = () => {
            setStatus("Não foi possível ler o ficheiro selecionado.", true);
        };
        reader.readAsText(file);
    });

    reopenButtons.forEach((button) => {
        button.addEventListener("click", async () => {
            const url = button.dataset.reopenWireframeUrl || "";
            const formato = (button.dataset.reopenWireframeFormato || "").toLowerCase();
            const name = button.dataset.reopenWireframeName || "wireframe";
            if (!url || (formato !== "obj" && formato !== "dxf")) {
                setStatus("Não foi possível reabrir este ficheiro.", true);
                return;
            }

            clearPlot();
            setStatus(`A carregar ficheiro guardado (${formato.toUpperCase()})…`, false);
            try {
                const response = await window.fetch(url, { credentials: "same-origin" });
                if (!response.ok) {
                    const errorBody = await response.text();
                    throw new Error(errorBody || `HTTP ${response.status}`);
                }
                const contentType = (response.headers.get("content-type") || "").toLowerCase();
                const text = await response.text();
                const lower = text.trim().toLowerCase();
                if (contentType.includes("text/html") || lower.startsWith("<!doctype html") || lower.startsWith("<html")) {
                    throw new Error("A resposta recebida não é um ficheiro técnico. Verifica sessão/permissões.");
                }
                if (formato === "obj") {
                    const model = parseObj(text);
                    if (!model.vertices.length) {
                        throw new Error("OBJ sem vértices válidos. Este registo pode ser antigo; guarda novamente o ficheiro.");
                    }
                    renderObjModel(model, name);
                } else {
                    const model = parseDxf(text);
                    if (!model.vertices.length) {
                        throw new Error("DXF sem geometria LINE/3DFACE válida. Guarda novamente o ficheiro.");
                    }
                    renderDxfModel(model, name);
                }
                applyTerrainStyle();
                updateAutoRotateState();
            } catch (error) {
                setStatus(
                    `Erro ao carregar ficheiro guardado: ${error && error.message ? error.message : "erro desconhecido"}`,
                    true,
                );
            }
        });
    });
})();
