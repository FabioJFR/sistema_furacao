(function () {
    const root = document.querySelector("[data-drone-sf-operacao-root]") || document.body;
    const estadoUrl = root.getAttribute("data-estado-url") || "";
    const historyLog = document.getElementById("sf-bridge-history-log");
    const modeBadge = document.getElementById("sf-bridge-mode-badge");
    const liveContainer = document.getElementById("sf-live-container");
    const mapElement = document.getElementById("droneSfControlMap");
    const operacaoAlvoLatInput = document.getElementById("id_operacao_sf-alvo_latitude");
    const operacaoAlvoLonInput = document.getElementById("id_operacao_sf-alvo_longitude");
    const operacaoAlvoAltInput = document.getElementById("id_operacao_sf-alvo_altitude_m");
    const comandoTipoInput = document.getElementById("id_comando_sf-tipo_comando");
    const comandoLatInput = document.getElementById("id_comando_sf-latitude_alvo");
    const comandoLonInput = document.getElementById("id_comando_sf-longitude_alvo");
    const comandoAltInput = document.getElementById("id_comando_sf-altitude_alvo_m");
    const comandoForm = comandoTipoInput ? comandoTipoInput.closest("form") : null;
    const mapGotoButton = document.getElementById("sf-map-goto-btn");
    const motorOriginFilter = document.getElementById("sf-motor-origin-filter");
    const motorTimeFilter = document.getElementById("sf-motor-time-filter");
    let map = null;
    let currentMarker = null;
    let targetMarker = null;
    let lastClickedTarget = null;
    let currentMotorOriginFilter = motorOriginFilter ? motorOriginFilter.value : "all";
    let currentMotorTimeFilter = motorTimeFilter ? motorTimeFilter.value : "all";

    function text(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value == null || value === "" ? "-" : value;
    }

    function formatDateTime(value) {
        if (!value) return "-";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleString("pt-PT");
    }

    function formatCommand(item) {
        if (!item || typeof item !== "object") return "-";
        const tipo = item.tipo || "-";
        const status = item.status || "";
        return status ? tipo + " · " + status : tipo;
    }

    function buildBridgeLogEntry(log) {
        const line = document.createElement("div");
        let classes = "rounded-lg px-3 py-2 ";
        if (log.tipo === "sucesso") {
            classes += "bg-emerald-900/40 text-emerald-200";
        } else if (log.tipo === "erro") {
            classes += "bg-rose-900/40 text-rose-200";
        } else {
            classes += "bg-slate-900 text-slate-200";
        }
        line.className = classes;

        const title = document.createElement("div");
        title.className = "font-medium";
        title.textContent = log.mensagem || "-";
        line.appendChild(title);

        const meta = document.createElement("div");
        meta.className = "text-xs opacity-80 mt-1";
        meta.textContent = log.timestamp || "-";
        line.appendChild(meta);
        return line;
    }

    function renderBridgeHistory(logs) {
        if (!historyLog) return;
        historyLog.innerHTML = "";
        if (!logs || !logs.length) {
            const empty = document.createElement("div");
            empty.className = "rounded-lg bg-slate-900 px-3 py-2 text-slate-200";
            empty.textContent = "Ainda não existem eventos recentes da bridge S_F.";
            historyLog.appendChild(empty);
            return;
        }
        logs.forEach(function (log) {
            historyLog.appendChild(buildBridgeLogEntry(log));
        });
    }

    function renderSummary(summary) {
        text("sf-ultimo-comando-recebido", formatCommand(summary?.ultimo_comando_recebido));
        text("sf-ultimo-comando-executado", formatCommand(summary?.ultimo_comando_executado));
        text("sf-hora-ultima-confirmacao", formatDateTime(summary?.hora_ultima_confirmacao));
        text("sf-ultimo-heartbeat-recebido", formatDateTime(summary?.ultimo_heartbeat_recebido));
        text("sf-estado-atual", summary?.ultimo_estado_bridge || "-");
        text("sf-ultimo-erro", summary?.ultimo_erro_bridge || "-");
    }

    function renderMotorSummary(summary) {
        text("sf-motor-ultima-execucao", formatDateTime(summary?.ultima_execucao_em));
        text("sf-motor-executadas", summary?.executadas != null ? String(summary.executadas) : "0");
        text("sf-motor-ignoradas", summary?.ignoradas != null ? String(summary.ignoradas) : "0");
        text("sf-motor-sem-operacao", summary?.sem_operacao != null ? String(summary.sem_operacao) : "0");
        text("sf-motor-ultimo-erro", summary?.ultimo_erro || "-");
        renderMotorList("sf-motor-ultimas-missoes", summary?.ultimas_missoes_disparadas || [], function (item) {
            const nome = item?.nome || "-";
            return {
                title: nome,
                origin: item?.origem || "",
                meta: formatDateTime(item?.timestamp),
            };
        }, "Ainda não há missões disparadas pelo motor.");
        renderMotorList("sf-motor-ultimos-comandos", summary?.ultimos_comandos_gerados || [], function (item) {
            const tipo = item?.tipo || "-";
            const status = item?.status ? " · " + item.status : "";
            return {
                title: tipo + status,
                origin: item?.origem || "",
                meta: formatDateTime(item?.timestamp),
            };
        }, "Ainda não há comandos gerados pelo motor.");
    }

    function renderMotorList(containerId, items, mapper, emptyText) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = "";
        const filteredItems = (items || []).filter(function (item) {
            if (currentMotorOriginFilter === "all") return true;
            return (item?.origem || "") === currentMotorOriginFilter;
        }).filter(function (item) {
            if (currentMotorTimeFilter === "all") return true;
            const timestamp = item?.timestamp;
            if (!timestamp) return false;
            const date = new Date(timestamp);
            if (Number.isNaN(date.getTime())) return false;
            const now = new Date();
            if (currentMotorTimeFilter === "today") {
                return (
                    date.getFullYear() === now.getFullYear() &&
                    date.getMonth() === now.getMonth() &&
                    date.getDate() === now.getDate()
                );
            }
            const diffMs = now.getTime() - date.getTime();
            if (currentMotorTimeFilter === "1h") {
                return diffMs >= 0 && diffMs <= 60 * 60 * 1000;
            }
            if (currentMotorTimeFilter === "24h") {
                return diffMs >= 0 && diffMs <= 24 * 60 * 60 * 1000;
            }
            return true;
        });
        if (!filteredItems.length) {
            const empty = document.createElement("div");
            empty.className = "text-sm text-slate-500";
            empty.textContent = emptyText;
            container.appendChild(empty);
            return;
        }
        filteredItems.forEach(function (item) {
            const data = mapper(item || {});
            const line = document.createElement("div");
            line.className = "rounded bg-white border border-slate-200 px-3 py-2";

            const title = document.createElement("div");
            title.className = "flex items-center justify-between gap-3";

            const titleText = document.createElement("div");
            titleText.className = "font-medium text-slate-900";
            titleText.textContent = data.title || "-";
            title.appendChild(titleText);

            if (data.origin) {
                const badge = document.createElement("span");
                badge.className = "text-[11px] uppercase tracking-wide rounded-full px-2 py-1 " + (
                    data.origin === "Manual"
                        ? "bg-cyan-100 text-cyan-700"
                        : "bg-emerald-100 text-emerald-700"
                );
                badge.textContent = data.origin;
                title.appendChild(badge);
            }
            line.appendChild(title);

            const meta = document.createElement("div");
            meta.className = "text-xs text-slate-500 mt-1";
            meta.textContent = data.meta || "-";
            line.appendChild(meta);

            container.appendChild(line);
        });
    }

    function renderLive(estado) {
        if (!liveContainer) return;
        const liveUrl = estado?.live_view_url || "";
        const snapshotUrl = estado?.frame_snapshot_url || "";
        if (liveUrl) {
            const current = document.getElementById("sf-live-frame");
            if (current && current.getAttribute("src") === liveUrl) return;
            liveContainer.innerHTML = '<iframe id="sf-live-frame" src="' + liveUrl + '" class="w-full h-[420px] border-0" loading="lazy"></iframe>';
            return;
        }
        if (snapshotUrl) {
            liveContainer.innerHTML = '<img id="sf-snapshot-image" src="' + snapshotUrl + '?t=' + Date.now() + '" alt="Snapshot Drone S_F" class="w-full h-[420px] object-cover">';
            return;
        }
        liveContainer.innerHTML = '<div id="sf-live-empty" class="text-sm text-slate-400 px-6 text-center">Ainda não existe feed ativo da bridge S_F. Assim que a bridge publicar `live_view_url` ou `frame_snapshot_url`, esta área passa a mostrar o estado visual do drone.</div>';
    }

    function renderModeBadge(sourceMode) {
        if (!modeBadge) return;
        const mode = sourceMode || "indefinido";
        modeBadge.textContent = "Modo: " + mode;
        modeBadge.className = "inline-flex items-center rounded-full px-3 py-1 font-semibold " + (
            mode === "webhook"
                ? "bg-emerald-100 text-emerald-800"
                : mode === "mock"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-700"
        );
    }

    function parseCoord(value) {
        if (value == null || value === "") return null;
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function updateMapStatus(currentLat, currentLon, targetLat, targetLon, targetAltitude) {
        text(
            "sf-mapa-posicao",
            currentLat != null && currentLon != null ? currentLat + ", " + currentLon : "-"
        );
        text(
            "sf-mapa-alvo",
            targetLat != null && targetLon != null ? targetLat + ", " + targetLon : "-"
        );
        text("sf-mapa-altitude-alvo", targetAltitude != null ? targetAltitude + " m" : "-");
    }

    function setFieldValue(field, value, decimals) {
        if (!field) return;
        if (value == null || value === "") {
            field.value = "";
            return;
        }
        const parsed = Number(value);
        field.value = Number.isFinite(parsed) && typeof decimals === "number" ? parsed.toFixed(decimals) : String(value);
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function applyTargetSelection(lat, lon) {
        const altitudeAtual = parseCoord(operacaoAlvoAltInput?.value) ?? parseCoord(comandoAltInput?.value) ?? 35;
        setFieldValue(operacaoAlvoLatInput, lat, 6);
        setFieldValue(operacaoAlvoLonInput, lon, 6);
        setFieldValue(operacaoAlvoAltInput, altitudeAtual, 2);
        setFieldValue(comandoTipoInput, "goto");
        setFieldValue(comandoLatInput, lat, 6);
        setFieldValue(comandoLonInput, lon, 6);
        setFieldValue(comandoAltInput, altitudeAtual, 2);
        lastClickedTarget = { lat, lon, altitude: altitudeAtual };
        text("sf-mapa-ponto-clicado", lat.toFixed(6) + ", " + lon.toFixed(6) + " · " + altitudeAtual.toFixed(2) + " m");
        if (mapGotoButton) {
            mapGotoButton.disabled = false;
        }
        updateMapStatus(
            parseCoord(document.getElementById("sf-latitude")?.textContent),
            parseCoord(document.getElementById("sf-longitude")?.textContent),
            lat,
            lon,
            altitudeAtual
        );
        if (targetMarker) {
            targetMarker.setLatLng([lat, lon]);
        } else if (map && typeof window.L !== "undefined") {
            targetMarker = window.L.marker([lat, lon], { opacity: 0.85 }).addTo(map).bindPopup("Alvo atual do Drone S_F");
        }
        if (targetMarker) {
            targetMarker.openPopup();
        }
    }

    function ensureMap() {
        if (!mapElement || typeof window.L === "undefined" || map) return;
        const initialLat = parseCoord(mapElement.dataset.currentLat) ?? parseCoord(mapElement.dataset.targetLat) ?? 40.2105;
        const initialLon = parseCoord(mapElement.dataset.currentLon) ?? parseCoord(mapElement.dataset.targetLon) ?? -8.4301;
        map = window.L.map(mapElement).setView([initialLat, initialLon], 15);
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap"
        }).addTo(map);
        map.on("click", function (event) {
            applyTargetSelection(event.latlng.lat, event.latlng.lng);
        });
    }

    function renderMap(estado) {
        if (!mapElement || typeof window.L === "undefined") return;
        ensureMap();
        if (!map) return;

        const currentLat = parseCoord(estado?.latitude_atual);
        const currentLon = parseCoord(estado?.longitude_atual);
        const targetLat = parseCoord(estado?.alvo_latitude);
        const targetLon = parseCoord(estado?.alvo_longitude);
        const targetAltitude = parseCoord(estado?.alvo_altitude_m);
        updateMapStatus(currentLat, currentLon, targetLat, targetLon, targetAltitude);

        if (currentLat != null && currentLon != null) {
            if (!currentMarker) {
                currentMarker = window.L.marker([currentLat, currentLon]).addTo(map).bindPopup("Posição atual do Drone S_F");
            } else {
                currentMarker.setLatLng([currentLat, currentLon]);
            }
        }

        if (targetLat != null && targetLon != null) {
            if (!targetMarker) {
                targetMarker = window.L.marker([targetLat, targetLon], { opacity: 0.85 }).addTo(map).bindPopup("Alvo atual do Drone S_F");
            } else {
                targetMarker.setLatLng([targetLat, targetLon]);
            }
        }

        const bounds = [];
        if (currentMarker) bounds.push(currentMarker.getLatLng());
        if (targetMarker) bounds.push(targetMarker.getLatLng());
        if (bounds.length === 1) {
            map.setView(bounds[0], 15);
        } else if (bounds.length > 1) {
            map.fitBounds(window.L.latLngBounds(bounds), { padding: [30, 30] });
        }
    }

    async function syncEstado() {
        if (!estadoUrl) return;
        try {
            const response = await fetch(estadoUrl, {
                method: "GET",
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });
            if (!response.ok) return;
            const data = await response.json();
            const estado = data?.estado || {};
            text("sf-bateria", estado.bateria_percent != null ? estado.bateria_percent + "%" : "-");
            text("sf-sinal", estado.sinal_percent != null ? estado.sinal_percent + "%" : "-");
            text("sf-latitude", estado.latitude_atual);
            text("sf-longitude", estado.longitude_atual);
            text("sf-altitude", estado.altitude_atual_m != null ? estado.altitude_atual_m + " m" : "-");
            text("sf-velocidade", estado.velocidade_atual_ms != null ? estado.velocidade_atual_ms + " m/s" : "-");
            text("sf-heading", estado.heading_graus != null ? estado.heading_graus + "°" : "-");
            text("sf-estado-label", estado.estado_label || "-");
            renderSummary(estado.bridge_status_summary || {});
            renderMotorSummary(estado.motor_missoes_summary || {});
            renderBridgeHistory(estado.bridge_logs || []);
            renderModeBadge(estado.bridge_source_mode || "");
            renderLive(estado);
            renderMap(estado);
        } catch (error) {
            // noop
        }
    }

    if (mapGotoButton) {
        mapGotoButton.addEventListener("click", function () {
            if (!lastClickedTarget || !comandoForm) return;
            setFieldValue(comandoTipoInput, "goto");
            setFieldValue(comandoLatInput, lastClickedTarget.lat, 6);
            setFieldValue(comandoLonInput, lastClickedTarget.lon, 6);
            setFieldValue(comandoAltInput, lastClickedTarget.altitude, 2);
            comandoForm.requestSubmit();
        });
    }

    if (motorOriginFilter) {
        motorOriginFilter.addEventListener("change", function () {
            currentMotorOriginFilter = motorOriginFilter.value || "all";
            syncEstado();
        });
    }

    if (motorTimeFilter) {
        motorTimeFilter.addEventListener("change", function () {
            currentMotorTimeFilter = motorTimeFilter.value || "all";
            syncEstado();
        });
    }

    syncEstado();
    window.setInterval(syncEstado, 8000);
})();
