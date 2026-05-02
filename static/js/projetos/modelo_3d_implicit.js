(function () {
    "use strict";

    const fileInput = document.querySelector('input[name="implicit_file"]');
    const plotEl = document.getElementById("implicit-3d-plot");
    const statusEl = document.getElementById("implicit-3d-status");
    const reopenButtons = document.querySelectorAll("[data-reopen-implicit-url]");
    const cameraButtons = document.querySelectorAll("[data-implicit-camera]");
    const exportPngBtn = document.getElementById("implicitExportPngBtn");
    const exportCsvBtn = document.getElementById("implicitExportCsvBtn");
    const exportJsonBtn = document.getElementById("implicitExportJsonBtn");
    const animRotateToggle = document.getElementById("implicitAnimRotateToggle");
    const animPulseToggle = document.getElementById("implicitAnimPulseToggle");
    const uploadForm = document.getElementById("implicit-upload-form");
    const domainFilter = document.getElementById("implicitDomainFilter");
    const domainChecklist = document.getElementById("implicitDomainChecklist");
    const selectAllDomainsBtn = document.getElementById("implicitSelectAllDomainsBtn");
    const clearDomainsBtn = document.getElementById("implicitClearDomainsBtn");
    const showPointsToggle = document.getElementById("implicitShowPointsToggle");
    const showSurfaceToggle = document.getElementById("implicitShowSurfaceToggle");
    const surfaceModeSelect = document.getElementById("implicitSurfaceMode");
    const opacityRange = document.getElementById("implicitOpacityRange");
    const opacityLabel = document.getElementById("implicitOpacityLabel");
    const analyticsEl = document.getElementById("implicit-analytics");
    const metricXEl = document.getElementById("implicitMetricX");
    const metricYEl = document.getElementById("implicitMetricY");
    const metricZEl = document.getElementById("implicitMetricZ");
    const metricVolEl = document.getElementById("implicitMetricVol");
    const domainMetricsEl = document.getElementById("implicitDomainMetrics");
    const STORAGE_KEY = "implicit_3d_preview_state_v1";
    const UI_STORAGE_PREFIX = "implicit_3d_ui_state_v1:";
    let currentPlot = null;
    let currentPoints = [];
    let currentStateScope = "temp";
    let currentConfigUrl = "";
    let pendingServerUiConfig = null;
    let serverSyncTimer = null;
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
        const domainChecks = [];
        if (domainChecklist) {
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) domainChecks.push(el.dataset.domain || "");
            });
        }
        return {
            showPoints: showPointsToggle ? !!showPointsToggle.checked : true,
            showSurface: showSurfaceToggle ? !!showSurfaceToggle.checked : true,
            surfaceMode: surfaceModeSelect ? (surfaceModeSelect.value || "delaunay") : "delaunay",
            opacity: opacityRange ? Number(opacityRange.value || "0.2") : 0.2,
            selectedDomain: domainFilter ? (domainFilter.value || "all") : "all",
            checkedDomains: domainChecks,
            rotateAnim: animRotateToggle ? !!animRotateToggle.checked : false,
            pulseAnim: animPulseToggle ? !!animPulseToggle.checked : false,
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
        if (showPointsToggle && typeof config.showPoints === "boolean") showPointsToggle.checked = config.showPoints;
        if (showSurfaceToggle && typeof config.showSurface === "boolean") showSurfaceToggle.checked = config.showSurface;
        if (surfaceModeSelect && config.surfaceMode) surfaceModeSelect.value = config.surfaceMode;
        if (opacityRange && Number.isFinite(Number(config.opacity))) opacityRange.value = String(config.opacity);
        if (opacityLabel && opacityRange) opacityLabel.textContent = Number(opacityRange.value || 0).toFixed(2);
        if (animRotateToggle && typeof config.rotateAnim === "boolean") animRotateToggle.checked = config.rotateAnim;
        if (animPulseToggle && typeof config.pulseAnim === "boolean") animPulseToggle.checked = config.pulseAnim;
        if (domainFilter && config.selectedDomain) {
            const exists = Array.from(domainFilter.options || []).some((o) => o.value === config.selectedDomain);
            domainFilter.value = exists ? config.selectedDomain : "all";
        }
        if (domainChecklist && Array.isArray(config.checkedDomains)) {
            const checkedSet = new Set(config.checkedDomains);
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                el.checked = checkedSet.has(el.dataset.domain || "");
            });
        }
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
            const markerSize = 3.5 + Math.sin(pulseT) * 1.2;
            const baseOpacity = opacityRange ? Number(opacityRange.value || "0.2") : 0.2;
            const meshOpacity = Math.max(0.05, Math.min(1, baseOpacity + Math.sin(pulseT + 0.5) * 0.06));
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
        const idxD = header.indexOf("dominio") >= 0 ? header.indexOf("dominio") : header.indexOf("domain");
        if (idxX < 0 || idxY < 0 || idxZ < 0) return [];
        const points = [];
        for (let i = 1; i < lines.length; i += 1) {
            const cols = lines[i].split(",").map((c) => c.trim());
            const x = Number(cols[idxX]);
            const y = Number(cols[idxY]);
            const z = Number(cols[idxZ]);
            const dominio = idxD >= 0 ? (cols[idxD] || "default") : "default";
            if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
                points.push({ x, y, z, dominio });
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
                    const dominio = (it.dominio || it.domain || "default");
                    return { x, y, z, dominio };
                })
                .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z));
        } catch (_) {
            return [];
        }
    }

    function colorForDomain(domain) {
        const value = String(domain || "default").trim().toLowerCase();

        // Paleta geológica: cores próximas ao aspeto visual típico da rocha/material.
        const rockColors = {
            granito: "#B8AFA6",
            quartz: "#E9EEF2",
            quartzo: "#E9EEF2",
            solo: "#8B5A2B",
            xisto: "#4B5563",
            "xisto escuro": "#2F343A",
            "xisto_escuro": "#2F343A",
            "xisto claro": "#7C8591",
            "xisto_claro": "#7C8591",
            calcario: "#D9D2C3",
            calcário: "#D9D2C3",
            basalto: "#2F343A",
            arenito: "#C9A66B",
            argila: "#A65E4A",
            pirite: "#D4AF37",
            jaspe: "#B7410E",
            marmore: "#F1F0EC",
            mármore: "#F1F0EC",
            gnaisse: "#8A7D75",
            dolomito: "#CFC4B0",
            cascalho: "#7A6A58",
            saibro: "#A9794A",
            minério: "#A9552B",
            minerio: "#A9552B",
            estéril: "#6B7280",
            esteril: "#6B7280",
            default: "#3B82F6",
        };

        if (rockColors[value]) {
            return rockColors[value];
        }

        const fallback = ["#64748B", "#0EA5E9", "#22C55E", "#F59E0B", "#A855F7", "#EF4444"];
        let hash = 0;
        for (let i = 0; i < value.length; i += 1) hash = ((hash << 5) - hash) + value.charCodeAt(i);
        return fallback[Math.abs(hash) % fallback.length];
    }

    function renderImplicit(points, name) {
        if (!points.length) {
            setStatus("Sem pontos válidos para renderizar (esperado: x,y,z).", true);
            return;
        }
        const previousCamera = currentPlot && currentPlot.layout && currentPlot.layout.scene
            ? currentPlot.layout.scene.camera
            : null;

        currentPoints = points;
        const groups = new Map();
        points.forEach((p) => {
            const key = p.dominio || "default";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(p);
        });

        const selectedDomain = domainFilter ? domainFilter.value : "all";
        const showPoints = !showPointsToggle || showPointsToggle.checked;
        const showSurface = !showSurfaceToggle || showSurfaceToggle.checked;
        const surfaceMode = surfaceModeSelect ? surfaceModeSelect.value : "delaunay";
        const checkedDomains = new Set();
        if (domainChecklist) {
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) checkedDomains.add(el.dataset.domain || "");
            });
        }
        const surfaceOpacity = opacityRange ? Number(opacityRange.value || "0.2") : 0.2;
        if (opacityLabel) opacityLabel.textContent = surfaceOpacity.toFixed(2);

        const traces = [];
        groups.forEach((pts, domain) => {
            if (selectedDomain !== "all" && domain !== selectedDomain) {
                return;
            }
            if (checkedDomains.size && !checkedDomains.has(domain)) {
                return;
            }
            const x = pts.map((p) => p.x);
            const y = pts.map((p) => p.y);
            const z = pts.map((p) => p.z);
            const color = colorForDomain(domain);

            if (showPoints) {
                traces.push({
                    type: "scatter3d",
                    mode: "markers",
                    x, y, z,
                    marker: { size: 4, color, opacity: 0.9 },
                    name: `Pontos: ${domain}`,
                    hovertemplate: "X=%{x:.2f}<br>Y=%{y:.2f}<br>Z=%{z:.2f}<extra></extra>",
                });
            }

            if (showSurface && pts.length >= 3) {
                traces.push({
                    type: "mesh3d",
                    x, y, z,
                    alphahull: surfaceMode === "hull" ? 0 : -1,
                    delaunayaxis: "z",
                    opacity: surfaceOpacity,
                    color,
                    name: `Superfície aprox.: ${domain}`,
                    hoverinfo: "skip",
                    flatshading: true,
                });
            }
        });

        if (!traces.length) {
            window.Plotly.purge(plotEl);
            plotEl.innerHTML = "";
            currentPlot = null;
            stopRotateAnimation();
            stopPulseAnimation();
            setStatus("Sem pontos para o domínio selecionado.", true);
            if (analyticsEl) analyticsEl.classList.add("hidden");
            return;
        }

        const filteredPoints = [];
        groups.forEach((pts, domain) => {
            if (selectedDomain !== "all" && domain !== selectedDomain) return;
            if (checkedDomains.size && !checkedDomains.has(domain)) return;
            filteredPoints.push(...pts);
        });

        const layout = {
            margin: { l: 0, r: 0, t: 30, b: 0 },
            paper_bgcolor: "#ffffff",
            plot_bgcolor: "#ffffff",
            title: { text: `Implicit Model: ${name}`, x: 0.02, xanchor: "left", font: { size: 14 } },
            scene: {
                xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#e2e8f0" },
                aspectmode: "data",
                camera: previousCamera || { eye: { x: 1.35, y: 1.35, z: 0.9 } },
            },
            legend: { orientation: "h", y: 0.96, yanchor: "top", x: 0 },
        };

        window.Plotly.newPlot(plotEl, traces, layout, { responsive: true, displaylogo: false });
        currentPlot = plotEl;
        setStatus(`Renderização concluída: ${points.length} pontos e ${groups.size} domínio(s).`, false);
        syncAnimations();
        persistUiConfig();
        scheduleServerUiConfigSync();
        atualizarResumoAnalitico(filteredPoints);
    }

    function atualizarResumoAnalitico(points) {
        if (!analyticsEl || !metricXEl || !metricYEl || !metricZEl || !metricVolEl) return;
        if (!Array.isArray(points) || !points.length) {
            analyticsEl.classList.add("hidden");
            return;
        }
        const xs = points.map((p) => p.x);
        const ys = points.map((p) => p.y);
        const zs = points.map((p) => p.z);
        const xMin = Math.min(...xs);
        const xMax = Math.max(...xs);
        const yMin = Math.min(...ys);
        const yMax = Math.max(...ys);
        const zMin = Math.min(...zs);
        const zMax = Math.max(...zs);
        const dx = xMax - xMin;
        const dy = yMax - yMin;
        const dz = zMax - zMin;
        const volume = Math.max(dx, 0) * Math.max(dy, 0) * Math.max(dz, 0);

        metricXEl.textContent = `${dx.toFixed(2)} m`;
        metricYEl.textContent = `${dy.toFixed(2)} m`;
        metricZEl.textContent = `${dz.toFixed(2)} m`;
        metricVolEl.textContent = `${volume.toFixed(2)} m³`;

        if (domainMetricsEl) {
            const rows = calcularResumoDominios(points);
            domainMetricsEl.innerHTML = rows.map((row) => (
                `<div class="flex items-center justify-between rounded-md border border-slate-200 bg-white px-2 py-1">
                    <span><strong>${row.domain}</strong> · ${row.points} pts</span>
                    <span>${row.volume.toFixed(2)} m³</span>
                </div>`
            )).join("");
        }
        analyticsEl.classList.remove("hidden");
    }

    function obterPontosFiltradosAtuais() {
        if (!currentPoints.length) return [];
        const selectedDomain = domainFilter ? domainFilter.value : "all";
        const checkedDomains = new Set();
        if (domainChecklist) {
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) checkedDomains.add(el.dataset.domain || "");
            });
        }
        return currentPoints.filter((p) => {
            const domain = p.dominio || "default";
            if (selectedDomain !== "all" && domain !== selectedDomain) return false;
            if (checkedDomains.size && !checkedDomains.has(domain)) return false;
            return true;
        });
    }

    function calcularResumoDominios(points) {
        const grouped = new Map();
        (points || []).forEach((p) => {
            const d = p.dominio || "default";
            if (!grouped.has(d)) grouped.set(d, []);
            grouped.get(d).push(p);
        });
        const rows = [];
        grouped.forEach((list, domain) => {
            const dxs = list.map((p) => p.x);
            const dys = list.map((p) => p.y);
            const dzs = list.map((p) => p.z);
            const ddx = Math.max(...dxs) - Math.min(...dxs);
            const ddy = Math.max(...dys) - Math.min(...dys);
            const ddz = Math.max(...dzs) - Math.min(...dzs);
            const dvol = Math.max(ddx, 0) * Math.max(ddy, 0) * Math.max(ddz, 0);
            rows.push({
                domain,
                points: list.length,
                volume: dvol,
                dx: ddx,
                dy: ddy,
                dz: ddz,
            });
        });
        rows.sort((a, b) => b.volume - a.volume);
        return rows;
    }

    function exportarCsvSelecao() {
        const points = obterPontosFiltradosAtuais();
        if (!points.length) {
            setStatus("Não há pontos filtrados para exportar.", true);
            return;
        }
        const pontosHeader = "x,y,z,dominio";
        const pontosRows = points.map((p) => `${p.x},${p.y},${p.z},${String(p.dominio || "default").replace(/,/g, " ")}`);
        const resumo = calcularResumoDominios(points);
        const resumoHeader = "dominio,pontos,extensao_x_m,extensao_y_m,extensao_z_m,volume_m3";
        const resumoRows = resumo.map((r) => (
            `${String(r.domain).replace(/,/g, " ")},${r.points},${r.dx.toFixed(4)},${r.dy.toFixed(4)},${r.dz.toFixed(4)},${r.volume.toFixed(4)}`
        ));
        const csv = [
            "# pontos_filtrados",
            pontosHeader,
            ...pontosRows,
            "",
            "# resumo_por_dominio_bounding_box",
            resumoHeader,
            ...resumoRows,
        ].join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        a.href = url;
        a.download = `implicit-model-filtrado-${ts}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setStatus(`CSV exportado com ${points.length} ponto(s) + resumo por domínio.`, false);
    }

    function exportarJsonTecnico() {
        const points = obterPontosFiltradosAtuais();
        if (!points.length) {
            setStatus("Não há pontos filtrados para exportar.", true);
            return;
        }
        const resumo = calcularResumoDominios(points);
        const payload = {
            tipo: "implicit_model_export",
            versao: "1.0",
            exportado_em: new Date().toISOString(),
            filtros_ativos: readUiConfig(),
            totais: {
                pontos: points.length,
                dominios: new Set(points.map((p) => p.dominio || "default")).size,
            },
            resumo_por_dominio: resumo.map((r) => ({
                dominio: r.domain,
                pontos: r.points,
                extensao_x_m: Number(r.dx.toFixed(4)),
                extensao_y_m: Number(r.dy.toFixed(4)),
                extensao_z_m: Number(r.dz.toFixed(4)),
                volume_m3_estimado: Number(r.volume.toFixed(4)),
            })),
            pontos_filtrados: points.map((p) => ({
                x: p.x,
                y: p.y,
                z: p.z,
                dominio: p.dominio || "default",
            })),
        };
        const json = JSON.stringify(payload, null, 2);
        const blob = new Blob([json], { type: "application/json;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        a.href = url;
        a.download = `implicit-model-tecnico-${ts}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setStatus(`JSON técnico exportado com ${points.length} ponto(s).`, false);
    }

    function rebuildDomainFilter(points) {
        if (!domainFilter) return;
        const current = domainFilter.value || "all";
        const domains = Array.from(new Set(points.map((p) => p.dominio || "default"))).sort();
        domainFilter.innerHTML = "";
        const allOption = document.createElement("option");
        allOption.value = "all";
        allOption.textContent = "Todos os domínios";
        domainFilter.appendChild(allOption);
        domains.forEach((domain) => {
            const opt = document.createElement("option");
            opt.value = domain;
            opt.textContent = domain;
            domainFilter.appendChild(opt);
        });
        domainFilter.value = domains.includes(current) || current === "all" ? current : "all";

        if (domainChecklist) {
            const previouslyChecked = new Set();
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) previouslyChecked.add(el.dataset.domain || "");
            });
            domainChecklist.innerHTML = "";
            domains.forEach((domain) => {
                const label = document.createElement("label");
                label.className = "inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-700";
                const input = document.createElement("input");
                input.type = "checkbox";
                input.dataset.domain = domain;
                input.checked = previouslyChecked.size ? previouslyChecked.has(domain) : true;
                input.addEventListener("change", () => {
                    if (!currentPoints.length) return;
                    renderImplicit(currentPoints, "Implicit Model");
                });
                const text = document.createElement("span");
                text.textContent = domain;
                label.appendChild(input);
                label.appendChild(text);
                domainChecklist.appendChild(label);
            });
        }
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

    if (uploadForm) uploadForm.addEventListener("submit", savePlotState);
    restorePlotState();
    syncAnimations();

    function applyCamera(view) {
        if (!currentPlot) return;
        const cameras = {
            iso: { eye: { x: 1.35, y: 1.35, z: 0.9 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
            top: { eye: { x: 0.001, y: 0.001, z: 2.4 }, up: { x: 0, y: 1, z: 0 }, center: { x: 0, y: 0, z: 0 } },
            side: { eye: { x: 2.4, y: 0.001, z: 0.001 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
            front: { eye: { x: 0.001, y: 2.4, z: 0.001 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
        };
        window.Plotly.relayout(currentPlot, { "scene.camera": cameras[view] || cameras.iso });
    }

    cameraButtons.forEach((button) => {
        button.addEventListener("click", () => {
            applyCamera(button.dataset.implicitCamera || "iso");
        });
    });

    if (exportPngBtn) {
        exportPngBtn.addEventListener("click", () => {
            if (!currentPlot) {
                setStatus("Não há gráfico para exportar.", true);
                return;
            }
            window.Plotly.downloadImage(currentPlot, {
                format: "png",
                filename: "implicit-model-3d",
                width: 1600,
                height: 1000,
                scale: 1,
            });
        });
    }
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", exportarCsvSelecao);
    }
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener("click", exportarJsonTecnico);
    }
    if (animRotateToggle) animRotateToggle.addEventListener("change", syncAnimations);
    if (animPulseToggle) animPulseToggle.addEventListener("change", syncAnimations);

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        currentStateScope = "temp";
        currentConfigUrl = "";
        pendingServerUiConfig = null;
        const name = file.name || "";
        const extension = name.includes(".") ? `.${name.split(".").pop().toLowerCase()}` : "";
        setStatus("A processar pontos geológicos…", false);
        const reader = new FileReader();
        reader.onload = () => {
            const text = String(reader.result || "");
            const points = extension === ".csv" ? parseCsv(text) : extension === ".json" ? parseJson(text) : [];
            if (!points.length) {
                setStatus("Formato inválido ou sem pontos válidos.", true);
                return;
            }
            rebuildDomainFilter(points);
            applyUiConfig(loadUiConfig());
            renderImplicit(points, name);
        };
        reader.onerror = () => setStatus("Não foi possível ler o ficheiro.", true);
        reader.readAsText(file);
    });

    reopenButtons.forEach((button) => {
        button.addEventListener("click", async () => {
            const url = button.dataset.reopenImplicitUrl || "";
            const modelId = button.dataset.reopenImplicitId || "";
            const configUrl = button.dataset.reopenImplicitConfigUrl || "";
            const formato = (button.dataset.reopenImplicitFormato || "").toLowerCase();
            const name = button.dataset.reopenImplicitName || "implicit-model";
            if (!url || (formato !== "csv" && formato !== "json")) {
                setStatus("Não foi possível reabrir este modelo implícito.", true);
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
                rebuildDomainFilter(points);
                if (pendingServerUiConfig) {
                    applyUiConfig(pendingServerUiConfig);
                    pendingServerUiConfig = null;
                } else {
                    applyUiConfig(loadUiConfig());
                }
                renderImplicit(points, name);
            } catch (error) {
                setStatus(`Erro ao reabrir modelo implícito: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        });
    });

    if (domainFilter) {
        domainFilter.addEventListener("change", () => {
            if (!currentPoints.length) return;
            renderImplicit(currentPoints, "Implicit Model");
        });
    }
    if (selectAllDomainsBtn) {
        selectAllDomainsBtn.addEventListener("click", () => {
            if (!domainChecklist) return;
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                el.checked = true;
            });
            if (currentPoints.length) {
                renderImplicit(currentPoints, "Implicit Model");
            }
        });
    }
    if (clearDomainsBtn) {
        clearDomainsBtn.addEventListener("click", () => {
            if (!domainChecklist) return;
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                el.checked = false;
            });
            if (currentPoints.length) {
                renderImplicit(currentPoints, "Implicit Model");
            }
        });
    }
    if (opacityRange) {
        opacityRange.addEventListener("input", () => {
            if (!currentPoints.length) {
                if (opacityLabel) opacityLabel.textContent = Number(opacityRange.value || 0).toFixed(2);
                persistUiConfig();
                return;
            }
            renderImplicit(currentPoints, "Implicit Model");
        });
    }
    if (showPointsToggle) {
        showPointsToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            renderImplicit(currentPoints, "Implicit Model");
        });
    }
    if (showSurfaceToggle) {
        showSurfaceToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            renderImplicit(currentPoints, "Implicit Model");
        });
    }
    if (surfaceModeSelect) {
        surfaceModeSelect.addEventListener("change", () => {
            if (!currentPoints.length) return;
            renderImplicit(currentPoints, "Implicit Model");
        });
    }
})();
