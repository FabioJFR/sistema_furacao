(() => {
    const root = document.getElementById("ai-analise-form-root");
    if (!root) {
        return;
    }

    const fileInput = document.getElementById(root.dataset.imagemInputId || "");
    const shell = document.getElementById("ai-area-preview-shell");
    const stage = document.getElementById("ai-area-preview-stage");
    const image = document.getElementById("ai-area-preview-image");
    const reportRect = document.getElementById("ai-report-preview-rect");
    const priorityRect = document.getElementById("ai-priority-preview-rect");
    const draftRect = document.getElementById("ai-draft-zone-rect");
    const customLayer = document.getElementById("ai-custom-zones-layer");
    const xInput = document.getElementById(root.dataset.areaXId || "");
    const yInput = document.getElementById(root.dataset.areaYId || "");
    const wInput = document.getElementById(root.dataset.areaWId || "");
    const hInput = document.getElementById(root.dataset.areaHId || "");
    const fullButton = document.getElementById("ai-area-full-image");
    const reportJsonInput = document.getElementById(root.dataset.reportZoneJsonId || "");
    const customZonesJsonInput = document.getElementById(root.dataset.customZonesJsonId || "");
    const stepReportButton = document.getElementById("ai-step-report");
    const stepZonesButton = document.getElementById("ai-step-zones");
    const nextStepButton = document.getElementById("ai-step-next");
    const zoneNameInput = document.getElementById("ai-zone-name");
    const zoneXInput = document.getElementById("ai-zone-x");
    const zoneYInput = document.getElementById("ai-zone-y");
    const zoneWInput = document.getElementById("ai-zone-w");
    const zoneHInput = document.getElementById("ai-zone-h");
    const saveZoneButton = document.getElementById("ai-save-zone");
    const clearDraftButton = document.getElementById("ai-clear-draft-zone");
    const zonesList = document.getElementById("ai-custom-zones-list");
    const reportSummary = document.getElementById("ai-report-zone-summary");
    const presetDataNode = document.getElementById("ai-zone-presets-data");
    const presetSelect = document.getElementById("ai-preset-select");
    const applyPresetButton = document.getElementById("ai-apply-preset");
    const savePresetButton = document.getElementById("ai-save-preset");
    const presetNameInput = document.getElementById("ai-preset-name");
    const presetFeedback = document.getElementById("ai-preset-feedback");
    const tipoDocumentoInput = document.getElementById(root.dataset.tipoDocumentoId || "");
    const savePresetUrl = root.dataset.savePresetUrl || "";

    if (
        !fileInput ||
        !shell ||
        !stage ||
        !image ||
        !reportRect ||
        !priorityRect ||
        !draftRect ||
        !customLayer ||
        !xInput ||
        !yInput ||
        !wInput ||
        !hInput ||
        !zoneNameInput ||
        !zoneXInput ||
        !zoneYInput ||
        !zoneWInput ||
        !zoneHInput ||
        !zonesList ||
        !reportSummary ||
        !presetSelect ||
        !presetNameInput ||
        !presetFeedback ||
        !tipoDocumentoInput ||
        !savePresetUrl
    ) {
        return;
    }

    let dragging = false;
    let startX = 0;
    let startY = 0;
    let activeStep = "report";
    let reportZone = null;
    let customZones = [];
    let editingZoneIndex = null;
    let resizeState = null;
    let zonePresets = [];

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function parseJsonInput(input, fallback) {
        if (!input || !input.value) {
            return fallback;
        }
        try {
            return JSON.parse(input.value);
        } catch (error) {
            return fallback;
        }
    }

    function writeJsonInput(input, value) {
        if (input) {
            input.value = value === "" || value === null ? "" : JSON.stringify(value);
        }
    }

    function zoneToStyle(zone, width, height) {
        return {
            left: `${(zone.x_percent / 100) * width}px`,
            top: `${(zone.y_percent / 100) * height}px`,
            width: `${(zone.w_percent / 100) * width}px`,
            height: `${(zone.h_percent / 100) * height}px`,
        };
    }

    function renderPriorityRectFromInputs() {
        if (!image.src) {
            priorityRect.classList.add("hidden");
            return;
        }
        const width = image.clientWidth || stage.clientWidth;
        const height = image.clientHeight || stage.clientHeight;
        const x = clamp(parseFloat(xInput.value || 0), 0, 100);
        const y = clamp(parseFloat(yInput.value || 0), 0, 100);
        const w = clamp(parseFloat(wInput.value || 0), 0, 100);
        const h = clamp(parseFloat(hInput.value || 0), 0, 100);

        Object.assign(priorityRect.style, zoneToStyle({ x_percent: x, y_percent: y, w_percent: w, h_percent: h }, width, height));
        priorityRect.classList.remove("hidden");
    }

    function renderReportRect() {
        if (!image.src || !reportZone) {
            reportRect.classList.add("hidden");
            reportSummary.textContent = "Ainda não definiste a moldura total do relatório.";
            writeJsonInput(reportJsonInput, "");
            return;
        }
        const width = image.clientWidth || stage.clientWidth;
        const height = image.clientHeight || stage.clientHeight;
        Object.assign(reportRect.style, zoneToStyle(reportZone, width, height));
        reportRect.classList.remove("hidden");
        reportSummary.textContent = `Relatório: X ${reportZone.x_percent.toFixed(1)}%, Y ${reportZone.y_percent.toFixed(1)}%, L ${reportZone.w_percent.toFixed(1)}%, A ${reportZone.h_percent.toFixed(1)}%.`;
        writeJsonInput(reportJsonInput, reportZone);
    }

    function renderDraftZone() {
        const width = image.clientWidth || stage.clientWidth;
        const height = image.clientHeight || stage.clientHeight;
        const x = parseFloat(zoneXInput.value || 0);
        const y = parseFloat(zoneYInput.value || 0);
        const w = parseFloat(zoneWInput.value || 0);
        const h = parseFloat(zoneHInput.value || 0);
        if (!w || !h) {
            draftRect.classList.add("hidden");
            return;
        }
        Object.assign(draftRect.style, zoneToStyle({ x_percent: x, y_percent: y, w_percent: w, h_percent: h }, width, height));
        draftRect.classList.remove("hidden");
    }

    function renderCustomZones() {
        customLayer.innerHTML = "";
        if (!customZones.length) {
            zonesList.innerHTML = '<div class="text-slate-400">Ainda não existem zonas nomeadas guardadas.</div>';
            writeJsonInput(customZonesJsonInput, []);
            return;
        }

        const width = image.clientWidth || stage.clientWidth;
        const height = image.clientHeight || stage.clientHeight;
        zonesList.innerHTML = "";

        customZones.forEach((zone, index) => {
            const item = document.createElement("div");
            item.className = "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 flex flex-wrap items-center justify-between gap-3";
            item.innerHTML = `
                <div>
                    <div class="font-medium text-slate-900">${zone.name || `Zona ${index + 1}`}</div>
                    <div class="text-slate-500">X ${zone.x_percent.toFixed(1)}%, Y ${zone.y_percent.toFixed(1)}%, L ${zone.w_percent.toFixed(1)}%, A ${zone.h_percent.toFixed(1)}%</div>
                </div>
                <div class="flex flex-wrap gap-2">
                    <button type="button" data-zone-index="${index}" class="btn btn-secondary ai-edit-zone">Editar</button>
                    <button type="button" data-zone-index="${index}" class="btn btn-secondary ai-remove-zone">Remover</button>
                </div>
            `;
            zonesList.appendChild(item);

            const zoneEl = document.createElement("div");
            zoneEl.className = "absolute border-[3px] border-amber-500 bg-amber-300/15";
            Object.assign(zoneEl.style, zoneToStyle(zone, width, height));

            const label = document.createElement("div");
            label.className = "absolute -top-6 left-0 rounded bg-amber-500 px-2 py-0.5 text-xs font-medium text-white whitespace-nowrap";
            label.textContent = zone.name || `Zona ${index + 1}`;
            zoneEl.appendChild(label);

            customLayer.appendChild(zoneEl);
        });

        writeJsonInput(customZonesJsonInput, customZones);
    }

    function setStep(step) {
        activeStep = step;
        stepReportButton?.classList.toggle("btn-primary", step === "report");
        stepReportButton?.classList.toggle("btn-secondary", step !== "report");
        stepZonesButton?.classList.toggle("btn-primary", step === "zones");
        stepZonesButton?.classList.toggle("btn-secondary", step !== "zones");
    }

    function setFullImage() {
        xInput.value = "0";
        yInput.value = "0";
        wInput.value = "100";
        hInput.value = "100";
        renderPriorityRectFromInputs();
    }

    function startResize(event, target, handle) {
        event.preventDefault();
        event.stopPropagation();
        const bounds = image.getBoundingClientRect();
        const zone = target === "report"
            ? (reportZone || { x_percent: 0, y_percent: 0, w_percent: 0, h_percent: 0 })
            : {
                x_percent: parseFloat(zoneXInput.value || 0),
                y_percent: parseFloat(zoneYInput.value || 0),
                w_percent: parseFloat(zoneWInput.value || 0),
                h_percent: parseFloat(zoneHInput.value || 0),
            };
        resizeState = { target, handle, bounds, zone };
    }

    function updateResize(clientX, clientY) {
        if (!resizeState) {
            return;
        }
        const { target, handle, bounds, zone } = resizeState;
        const currentX = clamp(((clientX - bounds.left) / bounds.width) * 100, 0, 100);
        const currentY = clamp(((clientY - bounds.top) / bounds.height) * 100, 0, 100);
        const x1 = zone.x_percent;
        const y1 = zone.y_percent;
        const x2 = zone.x_percent + zone.w_percent;
        const y2 = zone.y_percent + zone.h_percent;

        const newZone = handle === "nw"
            ? {
                x_percent: Math.min(currentX, x2 - 0.5),
                y_percent: Math.min(currentY, y2 - 0.5),
                w_percent: Math.max(0.5, x2 - currentX),
                h_percent: Math.max(0.5, y2 - currentY),
            }
            : {
                x_percent: x1,
                y_percent: y1,
                w_percent: Math.max(0.5, currentX - x1),
                h_percent: Math.max(0.5, currentY - y1),
            };

        if (target === "report") {
            reportZone = {
                x_percent: parseFloat(newZone.x_percent.toFixed(1)),
                y_percent: parseFloat(newZone.y_percent.toFixed(1)),
                w_percent: parseFloat(newZone.w_percent.toFixed(1)),
                h_percent: parseFloat(newZone.h_percent.toFixed(1)),
            };
            renderReportRect();
            return;
        }

        zoneXInput.value = newZone.x_percent.toFixed(1);
        zoneYInput.value = newZone.y_percent.toFixed(1);
        zoneWInput.value = newZone.w_percent.toFixed(1);
        zoneHInput.value = newZone.h_percent.toFixed(1);
        renderDraftZone();
    }

    function updateFromPointer(clientX, clientY) {
        const bounds = image.getBoundingClientRect();
        const currentX = clamp(clientX - bounds.left, 0, bounds.width);
        const currentY = clamp(clientY - bounds.top, 0, bounds.height);
        const left = Math.min(startX, currentX);
        const top = Math.min(startY, currentY);
        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);

        const zone = {
            x_percent: parseFloat(((left / bounds.width) * 100).toFixed(1)),
            y_percent: parseFloat(((top / bounds.height) * 100).toFixed(1)),
            w_percent: parseFloat(((width / bounds.width) * 100).toFixed(1)),
            h_percent: parseFloat(((height / bounds.height) * 100).toFixed(1)),
        };

        if (activeStep === "report") {
            reportZone = zone;
            renderReportRect();
            if (zone.w_percent > 0 && zone.h_percent > 0) {
                xInput.value = zone.x_percent.toFixed(1);
                yInput.value = zone.y_percent.toFixed(1);
                wInput.value = zone.w_percent.toFixed(1);
                hInput.value = zone.h_percent.toFixed(1);
                renderPriorityRectFromInputs();
            }
            return;
        }

        zoneXInput.value = zone.x_percent.toFixed(1);
        zoneYInput.value = zone.y_percent.toFixed(1);
        zoneWInput.value = zone.w_percent.toFixed(1);
        zoneHInput.value = zone.h_percent.toFixed(1);
        renderDraftZone();
    }

    function clearDraftZone() {
        zoneNameInput.value = "";
        zoneXInput.value = "";
        zoneYInput.value = "";
        zoneWInput.value = "";
        zoneHInput.value = "";
        editingZoneIndex = null;
        draftRect.classList.add("hidden");
    }

    function saveDraftZone() {
        const name = (zoneNameInput.value || "").trim();
        const x = parseFloat(zoneXInput.value || 0);
        const y = parseFloat(zoneYInput.value || 0);
        const w = parseFloat(zoneWInput.value || 0);
        const h = parseFloat(zoneHInput.value || 0);
        if (!name || !w || !h) {
            return;
        }
        const payload = { name, x_percent: x, y_percent: y, w_percent: w, h_percent: h };
        if (editingZoneIndex !== null) {
            customZones.splice(editingZoneIndex, 1, payload);
        } else {
            customZones.push(payload);
        }
        renderCustomZones();
        clearDraftZone();
    }

    function populatePresetSelect() {
        presetSelect.innerHTML = '<option value="">Sem preset</option>';
        zonePresets.forEach((preset) => {
            const option = document.createElement("option");
            option.value = preset.id;
            option.textContent = `${preset.nome} · ${preset.tipo_documento}`;
            presetSelect.appendChild(option);
        });
    }

    function applyPreset() {
        const selected = zonePresets.find((item) => item.id === presetSelect.value);
        if (!selected) {
            presetFeedback.textContent = "Seleciona um preset para aplicar.";
            return;
        }
        reportZone = selected.zona_relatorio || null;
        customZones = Array.isArray(selected.zonas_texto) ? selected.zonas_texto.slice() : [];
        renderReportRect();
        renderCustomZones();
        presetFeedback.textContent = `Preset aplicado: ${selected.nome}`;
    }

    async function savePreset() {
        const nome = (presetNameInput.value || "").trim();
        if (!nome) {
            presetFeedback.textContent = "Indica um nome para guardar o preset.";
            return;
        }

        const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
        const payload = new URLSearchParams();
        payload.set("nome", nome);
        payload.set("tipo_documento", tipoDocumentoInput.value || "relatorio_trabalhador");
        payload.set("report_zone_json", reportZone ? JSON.stringify(reportZone) : "");
        payload.set("custom_text_zones_json", JSON.stringify(customZones || []));

        const response = await fetch(savePresetUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrfToken || "",
            },
            body: payload.toString(),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            presetFeedback.textContent = data.error || "Não foi possível guardar o preset.";
            return;
        }

        const existingIndex = zonePresets.findIndex((item) => item.id === data.preset.id);
        if (existingIndex >= 0) {
            zonePresets.splice(existingIndex, 1, data.preset);
        } else {
            zonePresets.push(data.preset);
        }
        zonePresets.sort((a, b) => `${a.tipo_documento}-${a.nome}`.localeCompare(`${b.tipo_documento}-${b.nome}`, "pt"));
        populatePresetSelect();
        presetSelect.value = data.preset.id;
        presetFeedback.textContent = `Preset guardado: ${data.preset.nome}`;
    }

    fileInput.addEventListener("change", (event) => {
        const [file] = event.target.files || [];
        if (!file) {
            shell.classList.add("hidden");
            return;
        }
        const reader = new FileReader();
        reader.onload = (loadEvent) => {
            image.src = loadEvent.target.result;
            shell.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    });

    image.addEventListener("load", () => {
        renderPriorityRectFromInputs();
        renderReportRect();
        renderDraftZone();
        renderCustomZones();
    });

    image.addEventListener("pointerdown", (event) => {
        const bounds = image.getBoundingClientRect();
        dragging = true;
        startX = clamp(event.clientX - bounds.left, 0, bounds.width);
        startY = clamp(event.clientY - bounds.top, 0, bounds.height);
        updateFromPointer(event.clientX, event.clientY);
    });

    window.addEventListener("pointermove", (event) => {
        if (resizeState) {
            updateResize(event.clientX, event.clientY);
            return;
        }
        if (!dragging) {
            return;
        }
        updateFromPointer(event.clientX, event.clientY);
    });

    window.addEventListener("pointerup", () => {
        dragging = false;
        resizeState = null;
    });

    [xInput, yInput, wInput, hInput].forEach((input) => input.addEventListener("input", renderPriorityRectFromInputs));
    [zoneXInput, zoneYInput, zoneWInput, zoneHInput].forEach((input) => input.addEventListener("input", renderDraftZone));

    fullButton?.addEventListener("click", setFullImage);
    stepReportButton?.addEventListener("click", () => setStep("report"));
    stepZonesButton?.addEventListener("click", () => setStep("zones"));
    nextStepButton?.addEventListener("click", () => setStep("zones"));
    saveZoneButton?.addEventListener("click", saveDraftZone);
    clearDraftButton?.addEventListener("click", clearDraftZone);
    applyPresetButton?.addEventListener("click", applyPreset);
    savePresetButton?.addEventListener("click", savePreset);

    zonesList.addEventListener("click", (event) => {
        const editButton = event.target.closest(".ai-edit-zone");
        if (editButton) {
            const index = parseInt(editButton.dataset.zoneIndex || "-1", 10);
            const zone = customZones[index];
            if (zone) {
                editingZoneIndex = index;
                zoneNameInput.value = zone.name || "";
                zoneXInput.value = zone.x_percent.toFixed(1);
                zoneYInput.value = zone.y_percent.toFixed(1);
                zoneWInput.value = zone.w_percent.toFixed(1);
                zoneHInput.value = zone.h_percent.toFixed(1);
                setStep("zones");
                renderDraftZone();
            }
            return;
        }
        const button = event.target.closest(".ai-remove-zone");
        if (!button) {
            return;
        }
        const index = parseInt(button.dataset.zoneIndex || "-1", 10);
        if (index >= 0) {
            customZones.splice(index, 1);
            renderCustomZones();
        }
    });

    reportZone = parseJsonInput(reportJsonInput, null);
    customZones = parseJsonInput(customZonesJsonInput, []);
    zonePresets = presetDataNode ? parseJsonInput({ value: presetDataNode.textContent }, []) : [];

    stage.querySelectorAll("[data-handle]").forEach((handle) => {
        handle.addEventListener("pointerdown", (event) => {
            startResize(event, handle.dataset.rectTarget, handle.dataset.handle);
        });
    });

    populatePresetSelect();
    setStep("report");
    renderPriorityRectFromInputs();
    renderReportRect();
    renderCustomZones();
})();
