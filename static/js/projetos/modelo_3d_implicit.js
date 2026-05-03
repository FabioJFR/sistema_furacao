(function () {
    "use strict";

    const fileInput = document.querySelector('input[name="implicit_file"]');
    const plotEl = document.getElementById("implicit-3d-plot");
    const statusEl = document.getElementById("implicit-3d-status");
    const reopenButtons = document.querySelectorAll("[data-reopen-implicit-url]");
    const cameraButtons = document.querySelectorAll("[data-implicit-camera]");
    const focusSelectionBtn = document.getElementById("implicitFocusSelectionBtn");
    const clearFocusBtn = document.getElementById("implicitClearFocusBtn");
    const exportPngBtn = document.getElementById("implicitExportPngBtn");
    const exportCsvBtn = document.getElementById("implicitExportCsvBtn");
    const exportJsonBtn = document.getElementById("implicitExportJsonBtn");
    const animRotateToggle = document.getElementById("implicitAnimRotateToggle");
    const animPulseToggle = document.getElementById("implicitAnimPulseToggle");
    const pulseIntensityRange = document.getElementById("implicitPulseIntensityRange");
    const pulseIntensityLabel = document.getElementById("implicitPulseIntensityLabel");
    const uploadForm = document.getElementById("implicit-upload-form");
    const domainFilter = document.getElementById("implicitDomainFilter");
    const domainChecklist = document.getElementById("implicitDomainChecklist");
    const selectAllDomainsBtn = document.getElementById("implicitSelectAllDomainsBtn");
    const clearDomainsBtn = document.getElementById("implicitClearDomainsBtn");
    const showPointsToggle = document.getElementById("implicitShowPointsToggle");
    const showSurfaceToggle = document.getElementById("implicitShowSurfaceToggle");
    const showEstimatedVolumesToggle = document.getElementById("implicitShowEstimatedVolumesToggle");
    const surfaceModeSelect = document.getElementById("implicitSurfaceMode");
    const opacityRange = document.getElementById("implicitOpacityRange");
    const opacityLabel = document.getElementById("implicitOpacityLabel");
    const zoneThicknessRange = document.getElementById("implicitZoneThicknessRange");
    const zoneThicknessLabel = document.getElementById("implicitZoneThicknessLabel");
    const extrudeModeSelect = document.getElementById("implicitExtrudeMode");
    const smoothSurfaceToggle = document.getElementById("implicitSmoothSurfaceToggle");
    const smoothLevelRange = document.getElementById("implicitSmoothLevelRange");
    const smoothLevelLabel = document.getElementById("implicitSmoothLevelLabel");
    const showContoursToggle = document.getElementById("implicitShowContoursToggle");
    const contourAxisSelect = document.getElementById("implicitContourAxis");
    const contourLevelsRange = document.getElementById("implicitContourLevelsRange");
    const contourLevelsLabel = document.getElementById("implicitContourLevelsLabel");
    const contourIntensityRange = document.getElementById("implicitContourIntensityRange");
    const contourIntensityLabel = document.getElementById("implicitContourIntensityLabel");
    const contoursHighContrastToggle = document.getElementById("implicitContoursHighContrastToggle");
    const compareEnabledToggle = document.getElementById("implicitCompareEnabled");
    const compareShowPointsToggle = document.getElementById("implicitCompareShowPoints");
    const compareShowSurfaceToggle = document.getElementById("implicitCompareShowSurface");
    const compareShowDeltaToggle = document.getElementById("implicitCompareShowDelta");
    const compareShowDeltaShellToggle = document.getElementById("implicitCompareShowDeltaShell");
    const compareDeltaShellOpacityRange = document.getElementById("implicitCompareDeltaShellOpacity");
    const compareDeltaShellOpacityLabel = document.getElementById("implicitCompareDeltaShellOpacityLabel");
    const compareDeltaMarkerSizeRange = document.getElementById("implicitCompareDeltaMarkerSize");
    const compareDeltaMarkerSizeLabel = document.getElementById("implicitCompareDeltaMarkerSizeLabel");
    const compareModelASelect = document.getElementById("implicitCompareModelA");
    const compareModelBSelect = document.getElementById("implicitCompareModelB");
    const compareStatusEl = document.getElementById("implicitCompareStatus");
    const compareSummaryEl = document.getElementById("implicitCompareSummary");
    const compareSummaryBodyEl = document.getElementById("implicitCompareSummaryBody");
    const presetOperationalBtn = document.getElementById("implicitPresetOperationalBtn");
    const presetGeologyBtn = document.getElementById("implicitPresetGeologyBtn");
    const presetSupervisionBtn = document.getElementById("implicitPresetSupervisionBtn");
    const sliceEnabledToggle = document.getElementById("implicitSliceEnabled");
    const sliceAxisSelect = document.getElementById("implicitSliceAxis");
    const sliceValueRange = document.getElementById("implicitSliceValue");
    const sliceValueLabel = document.getElementById("implicitSliceValueLabel");
    const sliceInfoEl = document.getElementById("implicitSliceInfo");
    const analyticsEl = document.getElementById("implicit-analytics");
    const contoursLegendEl = document.getElementById("implicitContoursLegend");
    const contoursLegendBodyEl = document.getElementById("implicitContoursLegendBody");
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
    let pulseBaseState = null;
    let pulseFramePending = false;
    let plotUserInteracting = false;
    let plotInteractionReleaseTimer = null;
    let rotateAngle = 0;
    let pulseT = 0;
    let sliceUiLock = false;
    let currentModelName = "Implicit Model";
    const savedModelsIndex = new Map();
    const savedModelPointsCache = new Map();
    let compareModelBPoints = null;
    let compareModelBName = "";

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
            showEstimatedVolumes: showEstimatedVolumesToggle ? !!showEstimatedVolumesToggle.checked : true,
            surfaceMode: surfaceModeSelect ? (surfaceModeSelect.value || "delaunay") : "delaunay",
            opacity: opacityRange ? Number(opacityRange.value || "0.2") : 0.2,
            zoneThicknessFactor: zoneThicknessRange ? Number(zoneThicknessRange.value || "0.12") : 0.12,
            extrudeMode: extrudeModeSelect ? (extrudeModeSelect.value || "auto") : "auto",
            smoothSurface: smoothSurfaceToggle ? !!smoothSurfaceToggle.checked : false,
            smoothLevel: smoothLevelRange ? Number(smoothLevelRange.value || "1") : 1,
            showContours: showContoursToggle ? !!showContoursToggle.checked : false,
            contourAxis: contourAxisSelect ? (contourAxisSelect.value || "z") : "z",
            contourLevels: contourLevelsRange ? Number(contourLevelsRange.value || "6") : 6,
            contourIntensity: contourIntensityRange ? Number(contourIntensityRange.value || "1.0") : 1.0,
            contoursHighContrast: contoursHighContrastToggle ? !!contoursHighContrastToggle.checked : false,
            selectedDomain: domainFilter ? (domainFilter.value || "all") : "all",
            checkedDomains: domainChecks,
            rotateAnim: animRotateToggle ? !!animRotateToggle.checked : false,
            pulseAnim: animPulseToggle ? !!animPulseToggle.checked : false,
            pulseIntensity: pulseIntensityRange ? Number(pulseIntensityRange.value || "1") : 1,
            sliceEnabled: sliceEnabledToggle ? !!sliceEnabledToggle.checked : false,
            sliceAxis: sliceAxisSelect ? (sliceAxisSelect.value || "x") : "x",
            sliceValue: sliceValueRange ? Number(sliceValueRange.value || "0") : 0,
            compareEnabled: compareEnabledToggle ? !!compareEnabledToggle.checked : false,
            compareShowPoints: compareShowPointsToggle ? !!compareShowPointsToggle.checked : true,
            compareShowSurface: compareShowSurfaceToggle ? !!compareShowSurfaceToggle.checked : true,
            compareShowDelta: compareShowDeltaToggle ? !!compareShowDeltaToggle.checked : false,
            compareShowDeltaShell: compareShowDeltaShellToggle ? !!compareShowDeltaShellToggle.checked : false,
            compareDeltaShellOpacity: compareDeltaShellOpacityRange ? Number(compareDeltaShellOpacityRange.value || "0.18") : 0.18,
            compareDeltaMarkerSize: compareDeltaMarkerSizeRange ? Number(compareDeltaMarkerSizeRange.value || "5.5") : 5.5,
            compareModelA: compareModelASelect ? (compareModelASelect.value || "current") : "current",
            compareModelB: compareModelBSelect ? (compareModelBSelect.value || "") : "",
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
        if (showEstimatedVolumesToggle && typeof config.showEstimatedVolumes === "boolean") showEstimatedVolumesToggle.checked = config.showEstimatedVolumes;
        if (surfaceModeSelect && config.surfaceMode) surfaceModeSelect.value = config.surfaceMode;
        if (opacityRange && Number.isFinite(Number(config.opacity))) opacityRange.value = String(config.opacity);
        if (opacityLabel && opacityRange) opacityLabel.textContent = Number(opacityRange.value || 0).toFixed(2);
        if (zoneThicknessRange && Number.isFinite(Number(config.zoneThicknessFactor))) zoneThicknessRange.value = String(config.zoneThicknessFactor);
        if (zoneThicknessLabel && zoneThicknessRange) zoneThicknessLabel.textContent = Number(zoneThicknessRange.value || 0).toFixed(2);
        if (extrudeModeSelect && config.extrudeMode) extrudeModeSelect.value = config.extrudeMode;
        if (smoothSurfaceToggle && typeof config.smoothSurface === "boolean") smoothSurfaceToggle.checked = config.smoothSurface;
        if (smoothLevelRange && Number.isFinite(Number(config.smoothLevel))) smoothLevelRange.value = String(config.smoothLevel);
        if (smoothLevelLabel && smoothLevelRange) smoothLevelLabel.textContent = String(Math.round(Number(smoothLevelRange.value || 1)));
        if (showContoursToggle && typeof config.showContours === "boolean") showContoursToggle.checked = config.showContours;
        if (contourAxisSelect && config.contourAxis) contourAxisSelect.value = config.contourAxis;
        if (contourLevelsRange && Number.isFinite(Number(config.contourLevels))) contourLevelsRange.value = String(config.contourLevels);
        if (contourLevelsLabel && contourLevelsRange) contourLevelsLabel.textContent = String(Math.round(Number(contourLevelsRange.value || 6)));
        if (contourIntensityRange && Number.isFinite(Number(config.contourIntensity))) contourIntensityRange.value = String(config.contourIntensity);
        if (contourIntensityLabel && contourIntensityRange) contourIntensityLabel.textContent = Number(contourIntensityRange.value || 1).toFixed(2);
        if (contoursHighContrastToggle && typeof config.contoursHighContrast === "boolean") contoursHighContrastToggle.checked = config.contoursHighContrast;
        if (animRotateToggle && typeof config.rotateAnim === "boolean") animRotateToggle.checked = config.rotateAnim;
        if (animPulseToggle && typeof config.pulseAnim === "boolean") animPulseToggle.checked = config.pulseAnim;
        if (pulseIntensityRange && Number.isFinite(Number(config.pulseIntensity))) pulseIntensityRange.value = String(config.pulseIntensity);
        if (pulseIntensityLabel && pulseIntensityRange) pulseIntensityLabel.textContent = Number(pulseIntensityRange.value || 1).toFixed(2);
        if (sliceEnabledToggle && typeof config.sliceEnabled === "boolean") sliceEnabledToggle.checked = config.sliceEnabled;
        if (sliceAxisSelect && config.sliceAxis) sliceAxisSelect.value = config.sliceAxis;
        if (sliceValueRange && Number.isFinite(Number(config.sliceValue))) sliceValueRange.value = String(config.sliceValue);
        if (sliceValueLabel && sliceValueRange) sliceValueLabel.textContent = Number(sliceValueRange.value || 0).toFixed(2);
        if (compareEnabledToggle && typeof config.compareEnabled === "boolean") compareEnabledToggle.checked = config.compareEnabled;
        if (compareShowPointsToggle && typeof config.compareShowPoints === "boolean") compareShowPointsToggle.checked = config.compareShowPoints;
        if (compareShowSurfaceToggle && typeof config.compareShowSurface === "boolean") compareShowSurfaceToggle.checked = config.compareShowSurface;
        if (compareShowDeltaToggle && typeof config.compareShowDelta === "boolean") compareShowDeltaToggle.checked = config.compareShowDelta;
        if (compareShowDeltaShellToggle && typeof config.compareShowDeltaShell === "boolean") compareShowDeltaShellToggle.checked = config.compareShowDeltaShell;
        if (compareDeltaShellOpacityRange && Number.isFinite(Number(config.compareDeltaShellOpacity))) {
            compareDeltaShellOpacityRange.value = String(config.compareDeltaShellOpacity);
        }
        if (compareDeltaShellOpacityLabel && compareDeltaShellOpacityRange) {
            compareDeltaShellOpacityLabel.textContent = Number(compareDeltaShellOpacityRange.value || 0.18).toFixed(2);
        }
        if (compareDeltaMarkerSizeRange && Number.isFinite(Number(config.compareDeltaMarkerSize))) {
            compareDeltaMarkerSizeRange.value = String(config.compareDeltaMarkerSize);
        }
        if (compareDeltaMarkerSizeLabel && compareDeltaMarkerSizeRange) {
            compareDeltaMarkerSizeLabel.textContent = Number(compareDeltaMarkerSizeRange.value || 5.5).toFixed(1);
        }
        if (compareModelASelect && config.compareModelA) compareModelASelect.value = config.compareModelA;
        if (compareModelBSelect && config.compareModelB) compareModelBSelect.value = config.compareModelB;
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
        pulseFramePending = false;
        if (!currentPlot || !pulseBaseState) {
            pulseBaseState = null;
            return;
        }
        const scatterIdx = [];
        const scatterSizes = [];
        const scatterColors = [];
        pulseBaseState.scatter.forEach((item) => {
            if (!Number.isInteger(item.idx)) return;
            scatterIdx.push(item.idx);
            scatterSizes.push(item.size);
            scatterColors.push(item.color);
        });
        if (scatterIdx.length) {
            window.Plotly.restyle(
                currentPlot,
                { "marker.size": scatterSizes, "marker.color": scatterColors },
                scatterIdx,
            );
        }

        const meshIdx = [];
        const meshOpacities = [];
        const meshColors = [];
        pulseBaseState.mesh.forEach((item) => {
            if (!Number.isInteger(item.idx)) return;
            meshIdx.push(item.idx);
            meshOpacities.push(item.opacity);
            meshColors.push(item.color);
        });
        if (meshIdx.length) {
            window.Plotly.restyle(
                currentPlot,
                { opacity: meshOpacities, color: meshColors },
                meshIdx,
            );
        }
        pulseBaseState = null;
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
        pulseBaseState = { scatter: [], mesh: [] };
        (currentPlot.data || []).forEach((trace, idx) => {
            if (trace.type === "scatter3d") {
                const rawSize = Number(trace?.marker?.size);
                pulseBaseState.scatter.push({
                    idx,
                    size: Number.isFinite(rawSize) ? rawSize : 3.5,
                    color: trace?.marker?.color,
                });
            } else if (trace.type === "mesh3d") {
                const rawOpacity = Number(trace.opacity);
                pulseBaseState.mesh.push({
                    idx,
                    opacity: Number.isFinite(rawOpacity) ? rawOpacity : 0.2,
                    color: trace?.color,
                });
            }
        });
        const shouldAnimateMesh = pulseBaseState.mesh.length > 0 && pulseBaseState.mesh.length <= 4;
        pulseT = 0;
        pulseTimer = window.setInterval(() => {
            if (plotUserInteracting) return;
            if (pulseFramePending) return;
            pulseFramePending = true;
            try {
                pulseT += 0.2;
                const pulse = Math.sin(pulseT);
                const intensity = pulseIntensityRange ? Number(pulseIntensityRange.value || "1") : 1;
                const safeIntensity = Number.isFinite(intensity) ? Math.max(0.2, Math.min(3, intensity)) : 1;
                const scatterIdx = [];
                const scatterSizes = [];
                const scatterColors = [];
                (pulseBaseState?.scatter || []).forEach((item) => {
                    scatterIdx.push(item.idx);
                    scatterSizes.push(Math.max(2.2, item.size + pulse * (2.6 * safeIntensity)));
                    scatterColors.push(pulseColorAny(item.color, pulse * (0.42 * safeIntensity)));
                });
                if (scatterIdx.length) {
                    window.Plotly.restyle(
                        currentPlot,
                        { "marker.size": scatterSizes, "marker.color": scatterColors },
                        scatterIdx,
                    );
                }

                if (shouldAnimateMesh) {
                    const meshPulse = Math.sin(pulseT + 0.5) * (0.14 * safeIntensity);
                    const meshIdx = [];
                    const meshOpacities = [];
                    const meshColors = [];
                    (pulseBaseState?.mesh || []).forEach((item) => {
                        meshIdx.push(item.idx);
                        meshOpacities.push(Math.max(0.06, Math.min(0.96, item.opacity + meshPulse)));
                        meshColors.push(pulseColorAny(item.color, pulse * (0.34 * safeIntensity)));
                    });
                    if (meshIdx.length) {
                        window.Plotly.restyle(
                            currentPlot,
                            { opacity: meshOpacities, color: meshColors },
                            meshIdx,
                        );
                    }
                }
                pulseFramePending = false;
            } catch (err) {
                stopPulseAnimation();
                if (animPulseToggle) animPulseToggle.checked = false;
                setStatus("Erro na animação de pulso. A animação foi desativada automaticamente.", true);
                pulseFramePending = false;
            }
        }, 170);
        setStatus("Animação ativa: pulso em pontos/superfícies.", false);
    }

    function markPlotInteraction() {
        plotUserInteracting = true;
        if (plotInteractionReleaseTimer) {
            window.clearTimeout(plotInteractionReleaseTimer);
            plotInteractionReleaseTimer = null;
        }
    }

    function releasePlotInteractionSoon() {
        if (plotInteractionReleaseTimer) window.clearTimeout(plotInteractionReleaseTimer);
        plotInteractionReleaseTimer = window.setTimeout(() => {
            plotUserInteracting = false;
        }, 220);
    }

    function bindPlotInteractionGuards() {
        if (!plotEl) return;
        plotEl.onmousedown = markPlotInteraction;
        plotEl.ontouchstart = markPlotInteraction;
        plotEl.onwheel = markPlotInteraction;
        plotEl.onmouseup = releasePlotInteractionSoon;
        plotEl.ontouchend = releasePlotInteractionSoon;
        plotEl.onmouseleave = releasePlotInteractionSoon;
        if (typeof plotEl.on === "function") {
            plotEl.on("plotly_relayouting", markPlotInteraction);
            plotEl.on("plotly_relayout", releasePlotInteractionSoon);
        }
    }

    function syncAnimations() {
        if (animRotateToggle && animRotateToggle.checked) startRotateAnimation();
        else stopRotateAnimation();
        if (animPulseToggle && animPulseToggle.checked) startPulseAnimation();
        else {
            stopPulseAnimation();
            setStatus("Animação de pulso desativada.", false);
        }
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

    function parseCssColorToRgb(color) {
        if (typeof color !== "string") return null;
        const raw = color.trim();
        if (!raw) return null;
        const hex = raw.startsWith("#") ? raw.slice(1) : raw;
        if (/^[0-9a-fA-F]{3}$/.test(hex)) {
            return {
                r: parseInt(hex[0] + hex[0], 16),
                g: parseInt(hex[1] + hex[1], 16),
                b: parseInt(hex[2] + hex[2], 16),
            };
        }
        if (/^[0-9a-fA-F]{6}$/.test(hex)) {
            return {
                r: parseInt(hex.slice(0, 2), 16),
                g: parseInt(hex.slice(2, 4), 16),
                b: parseInt(hex.slice(4, 6), 16),
            };
        }
        const rgbMatch = raw.match(/^rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)/i);
        if (rgbMatch) {
            return {
                r: Math.max(0, Math.min(255, Number(rgbMatch[1]))),
                g: Math.max(0, Math.min(255, Number(rgbMatch[2]))),
                b: Math.max(0, Math.min(255, Number(rgbMatch[3]))),
            };
        }
        return null;
    }

    function rgbToHex(rgb) {
        if (!rgb) return null;
        const toHex = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0");
        return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
    }

    function pulseColor(baseColor, pulseFactor) {
        const rgb = parseCssColorToRgb(baseColor);
        if (!rgb) return baseColor;
        const shift = Math.max(-0.55, Math.min(0.55, pulseFactor));
        const out = shift >= 0
            ? {
                r: rgb.r + (255 - rgb.r) * shift,
                g: rgb.g + (255 - rgb.g) * shift,
                b: rgb.b + (255 - rgb.b) * shift,
            }
            : {
                r: rgb.r * (1 + shift),
                g: rgb.g * (1 + shift),
                b: rgb.b * (1 + shift),
            };
        return rgbToHex(out) || baseColor;
    }

    function pulseColorAny(baseColor, pulseFactor) {
        if (Array.isArray(baseColor)) {
            return baseColor.map((c) => pulseColor(c, pulseFactor));
        }
        return pulseColor(baseColor, pulseFactor);
    }

    function updateSliceRange(points) {
        if (!sliceValueRange || !sliceValueLabel || !sliceAxisSelect || !Array.isArray(points) || !points.length) return;
        const axis = (sliceAxisSelect.value || "x").toLowerCase();
        const values = points.map((p) => Number(p[axis])).filter((v) => Number.isFinite(v));
        if (!values.length) return;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const span = Math.max(max - min, 0.0001);
        const step = Math.max(span / 500, 0.001);
        const current = Number(sliceValueRange.value || min);
        const clamped = Math.min(max, Math.max(min, current));
        sliceUiLock = true;
        sliceValueRange.min = String(min);
        sliceValueRange.max = String(max);
        sliceValueRange.step = String(step);
        sliceValueRange.value = String(clamped);
        sliceValueLabel.textContent = clamped.toFixed(2);
        sliceUiLock = false;
    }

    function applySliceFilter(points) {
        if (!Array.isArray(points) || !points.length) return [];
        if (!sliceEnabledToggle || !sliceEnabledToggle.checked || !sliceAxisSelect || !sliceValueRange) return points.slice();
        const axis = (sliceAxisSelect.value || "x").toLowerCase();
        const pivot = Number(sliceValueRange.value || "0");
        const eps = Number(sliceValueRange.step || "0.1") * 2;
        return points.filter((p) => Number(p[axis]) <= (pivot + eps));
    }

    function norm3(v) {
        const m = Math.hypot(v.x, v.y, v.z);
        if (m <= 1e-9) return null;
        return { x: v.x / m, y: v.y / m, z: v.z / m };
    }

    function cross3(a, b) {
        return {
            x: a.y * b.z - a.z * b.y,
            y: a.z * b.x - a.x * b.z,
            z: a.x * b.y - a.y * b.x,
        };
    }

    function pickFourPoints(pts) {
        if (pts.length <= 4) return pts.slice(0, 4);
        const chosen = [pts[0]];
        while (chosen.length < 4) {
            let best = null;
            let bestScore = -1;
            for (let i = 0; i < pts.length; i += 1) {
                const p = pts[i];
                if (chosen.includes(p)) continue;
                let minDist = Infinity;
                for (let j = 0; j < chosen.length; j += 1) {
                    const c = chosen[j];
                    const d = Math.hypot(p.x - c.x, p.y - c.y, p.z - c.z);
                    if (d < minDist) minDist = d;
                }
                if (minDist > bestScore) {
                    bestScore = minDist;
                    best = p;
                }
            }
            if (!best) break;
            chosen.push(best);
        }
        return chosen.slice(0, 4);
    }

    function buildDomainPerpendicularZoneMesh(pts, color, opacity, thicknessFactor, extrudeDirection) {
        if (!Array.isArray(pts) || pts.length < 4) return null;
        const base = pickFourPoints(pts);
        if (base.length < 4) return null;

        const v1 = { x: base[1].x - base[0].x, y: base[1].y - base[0].y, z: base[1].z - base[0].z };
        const v2 = { x: base[2].x - base[0].x, y: base[2].y - base[0].y, z: base[2].z - base[0].z };
        let n = norm3(cross3(v1, v2));
        if (!n) {
            const v3 = { x: base[3].x - base[0].x, y: base[3].y - base[0].y, z: base[3].z - base[0].z };
            n = norm3(cross3(v1, v3));
        }
        if (!n) return null;

        const xs = base.map((p) => p.x);
        const ys = base.map((p) => p.y);
        const zs = base.map((p) => p.z);
        const span = Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), Math.max(...zs) - Math.min(...zs));
        const factor = Number.isFinite(Number(thicknessFactor)) ? Number(thicknessFactor) : 0.12;
        const thickness = Math.max(span * Math.max(0.01, factor), 0.5);
        // Extrusão unidirecional baseada na referência geológica (ex.: solo topo -> crescer para baixo).
        const dir = extrudeDirection === "up" ? 1 : -1;
        const shifted = base.map((p) => ({ x: p.x, y: p.y, z: p.z + (dir * thickness) }));
        const verts = [...base, ...shifted];

        const x = verts.map((p) => p.x);
        const y = verts.map((p) => p.y);
        const z = verts.map((p) => p.z);

        const i = [
            0, 0,      // face original
            4, 4,      // face extrudida
            0, 0,      // side 0-1
            1, 1,      // side 1-2
            2, 2,      // side 2-3
            3, 3,      // side 3-0
        ];
        const j = [
            1, 2,
            5, 6,
            1, 5,
            2, 6,
            3, 7,
            0, 4,
        ];
        const k = [
            2, 3,
            6, 7,
            5, 4,
            6, 5,
            7, 6,
            4, 7,
        ];

        return { x, y, z, i, j, k, color, opacity: Math.max(0.08, opacity * 0.42) };
    }

    function buildSlicePlaneTrace(points, axis, pivot) {
        if (!Array.isArray(points) || points.length < 2) return null;
        const xs = points.map((p) => p.x);
        const ys = points.map((p) => p.y);
        const zs = points.map((p) => p.z);
        const x0 = Math.min(...xs); const x1 = Math.max(...xs);
        const y0 = Math.min(...ys); const y1 = Math.max(...ys);
        const z0 = Math.min(...zs); const z1 = Math.max(...zs);
        let x = []; let y = []; let z = [];
        if (axis === "x") {
            x = [pivot, pivot, pivot, pivot]; y = [y0, y1, y1, y0]; z = [z0, z0, z1, z1];
        } else if (axis === "y") {
            x = [x0, x1, x1, x0]; y = [pivot, pivot, pivot, pivot]; z = [z0, z0, z1, z1];
        } else {
            x = [x0, x1, x1, x0]; y = [y0, y0, y1, y1]; z = [pivot, pivot, pivot, pivot];
        }
        return {
            type: "mesh3d",
            x, y, z,
            i: [0, 0],
            j: [1, 2],
            k: [2, 3],
            color: "#0ea5e9",
            opacity: 0.16,
            name: "Slice plane",
            hovertemplate: `${axis.toUpperCase()}=${pivot.toFixed(2)}<extra></extra>`,
            flatshading: true,
        };
    }

    function densifyDomainPoints(points, level) {
        if (!Array.isArray(points) || points.length < 3) return points;
        let out = points.slice();
        const loops = Math.max(1, Math.min(3, Number(level) || 1));
        for (let r = 0; r < loops; r += 1) {
            const extra = [];
            for (let i = 0; i < out.length; i += 1) {
                const p = out[i];
                let n1 = null; let n2 = null;
                let d1 = Infinity; let d2 = Infinity;
                for (let j = 0; j < out.length; j += 1) {
                    if (i === j) continue;
                    const q = out[j];
                    const d = Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
                    if (d < d1) {
                        d2 = d1; n2 = n1;
                        d1 = d; n1 = q;
                    } else if (d < d2) {
                        d2 = d; n2 = q;
                    }
                }
                if (n1) extra.push({ x: (p.x + n1.x) / 2, y: (p.y + n1.y) / 2, z: (p.z + n1.z) / 2, dominio: p.dominio });
                if (n2) extra.push({ x: (p.x + n2.x) / 2, y: (p.y + n2.y) / 2, z: (p.z + n2.z) / 2, dominio: p.dominio });
            }
            out = out.concat(extra);
        }
        return out;
    }

    function resolveGeologyExtrudeDirection(allPoints) {
        if (!Array.isArray(allPoints) || !allPoints.length) return "down";
        const allZ = allPoints.map((p) => Number(p.z)).filter((v) => Number.isFinite(v));
        if (!allZ.length) return "down";
        const allMin = Math.min(...allZ);
        const allMax = Math.max(...allZ);

        const soloPoints = allPoints.filter((p) => String(p.dominio || "").trim().toLowerCase() === "solo");
        if (!soloPoints.length) return "down";
        const soloZ = soloPoints.map((p) => Number(p.z)).filter((v) => Number.isFinite(v));
        if (!soloZ.length) return "down";
        const soloMin = Math.min(...soloZ);
        const soloMax = Math.max(...soloZ);

        const distToTop = Math.abs(allMax - soloMax);
        const distToBottom = Math.abs(soloMin - allMin);
        return distToTop <= distToBottom ? "down" : "up";
    }

    function buildContourTraces(points, domain, color, levelsCount, axis, intensity, highContrast) {
        if (!Array.isArray(points) || points.length < 4) return [];
        const key = axis === "x" || axis === "y" ? axis : "z";
        const values = points.map((p) => Number(p[key])).filter((v) => Number.isFinite(v));
        if (!values.length) return [];
        const vMin = Math.min(...values);
        const vMax = Math.max(...values);
        const span = vMax - vMin;
        if (!Number.isFinite(span) || span <= 0) return [];
        const n = Math.max(3, Math.min(12, Number(levelsCount) || 6));
        const step = span / (n + 1);
        const band = Math.max(step * 0.45, 0.15);
        const traces = [];
        const k = Math.max(0.6, Math.min(2.2, Number(intensity) || 1.0));
        const haloWidth = Math.round((highContrast ? 6 : 5) * k);
        const mainWidth = Math.round((highContrast ? 3.2 : 2.5) * k);
        const haloColor = highContrast ? "rgba(0,0,0,0.98)" : "rgba(255,255,255,0.95)";
        const mainColor = highContrast ? "#FDE047" : "#111827";
        for (let i = 1; i <= n; i += 1) {
            const level = vMin + (step * i);
            const ring = points.filter((p) => Math.abs(Number(p[key]) - level) <= band);
            if (ring.length < 3) continue;
            let cA = 0;
            let cB = 0;
            if (key === "z") {
                cA = ring.reduce((acc, p) => acc + p.x, 0) / ring.length;
                cB = ring.reduce((acc, p) => acc + p.y, 0) / ring.length;
                ring.sort((a, b) => Math.atan2(a.y - cB, a.x - cA) - Math.atan2(b.y - cB, b.x - cA));
            } else if (key === "x") {
                cA = ring.reduce((acc, p) => acc + p.y, 0) / ring.length;
                cB = ring.reduce((acc, p) => acc + p.z, 0) / ring.length;
                ring.sort((a, b) => Math.atan2(a.z - cB, a.y - cA) - Math.atan2(b.z - cB, b.y - cA));
            } else {
                cA = ring.reduce((acc, p) => acc + p.x, 0) / ring.length;
                cB = ring.reduce((acc, p) => acc + p.z, 0) / ring.length;
                ring.sort((a, b) => Math.atan2(a.z - cB, a.x - cA) - Math.atan2(b.z - cB, b.x - cA));
            }
            const closed = ring.concat([ring[0]]);
            traces.push({
                type: "scatter3d",
                mode: "lines",
                x: closed.map((p) => p.x),
                y: closed.map((p) => p.y),
                z: closed.map((p) => p.z),
                line: { color: haloColor, width: haloWidth, dash: "solid" },
                opacity: 0.95,
                name: `Iso-halo: ${domain}`,
                hoverinfo: "skip",
                showlegend: false,
            });
            traces.push({
                type: "scatter3d",
                mode: "lines",
                x: closed.map((p) => p.x),
                y: closed.map((p) => p.y),
                z: closed.map((p) => p.z),
                line: { color: mainColor, width: mainWidth, dash: "dot" },
                opacity: 1,
                name: `Iso-linhas: ${domain}`,
                hovertemplate: `Domínio: ${domain}<br>Nível ${key.toUpperCase()}≈${level.toFixed(2)}<extra></extra>`,
                showlegend: i === 1,
            });
        }
        return traces;
    }

    function updateContoursLegend(groups, contourAxis, contourLevels, showContours) {
        if (!contoursLegendEl || !contoursLegendBodyEl) return;
        if (!showContours || !groups || !groups.size) {
            contoursLegendEl.classList.add("hidden");
            contoursLegendBodyEl.innerHTML = "";
            return;
        }
        const axisKey = contourAxis === "x" || contourAxis === "y" ? contourAxis : "z";
        const rows = [];
        groups.forEach((pts, domain) => {
            const vals = pts.map((p) => Number(p[axisKey])).filter((v) => Number.isFinite(v));
            if (!vals.length) return;
            const vMin = Math.min(...vals);
            const vMax = Math.max(...vals);
            const color = colorForDomain(domain);
            rows.push(
                `<div class="flex items-center justify-between rounded-md border border-slate-200 px-2 py-1 bg-slate-50">
                    <span class="inline-flex items-center gap-2">
                        <span class="inline-block h-2.5 w-2.5 rounded-full" style="background:${color}"></span>
                        <strong>${domain}</strong> · eixo ${axisKey.toUpperCase()}
                    </span>
                    <span>${vMin.toFixed(2)} → ${vMax.toFixed(2)} · ${Math.round(contourLevels)} níveis</span>
                </div>`
            );
        });
        if (!rows.length) {
            contoursLegendEl.classList.add("hidden");
            contoursLegendBodyEl.innerHTML = "";
            return;
        }
        contoursLegendBodyEl.innerHTML = rows.join("");
        contoursLegendEl.classList.remove("hidden");
    }

    function groupByDomain(points) {
        const groups = new Map();
        (points || []).forEach((p) => {
            const key = p.dominio || "default";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(p);
        });
        return groups;
    }

    function applyCurrentDomainFilters(points) {
        const selectedDomain = domainFilter ? domainFilter.value : "all";
        const checkedDomains = new Set();
        if (domainChecklist) {
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) checkedDomains.add(el.dataset.domain || "");
            });
        }
        const domainFiltered = (points || []).filter((p) => {
            const domain = p.dominio || "default";
            if (selectedDomain !== "all" && domain !== selectedDomain) return false;
            if (checkedDomains.size && !checkedDomains.has(domain)) return false;
            return true;
        });
        return applySliceFilter(domainFiltered);
    }

    function sanitizeModelPoints(points) {
        if (!Array.isArray(points)) return [];
        return points
            .map((it) => ({ x: Number(it.x), y: Number(it.y), z: Number(it.z), dominio: it.dominio || it.domain || "default" }))
            .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z));
    }

    async function getSavedModelPoints(modelId) {
        if (!modelId || !savedModelsIndex.has(modelId)) return null;
        if (savedModelPointsCache.has(modelId)) return savedModelPointsCache.get(modelId);
        const meta = savedModelsIndex.get(modelId);
        if (!meta || !meta.url || !meta.formato) return null;
        const response = await window.fetch(meta.url, { credentials: "same-origin" });
        const text = await response.text();
        if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
        const points = meta.formato === "csv" ? parseCsv(text) : parseJson(text);
        savedModelPointsCache.set(modelId, points);
        return points;
    }

    function renderCompareSummary(pointsA, pointsB, nameA, nameB) {
        if (!compareSummaryEl || !compareSummaryBodyEl) return;
        if (!Array.isArray(pointsA) || !pointsA.length || !Array.isArray(pointsB) || !pointsB.length) {
            compareSummaryEl.classList.add("hidden");
            compareSummaryBodyEl.innerHTML = "";
            return;
        }
        const groupedA = groupByDomain(pointsA);
        const groupedB = groupByDomain(pointsB);
        const allDomains = Array.from(new Set([...groupedA.keys(), ...groupedB.keys()])).sort();
        const rows = allDomains.map((domain) => {
            const a = groupedA.get(domain) || [];
            const b = groupedB.get(domain) || [];
            const vol = (list) => {
                if (!list.length) return 0;
                const xs = list.map((p) => p.x);
                const ys = list.map((p) => p.y);
                const zs = list.map((p) => p.z);
                return Math.max(Math.max(...xs) - Math.min(...xs), 0) * Math.max(Math.max(...ys) - Math.min(...ys), 0) * Math.max(Math.max(...zs) - Math.min(...zs), 0);
            };
            const deltaPts = b.length - a.length;
            const deltaVol = vol(b) - vol(a);
            const deltaPtsStr = `${deltaPts >= 0 ? "+" : ""}${deltaPts}`;
            const deltaVolStr = `${deltaVol >= 0 ? "+" : ""}${deltaVol.toFixed(2)} m³`;
            return `<div class="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
                <span><strong>${domain}</strong> · A:${a.length} | B:${b.length}</span>
                <span>Δ pontos ${deltaPtsStr} · Δ vol ${deltaVolStr}</span>
            </div>`;
        });
        compareSummaryBodyEl.innerHTML = `
            <div class="text-[11px] text-slate-500 mb-1">A: ${nameA || "Atual"} · B: ${nameB || "Modelo B"}</div>
            ${rows.join("")}
        `;
        compareSummaryEl.classList.remove("hidden");
    }

    function pointKeyWithTolerance(p, tol) {
        const t = Math.max(0.0001, Number(tol) || 1.0);
        const rx = Math.round(Number(p.x) / t);
        const ry = Math.round(Number(p.y) / t);
        const rz = Math.round(Number(p.z) / t);
        const d = String(p.dominio || "default");
        return `${d}|${rx}|${ry}|${rz}`;
    }

    function buildSpatialDeltaTraces(pointsA, pointsB, markerSize) {
        const tolerance = 1.0;
        const size = Math.max(3, Math.min(10, Number(markerSize) || 5.5));
        const setA = new Set((pointsA || []).map((p) => pointKeyWithTolerance(p, tolerance)));
        const setB = new Set((pointsB || []).map((p) => pointKeyWithTolerance(p, tolerance)));

        const added = (pointsB || []).filter((p) => !setA.has(pointKeyWithTolerance(p, tolerance)));
        const removed = (pointsA || []).filter((p) => !setB.has(pointKeyWithTolerance(p, tolerance)));
        const traces = [];

        if (added.length) {
            traces.push({
                type: "scatter3d",
                mode: "markers",
                x: added.map((p) => p.x),
                y: added.map((p) => p.y),
                z: added.map((p) => p.z),
                marker: { size, color: "#16A34A", opacity: 0.9, symbol: "diamond-open" },
                name: "Delta + (B>A)",
                hovertemplate: "Delta +<br>X=%{x:.2f}<br>Y=%{y:.2f}<br>Z=%{z:.2f}<extra></extra>",
            });
        }
        if (removed.length) {
            traces.push({
                type: "scatter3d",
                mode: "markers",
                x: removed.map((p) => p.x),
                y: removed.map((p) => p.y),
                z: removed.map((p) => p.z),
                marker: { size, color: "#DC2626", opacity: 0.9, symbol: "x" },
                name: "Delta - (A>B)",
                hovertemplate: "Delta -<br>X=%{x:.2f}<br>Y=%{y:.2f}<br>Z=%{z:.2f}<extra></extra>",
            });
        }
        return { traces, addedCount: added.length, removedCount: removed.length, addedPoints: added, removedPoints: removed };
    }

    function buildSpatialDeltaShellTraces(addedPoints, removedPoints, shellOpacity) {
        const traces = [];
        const safeOpacity = Math.max(0.05, Math.min(0.6, Number(shellOpacity) || 0.18));
        const buildShellByDomain = (points, color, name) => {
            const grouped = groupByDomain(points || []);
            grouped.forEach((pts, domain) => {
                if (!Array.isArray(pts) || pts.length < 4) return;
                traces.push({
                    type: "mesh3d",
                    x: pts.map((p) => p.x),
                    y: pts.map((p) => p.y),
                    z: pts.map((p) => p.z),
                    alphahull: 0,
                    opacity: safeOpacity,
                    color,
                    flatshading: true,
                    name: `${name}: ${domain}`,
                    hovertemplate: `${name}<br>Domínio: ${domain}<extra></extra>`,
                });
            });
        };
        buildShellByDomain(addedPoints, "#16A34A", "Delta+ casca");
        buildShellByDomain(removedPoints, "#DC2626", "Delta- casca");
        return traces;
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

        const selectedDomain = domainFilter ? domainFilter.value : "all";
        const showPoints = !showPointsToggle || showPointsToggle.checked;
        const showSurface = !showSurfaceToggle || showSurfaceToggle.checked;
        const showEstimatedVolumes = !showEstimatedVolumesToggle || showEstimatedVolumesToggle.checked;
        const compareEnabled = !!(compareEnabledToggle && compareEnabledToggle.checked && Array.isArray(compareModelBPoints) && compareModelBPoints.length);
        const compareShowPoints = !!(compareShowPointsToggle && compareShowPointsToggle.checked);
        const compareShowSurface = !!(compareShowSurfaceToggle && compareShowSurfaceToggle.checked);
        const compareShowDelta = !!(compareShowDeltaToggle && compareShowDeltaToggle.checked);
        const compareShowDeltaShell = !!(compareShowDeltaShellToggle && compareShowDeltaShellToggle.checked);
        const compareDeltaShellOpacity = compareDeltaShellOpacityRange ? Number(compareDeltaShellOpacityRange.value || "0.18") : 0.18;
        const compareDeltaMarkerSize = compareDeltaMarkerSizeRange ? Number(compareDeltaMarkerSizeRange.value || "5.5") : 5.5;
        if (compareDeltaShellOpacityLabel && compareDeltaShellOpacityRange) {
            compareDeltaShellOpacityLabel.textContent = Number(compareDeltaShellOpacityRange.value || "0.18").toFixed(2);
        }
        if (compareDeltaMarkerSizeLabel && compareDeltaMarkerSizeRange) {
            compareDeltaMarkerSizeLabel.textContent = Number(compareDeltaMarkerSizeRange.value || "5.5").toFixed(1);
        }
        const surfaceMode = surfaceModeSelect ? surfaceModeSelect.value : "delaunay";
        const zoneThicknessFactor = zoneThicknessRange ? Number(zoneThicknessRange.value || "0.12") : 0.12;
        const smoothSurface = !!(smoothSurfaceToggle && smoothSurfaceToggle.checked);
        const smoothLevel = smoothLevelRange ? Number(smoothLevelRange.value || "1") : 1;
        const showContours = !!(showContoursToggle && showContoursToggle.checked);
        const contourAxis = contourAxisSelect ? (contourAxisSelect.value || "z") : "z";
        const contourLevels = contourLevelsRange ? Number(contourLevelsRange.value || "6") : 6;
        const contourIntensity = contourIntensityRange ? Number(contourIntensityRange.value || "1.0") : 1.0;
        const contoursHighContrast = !!(contoursHighContrastToggle && contoursHighContrastToggle.checked);
        const autoDirection = resolveGeologyExtrudeDirection(points);
        const extrudeMode = extrudeModeSelect ? (extrudeModeSelect.value || "auto") : "auto";
        const extrudeDirection = extrudeMode === "up" ? "up" : extrudeMode === "down" ? "down" : autoDirection;
        const checkedDomains = new Set();
        if (domainChecklist) {
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                if (el.checked) checkedDomains.add(el.dataset.domain || "");
            });
        }
        const surfaceOpacity = opacityRange ? Number(opacityRange.value || "0.2") : 0.2;
        if (opacityLabel) opacityLabel.textContent = surfaceOpacity.toFixed(2);

        const domainFilteredPoints = points.filter((p) => {
            const domain = p.dominio || "default";
            if (selectedDomain !== "all" && domain !== selectedDomain) return false;
            if (checkedDomains.size && !checkedDomains.has(domain)) return false;
            return true;
        });
        const slicedPoints = applySliceFilter(domainFilteredPoints);
        const slicedComparePoints = compareEnabled ? applyCurrentDomainFilters(compareModelBPoints || []) : [];
        const groups = new Map();
        slicedPoints.forEach((p) => {
            const key = p.dominio || "default";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(p);
        });
        const compareGroups = groupByDomain(slicedComparePoints);

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
                const surfacePts = smoothSurface ? densifyDomainPoints(pts, smoothLevel) : pts;
                traces.push({
                    type: "mesh3d",
                    x: surfacePts.map((p) => p.x),
                    y: surfacePts.map((p) => p.y),
                    z: surfacePts.map((p) => p.z),
                    alphahull: surfaceMode === "hull" ? 0 : -1,
                    delaunayaxis: "z",
                    opacity: surfaceOpacity,
                    color,
                    name: `Superfície aprox.: ${domain}`,
                    hoverinfo: "skip",
                    flatshading: true,
                });

                if (showContours && surfacePts.length >= 4) {
                    traces.push(...buildContourTraces(surfacePts, domain, color, contourLevels, contourAxis, contourIntensity, contoursHighContrast));
                }
            }

            if (showEstimatedVolumes && pts.length >= 4) {
                const zone = buildDomainPerpendicularZoneMesh(pts, color, surfaceOpacity, zoneThicknessFactor, extrudeDirection);
                if (zone) {
                    traces.push({
                        type: "mesh3d",
                        x: zone.x, y: zone.y, z: zone.z,
                        i: zone.i, j: zone.j, k: zone.k,
                        color: zone.color,
                        opacity: zone.opacity,
                        name: `Volume estimado: ${domain}`,
                        hoverinfo: "skip",
                        flatshading: true,
                    });
                }
            }
        });

        let deltaStats = { addedCount: 0, removedCount: 0 };
        if (compareEnabled) {
            compareGroups.forEach((pts, domain) => {
                const x = pts.map((p) => p.x);
                const y = pts.map((p) => p.y);
                const z = pts.map((p) => p.z);
                const baseColor = colorForDomain(domain);
                if (compareShowPoints) {
                    traces.push({
                        type: "scatter3d",
                        mode: "markers",
                        x, y, z,
                        marker: { size: 4.5, color: baseColor, opacity: 0.45, symbol: "diamond" },
                        name: `B pontos: ${domain}`,
                        hovertemplate: "B · X=%{x:.2f}<br>Y=%{y:.2f}<br>Z=%{z:.2f}<extra></extra>",
                    });
                }
                if (compareShowSurface && pts.length >= 3) {
                    const surfacePts = smoothSurface ? densifyDomainPoints(pts, smoothLevel) : pts;
                    traces.push({
                        type: "mesh3d",
                        x: surfacePts.map((p) => p.x),
                        y: surfacePts.map((p) => p.y),
                        z: surfacePts.map((p) => p.z),
                        alphahull: surfaceMode === "hull" ? 0 : -1,
                        delaunayaxis: "z",
                        opacity: Math.max(0.08, surfaceOpacity * 0.35),
                        color: baseColor,
                        name: `B superfície: ${domain}`,
                        hoverinfo: "skip",
                        flatshading: true,
                    });
                }
            });
            if (compareShowDelta) {
                const delta = buildSpatialDeltaTraces(slicedPoints, slicedComparePoints, compareDeltaMarkerSize);
                deltaStats = { addedCount: delta.addedCount, removedCount: delta.removedCount };
                traces.push(...delta.traces);
                if (compareShowDeltaShell) {
                    traces.push(...buildSpatialDeltaShellTraces(delta.addedPoints, delta.removedPoints, compareDeltaShellOpacity));
                }
            }
        }

        if (sliceEnabledToggle && sliceEnabledToggle.checked && sliceAxisSelect && sliceValueRange) {
            const axis = (sliceAxisSelect.value || "x").toLowerCase();
            const pivot = Number(sliceValueRange.value || "0");
            const plane = buildSlicePlaneTrace(domainFilteredPoints, axis, pivot);
            if (plane) traces.push(plane);
        }

        if (!traces.length) {
            window.Plotly.purge(plotEl);
            plotEl.innerHTML = "";
            currentPlot = null;
            stopRotateAnimation();
            stopPulseAnimation();
            setStatus("Sem pontos para o domínio selecionado.", true);
            if (analyticsEl) analyticsEl.classList.add("hidden");
            if (contoursLegendEl) contoursLegendEl.classList.add("hidden");
            return;
        }

        const filteredPoints = slicedPoints.slice();

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
        bindPlotInteractionGuards();
        currentPlot = plotEl;
        const dirText = extrudeDirection === "up" ? "cima" : "baixo";
        const modeText = extrudeMode === "auto" ? "auto" : "manual";
        setStatus(`Renderização concluída: ${slicedPoints.length} pontos e ${groups.size} domínio(s). Extrusão para ${dirText} (${modeText}).`, false);
        if (sliceInfoEl) {
            if (sliceEnabledToggle && sliceEnabledToggle.checked && sliceAxisSelect && sliceValueRange) {
                const axis = (sliceAxisSelect.value || "x").toUpperCase();
                const pivot = Number(sliceValueRange.value || "0");
                sliceInfoEl.textContent = `Corte ativo: ${axis} <= ${pivot.toFixed(2)} | ${slicedPoints.length}/${domainFilteredPoints.length} pontos visíveis.`;
            } else {
                sliceInfoEl.textContent = "Corte inativo.";
            }
        }
        syncAnimations();
        persistUiConfig();
        scheduleServerUiConfigSync();
        atualizarResumoAnalitico(filteredPoints);
        updateContoursLegend(groups, contourAxis, contourLevels, showContours);
        if (compareEnabled) {
            renderCompareSummary(filteredPoints, slicedComparePoints, currentModelName, compareModelBName);
            if (compareStatusEl) {
                const deltaText = compareShowDelta ? ` | Delta +: ${deltaStats.addedCount} · Delta -: ${deltaStats.removedCount}` : "";
                const shellText = (compareShowDelta && compareShowDeltaShell) ? " · casca ON" : "";
                compareStatusEl.textContent = `Comparação ativa: A="${currentModelName}" vs B="${compareModelBName || "Modelo B"}"${deltaText}${shellText}`;
            }
        } else {
            if (compareStatusEl) compareStatusEl.textContent = "Comparação desativada.";
            if (compareSummaryEl) compareSummaryEl.classList.add("hidden");
        }
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
                    <span>bbox: ${row.volume.toFixed(2)} m³ · voxel: ${row.volumeVoxel.toFixed(2)} m³</span>
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
        const base = currentPoints.filter((p) => {
            const domain = p.dominio || "default";
            if (selectedDomain !== "all" && domain !== selectedDomain) return false;
            if (checkedDomains.size && !checkedDomains.has(domain)) return false;
            return true;
        });
        return applySliceFilter(base);
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
            const dvox = estimarVolumeVoxel(list);
            rows.push({
                domain,
                points: list.length,
                volume: dvol,
                volumeVoxel: dvox,
                dx: ddx,
                dy: ddy,
                dz: ddz,
            });
        });
        rows.sort((a, b) => b.volume - a.volume);
        return rows;
    }

    function estimarVolumeVoxel(points) {
        if (!Array.isArray(points) || points.length < 4) return 0;
        const xs = points.map((p) => Number(p.x)).filter((v) => Number.isFinite(v));
        const ys = points.map((p) => Number(p.y)).filter((v) => Number.isFinite(v));
        const zs = points.map((p) => Number(p.z)).filter((v) => Number.isFinite(v));
        if (!xs.length || !ys.length || !zs.length) return 0;

        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const minZ = Math.min(...zs), maxZ = Math.max(...zs);
        const spanX = Math.max(maxX - minX, 0.0001);
        const spanY = Math.max(maxY - minY, 0.0001);
        const spanZ = Math.max(maxZ - minZ, 0.0001);

        // Resolução moderada para manter performance no browser.
        const targetDiv = 16;
        const stepX = spanX / targetDiv;
        const stepY = spanY / targetDiv;
        const stepZ = spanZ / targetDiv;
        const cellVol = stepX * stepY * stepZ;
        if (!Number.isFinite(cellVol) || cellVol <= 0) return 0;

        const occupied = new Set();
        points.forEach((p) => {
            const ix = Math.min(targetDiv - 1, Math.max(0, Math.floor((p.x - minX) / stepX)));
            const iy = Math.min(targetDiv - 1, Math.max(0, Math.floor((p.y - minY) / stepY)));
            const iz = Math.min(targetDiv - 1, Math.max(0, Math.floor((p.z - minZ) / stepZ)));
            occupied.add(`${ix}|${iy}|${iz}`);
        });

        return occupied.size * cellVol;
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
        const resumoHeader = "dominio,pontos,extensao_x_m,extensao_y_m,extensao_z_m,volume_bbox_m3,volume_voxel_m3";
        const resumoRows = resumo.map((r) => (
            `${String(r.domain).replace(/,/g, " ")},${r.points},${r.dx.toFixed(4)},${r.dy.toFixed(4)},${r.dz.toFixed(4)},${r.volume.toFixed(4)},${r.volumeVoxel.toFixed(4)}`
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
                volume_bbox_m3_estimado: Number(r.volume.toFixed(4)),
                volume_voxel_m3_estimado: Number(r.volumeVoxel.toFixed(4)),
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
                    rerenderCurrentModel();
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
            bindPlotInteractionGuards();
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
    reopenButtons.forEach((button) => {
        const id = button.dataset.reopenImplicitId || "";
        const url = button.dataset.reopenImplicitUrl || "";
        const formato = (button.dataset.reopenImplicitFormato || "").toLowerCase();
        if (!id || !url || (formato !== "csv" && formato !== "json")) return;
        savedModelsIndex.set(id, {
            id,
            url,
            formato,
            name: button.dataset.reopenImplicitName || "modelo",
        });
    });
    rebuildCompareModelSelectors();

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

    function focusCurrentSelection() {
        if (!currentPlot) return;
        const points = obterPontosFiltradosAtuais();
        if (!points.length) {
            setStatus("Não há pontos visíveis para focar.", true);
            return;
        }
        const xs = points.map((p) => p.x);
        const ys = points.map((p) => p.y);
        const zs = points.map((p) => p.z);
        const xMin = Math.min(...xs); const xMax = Math.max(...xs);
        const yMin = Math.min(...ys); const yMax = Math.max(...ys);
        const zMin = Math.min(...zs); const zMax = Math.max(...zs);
        const span = Math.max(xMax - xMin, yMax - yMin, zMax - zMin, 1);
        const pad = span * 0.15;
        window.Plotly.relayout(currentPlot, {
            "scene.xaxis.range": [xMin - pad, xMax + pad],
            "scene.yaxis.range": [yMin - pad, yMax + pad],
            "scene.zaxis.range": [zMin - pad, zMax + pad],
            "scene.camera": { eye: { x: 1.35, y: 1.35, z: 0.9 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
        });
    }

    function clearFocusSelection() {
        if (!currentPlot) return;
        window.Plotly.relayout(currentPlot, {
            "scene.xaxis.autorange": true,
            "scene.yaxis.autorange": true,
            "scene.zaxis.autorange": true,
            "scene.camera": { eye: { x: 1.35, y: 1.35, z: 0.9 }, up: { x: 0, y: 0, z: 1 }, center: { x: 0, y: 0, z: 0 } },
        });
    }

    function rerenderCurrentModel() {
        if (!currentPoints.length) return;
        renderImplicit(currentPoints, currentModelName || "Implicit Model");
    }

    function setRangeValue(rangeEl, labelEl, value, fixedDigits) {
        if (!rangeEl) return;
        rangeEl.value = String(value);
        if (labelEl) {
            if (typeof fixedDigits === "number") labelEl.textContent = Number(value).toFixed(fixedDigits);
            else labelEl.textContent = String(value);
        }
    }

    function applyPresetOperational() {
        if (showPointsToggle) showPointsToggle.checked = true;
        if (showSurfaceToggle) showSurfaceToggle.checked = true;
        if (showEstimatedVolumesToggle) showEstimatedVolumesToggle.checked = true;
        if (surfaceModeSelect) surfaceModeSelect.value = "delaunay";
        setRangeValue(opacityRange, opacityLabel, 0.2, 2);
        setRangeValue(zoneThicknessRange, zoneThicknessLabel, 0.12, 2);
        if (extrudeModeSelect) extrudeModeSelect.value = "auto";
        if (smoothSurfaceToggle) smoothSurfaceToggle.checked = false;
        setRangeValue(smoothLevelRange, smoothLevelLabel, 1);
        if (showContoursToggle) showContoursToggle.checked = false;
        if (contoursHighContrastToggle) contoursHighContrastToggle.checked = false;
        if (sliceEnabledToggle) sliceEnabledToggle.checked = false;
        if (animRotateToggle) animRotateToggle.checked = false;
        if (animPulseToggle) animPulseToggle.checked = false;
    }

    function applyPresetGeology() {
        if (showPointsToggle) showPointsToggle.checked = true;
        if (showSurfaceToggle) showSurfaceToggle.checked = true;
        if (showEstimatedVolumesToggle) showEstimatedVolumesToggle.checked = true;
        if (surfaceModeSelect) surfaceModeSelect.value = "hull";
        setRangeValue(opacityRange, opacityLabel, 0.35, 2);
        setRangeValue(zoneThicknessRange, zoneThicknessLabel, 0.18, 2);
        if (extrudeModeSelect) extrudeModeSelect.value = "auto";
        if (smoothSurfaceToggle) smoothSurfaceToggle.checked = true;
        setRangeValue(smoothLevelRange, smoothLevelLabel, 2);
        if (showContoursToggle) showContoursToggle.checked = true;
        if (contourAxisSelect) contourAxisSelect.value = "z";
        setRangeValue(contourLevelsRange, contourLevelsLabel, 8);
        setRangeValue(contourIntensityRange, contourIntensityLabel, 1.2, 2);
        if (contoursHighContrastToggle) contoursHighContrastToggle.checked = true;
        if (sliceEnabledToggle) sliceEnabledToggle.checked = false;
        if (animRotateToggle) animRotateToggle.checked = false;
        if (animPulseToggle) animPulseToggle.checked = true;
    }

    function applyPresetSupervision() {
        if (showPointsToggle) showPointsToggle.checked = false;
        if (showSurfaceToggle) showSurfaceToggle.checked = true;
        if (showEstimatedVolumesToggle) showEstimatedVolumesToggle.checked = true;
        if (surfaceModeSelect) surfaceModeSelect.value = "delaunay";
        setRangeValue(opacityRange, opacityLabel, 0.28, 2);
        setRangeValue(zoneThicknessRange, zoneThicknessLabel, 0.22, 2);
        if (extrudeModeSelect) extrudeModeSelect.value = "down";
        if (smoothSurfaceToggle) smoothSurfaceToggle.checked = true;
        setRangeValue(smoothLevelRange, smoothLevelLabel, 2);
        if (showContoursToggle) showContoursToggle.checked = true;
        if (contourAxisSelect) contourAxisSelect.value = "z";
        setRangeValue(contourLevelsRange, contourLevelsLabel, 6);
        setRangeValue(contourIntensityRange, contourIntensityLabel, 1.0, 2);
        if (contoursHighContrastToggle) contoursHighContrastToggle.checked = false;
        if (sliceEnabledToggle) sliceEnabledToggle.checked = false;
        if (animRotateToggle) animRotateToggle.checked = true;
        if (animPulseToggle) animPulseToggle.checked = false;
    }

    function rebuildCompareModelSelectors() {
        if (!compareModelASelect || !compareModelBSelect) return;
        const prevA = compareModelASelect.value || "current";
        const prevB = compareModelBSelect.value || "";
        compareModelASelect.innerHTML = `<option value="current">Atual (preview aberto)</option>`;
        compareModelBSelect.innerHTML = `<option value="">Selecionar modelo guardado...</option>`;
        savedModelsIndex.forEach((meta, id) => {
            const label = `${meta.name || "modelo"} (${(meta.formato || "").toUpperCase()})`;
            const optA = document.createElement("option");
            optA.value = id;
            optA.textContent = label;
            compareModelASelect.appendChild(optA);
            const optB = document.createElement("option");
            optB.value = id;
            optB.textContent = label;
            compareModelBSelect.appendChild(optB);
        });
        compareModelASelect.value = savedModelsIndex.has(prevA) || prevA === "current" ? prevA : "current";
        compareModelBSelect.value = savedModelsIndex.has(prevB) ? prevB : "";
    }

    cameraButtons.forEach((button) => {
        button.addEventListener("click", () => {
            applyCamera(button.dataset.implicitCamera || "iso");
        });
    });
    if (focusSelectionBtn) {
        focusSelectionBtn.addEventListener("click", focusCurrentSelection);
    }
    if (clearFocusBtn) {
        clearFocusBtn.addEventListener("click", clearFocusSelection);
    }

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
    if (presetOperationalBtn) {
        presetOperationalBtn.addEventListener("click", () => {
            applyPresetOperational();
            if (currentPoints.length) rerenderCurrentModel();
            else persistUiConfig();
        });
    }
    if (presetGeologyBtn) {
        presetGeologyBtn.addEventListener("click", () => {
            applyPresetGeology();
            if (currentPoints.length) rerenderCurrentModel();
            else persistUiConfig();
        });
    }
    if (presetSupervisionBtn) {
        presetSupervisionBtn.addEventListener("click", () => {
            applyPresetSupervision();
            if (currentPoints.length) rerenderCurrentModel();
            else persistUiConfig();
        });
    }
    if (animRotateToggle) animRotateToggle.addEventListener("change", syncAnimations);
    if (animPulseToggle) animPulseToggle.addEventListener("change", syncAnimations);
    if (pulseIntensityRange) {
        pulseIntensityRange.addEventListener("input", () => {
            if (pulseIntensityLabel) pulseIntensityLabel.textContent = Number(pulseIntensityRange.value || 1).toFixed(2);
            persistUiConfig();
            scheduleServerUiConfigSync();
        });
    }

    fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) return;
        currentStateScope = "temp";
        currentConfigUrl = "";
        pendingServerUiConfig = null;
        const name = file.name || "";
        currentModelName = name || "Implicit Model";
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
            updateSliceRange(points);
            rebuildDomainFilter(points);
            applyUiConfig(loadUiConfig());
            updateSliceRange(points);
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
                if (modelId) savedModelPointsCache.set(modelId, points);
                currentModelName = name;
                updateSliceRange(points);
                rebuildDomainFilter(points);
                if (pendingServerUiConfig) {
                    applyUiConfig(pendingServerUiConfig);
                    pendingServerUiConfig = null;
                } else {
                    applyUiConfig(loadUiConfig());
                }
                updateSliceRange(points);
                renderImplicit(points, name);
            } catch (error) {
                setStatus(`Erro ao reabrir modelo implícito: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        });
    });

    if (compareModelASelect) {
        compareModelASelect.addEventListener("change", async () => {
            const value = compareModelASelect.value || "current";
            if (value === "current") {
                rerenderCurrentModel();
                persistUiConfig();
                return;
            }
            try {
                const points = await getSavedModelPoints(value);
                const meta = savedModelsIndex.get(value);
                const safePoints = sanitizeModelPoints(points || []);
                if (!safePoints.length) throw new Error("Modelo A sem pontos válidos.");
                currentPoints = safePoints;
                currentModelName = meta && meta.name ? meta.name : "Modelo A";
                rebuildDomainFilter(currentPoints);
                updateSliceRange(currentPoints);
                rerenderCurrentModel();
            } catch (error) {
                setStatus(`Erro ao carregar Modelo A: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        });
    }

    if (compareModelBSelect) {
        compareModelBSelect.addEventListener("change", async () => {
            const value = compareModelBSelect.value || "";
            if (!value) {
                compareModelBPoints = null;
                compareModelBName = "";
                rerenderCurrentModel();
                persistUiConfig();
                return;
            }
            try {
                const points = await getSavedModelPoints(value);
                const meta = savedModelsIndex.get(value);
                compareModelBPoints = sanitizeModelPoints(points || []);
                compareModelBName = meta && meta.name ? meta.name : "Modelo B";
                if (compareStatusEl) compareStatusEl.textContent = `Modelo B carregado: ${compareModelBName}`;
                rerenderCurrentModel();
            } catch (error) {
                compareModelBPoints = null;
                compareModelBName = "";
                setStatus(`Erro ao carregar Modelo B: ${error && error.message ? error.message : "erro desconhecido"}`, true);
            }
        });
    }

    [compareEnabledToggle, compareShowPointsToggle, compareShowSurfaceToggle, compareShowDeltaToggle, compareShowDeltaShellToggle].forEach((el) => {
        if (!el) return;
        el.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    });
    if (compareDeltaShellOpacityRange) {
        compareDeltaShellOpacityRange.addEventListener("input", () => {
            if (compareDeltaShellOpacityLabel) {
                compareDeltaShellOpacityLabel.textContent = Number(compareDeltaShellOpacityRange.value || "0.18").toFixed(2);
            }
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (compareDeltaMarkerSizeRange) {
        compareDeltaMarkerSizeRange.addEventListener("input", () => {
            if (compareDeltaMarkerSizeLabel) {
                compareDeltaMarkerSizeLabel.textContent = Number(compareDeltaMarkerSizeRange.value || "5.5").toFixed(1);
            }
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }

    if (domainFilter) {
        domainFilter.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
    if (selectAllDomainsBtn) {
        selectAllDomainsBtn.addEventListener("click", () => {
            if (!domainChecklist) return;
            domainChecklist.querySelectorAll("input[type='checkbox'][data-domain]").forEach((el) => {
                el.checked = true;
            });
            if (currentPoints.length) {
                rerenderCurrentModel();
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
                rerenderCurrentModel();
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
            rerenderCurrentModel();
        });
    }
    if (zoneThicknessRange) {
        zoneThicknessRange.addEventListener("input", () => {
            if (zoneThicknessLabel) zoneThicknessLabel.textContent = Number(zoneThicknessRange.value || 0).toFixed(2);
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (extrudeModeSelect) {
        extrudeModeSelect.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (smoothSurfaceToggle) {
        smoothSurfaceToggle.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (smoothLevelRange) {
        smoothLevelRange.addEventListener("input", () => {
            if (smoothLevelLabel) smoothLevelLabel.textContent = String(Math.round(Number(smoothLevelRange.value || 1)));
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (showContoursToggle) {
        showContoursToggle.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (contourAxisSelect) {
        contourAxisSelect.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (contourLevelsRange) {
        contourLevelsRange.addEventListener("input", () => {
            if (contourLevelsLabel) contourLevelsLabel.textContent = String(Math.round(Number(contourLevelsRange.value || 6)));
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (contourIntensityRange) {
        contourIntensityRange.addEventListener("input", () => {
            if (contourIntensityLabel) contourIntensityLabel.textContent = Number(contourIntensityRange.value || 1).toFixed(2);
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (contoursHighContrastToggle) {
        contoursHighContrastToggle.addEventListener("change", () => {
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (sliceEnabledToggle) {
        sliceEnabledToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
    if (sliceAxisSelect) {
        sliceAxisSelect.addEventListener("change", () => {
            if (!currentPoints.length) return;
            updateSliceRange(currentPoints);
            rerenderCurrentModel();
        });
    }
    if (sliceValueRange) {
        sliceValueRange.addEventListener("input", () => {
            if (sliceUiLock) return;
            if (sliceValueLabel) sliceValueLabel.textContent = Number(sliceValueRange.value || 0).toFixed(2);
            if (!currentPoints.length) {
                persistUiConfig();
                return;
            }
            rerenderCurrentModel();
        });
    }
    if (showPointsToggle) {
        showPointsToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
    if (showSurfaceToggle) {
        showSurfaceToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
    if (showEstimatedVolumesToggle) {
        showEstimatedVolumesToggle.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
    if (surfaceModeSelect) {
        surfaceModeSelect.addEventListener("change", () => {
            if (!currentPoints.length) return;
            rerenderCurrentModel();
        });
    }
})();
