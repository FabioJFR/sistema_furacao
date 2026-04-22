(function () {
    const form = document.querySelector("[data-geologia-drone-import-form]");
    if (form) {
        const summary = form.querySelector("[data-drone-import-summary]");
        const furoField = form.querySelector("#id_furo");
        const fileField = form.querySelector("#id_ficheiro_metadados");
        const titleField = form.querySelector("#id_titulo");

        function updateSummary() {
            const partes = [];

            if (furoField && furoField.selectedOptions.length > 0) {
                const selected = furoField.selectedOptions[0];
                if (selected.value) {
                    partes.push("Furo: " + selected.textContent.trim());
                }
            }

            if (fileField && fileField.files.length > 0) {
                partes.push("Ficheiro: " + fileField.files[0].name);
            }

            if (titleField && titleField.value.trim()) {
                partes.push("Titulo: " + titleField.value.trim());
            }

            summary.textContent = partes.length ? partes.join(" | ") : "Aguardando selecao de furo e ficheiro.";
        }

        [furoField, fileField, titleField].forEach(function (field) {
            if (!field) {
                return;
            }
            field.addEventListener("change", updateSummary);
            field.addEventListener("input", updateSummary);
        });

        updateSummary();
    }

    const mapElement = document.getElementById("droneControlMap");
    const commandForm = document.getElementById("droneCommandForm");
    const debugLog = document.getElementById("drone-debug-log");
    const bridgeHistoryLog = document.getElementById("bridge-history-log");
    const linkChip = document.getElementById("drone-link-chip");
    const ultimoComandoRecebido = document.getElementById("bridge-ultimo-comando-recebido");
    const ultimoComandoExecutado = document.getElementById("bridge-ultimo-comando-executado");
    const horaUltimaConfirmacao = document.getElementById("bridge-hora-ultima-confirmacao");
    const ultimoHeartbeatRecebido = document.getElementById("bridge-ultimo-heartbeat-recebido");
    const estadoAtualBridge = document.getElementById("bridge-estado-atual");
    const ultimoErroBridge = document.getElementById("bridge-ultimo-erro");
    const bridgeSourceMode = document.getElementById("bridge-source-mode");
    const bridgeSourceBadge = document.getElementById("bridge-source-badge");
    const bridgeSourceLabel = document.getElementById("bridge-source-label");
    const btnTestarLigacao = document.getElementById("btn-drone-testar-ligacao");
    const btnProcurar = document.getElementById("btn-drone-procurar");
    const btnSincronizar = document.getElementById("btn-drone-sincronizar");
    const apiEstadoUrl = "/app/geologia/drone/api/estado/";
    const apiTestarUrl = "/app/geologia/drone/api/testar-ligacao/";
    const apiProcurarUrl = "/app/geologia/drone/api/procurar/";

    function appendLog(tipo, mensagem) {
        if (!debugLog) return;
        const line = document.createElement("div");
        let classes = "rounded-lg px-3 py-2 ";
        if (tipo === "sucesso") {
            classes += "bg-emerald-900/40 text-emerald-200";
        } else if (tipo === "erro") {
            classes += "bg-rose-900/40 text-rose-200";
        } else {
            classes += "bg-slate-900 text-slate-200";
        }
        line.className = classes;
        line.textContent = mensagem;
        debugLog.prepend(line);
    }

    function updateChip(estadoLabel, estadoKey) {
        if (!linkChip) return;
        linkChip.textContent = estadoLabel || "Desconhecido";
        linkChip.className = "text-xs uppercase tracking-wide rounded-full px-3 py-1 ";
        if (estadoKey === "pronto") {
            linkChip.className += "bg-emerald-100 text-emerald-700";
        } else if (estadoKey === "procurando") {
            linkChip.className += "bg-amber-100 text-amber-700";
        } else if (estadoKey === "erro") {
            linkChip.className += "bg-rose-100 text-rose-700";
        } else if (estadoKey === "em_voo" || estadoKey === "em_missao") {
            linkChip.className += "bg-sky-100 text-sky-700";
        } else {
            linkChip.className += "bg-slate-100 text-slate-700";
        }
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

        let tagLabel = "INFO";
        const message = (log.mensagem || "").toLowerCase();
        if (message.includes("/live")) {
            tagLabel = "LIVE";
        } else if (message.includes("/frame")) {
            tagLabel = "FRAME";
        } else if (message.includes("heartbeat")) {
            tagLabel = "HEARTBEAT";
        } else if (message.includes("comando")) {
            tagLabel = "COMANDO";
        } else if (log.tipo === "erro") {
            tagLabel = "ERRO";
        }

        const header = document.createElement("div");
        header.className = "flex items-center gap-2 mb-1";
        const badge = document.createElement("span");
        badge.className = "inline-flex items-center rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold tracking-wide";
        badge.textContent = tagLabel;
        header.appendChild(badge);
        line.appendChild(header);

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
        if (!bridgeHistoryLog) return;
        bridgeHistoryLog.innerHTML = "";
        if (!logs || !logs.length) {
            const empty = document.createElement("div");
            empty.className = "rounded-lg bg-slate-900 px-3 py-2 text-slate-200";
            empty.textContent = "Ainda não existem eventos recentes da bridge.";
            bridgeHistoryLog.appendChild(empty);
            return;
        }
        logs.forEach(function (log) {
            bridgeHistoryLog.appendChild(buildBridgeLogEntry(log));
        });
    }

    function formatBridgeSummaryItem(item) {
        if (!item || typeof item !== "object") {
            return "-";
        }
        const tipo = item.tipo || "-";
        const status = item.status || "";
        return status ? tipo + " · " + status : tipo;
    }

    function formatDateTime(value) {
        if (!value) {
            return "-";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString("pt-PT");
    }

    function renderBridgeStatusSummary(summary) {
        if (!summary) {
            return;
        }
        if (ultimoComandoRecebido) {
            ultimoComandoRecebido.textContent = formatBridgeSummaryItem(summary.ultimo_comando_recebido);
        }
        if (ultimoComandoExecutado) {
            ultimoComandoExecutado.textContent = formatBridgeSummaryItem(summary.ultimo_comando_executado);
            ultimoComandoExecutado.className = "font-semibold mt-1 " + (
                summary.ultimo_comando_executado && String(summary.ultimo_comando_executado.status || "").toLowerCase() === "executado"
                    ? "text-emerald-700"
                    : summary.ultimo_comando_executado
                        ? "text-amber-700"
                        : "text-slate-900"
            );
        }
        if (horaUltimaConfirmacao) {
            horaUltimaConfirmacao.textContent = formatDateTime(summary.hora_ultima_confirmacao);
        }
        if (ultimoHeartbeatRecebido) {
            ultimoHeartbeatRecebido.textContent = formatDateTime(summary.ultimo_heartbeat_recebido);
            ultimoHeartbeatRecebido.className = "font-semibold mt-1 " + (
                summary.ultimo_heartbeat_recebido ? "text-emerald-700" : "text-slate-900"
            );
        }
        if (estadoAtualBridge) {
            estadoAtualBridge.textContent = summary.ultimo_estado_bridge || "-";
            estadoAtualBridge.className = "font-semibold mt-1 " + (
                summary.ultimo_estado_bridge &&
                !["online", "ok", "ready"].includes(String(summary.ultimo_estado_bridge).toLowerCase())
                    ? "text-amber-700"
                    : "text-emerald-700"
            );
        }
        if (ultimoErroBridge) {
            ultimoErroBridge.textContent = summary.ultimo_erro_bridge || "-";
            ultimoErroBridge.className = "font-semibold mt-1 " + (
                summary.ultimo_erro_bridge ? "text-rose-700" : "text-emerald-700"
            );
        }
    }

    function renderBridgeSourceInfo(estado) {
        const sourceMode = estado?.bridge_source_mode || "indefinido";
        if (bridgeSourceMode) {
            bridgeSourceMode.textContent = sourceMode;
        }
        if (bridgeSourceBadge) {
            bridgeSourceBadge.textContent = "Modo: " + sourceMode;
            bridgeSourceBadge.className = "inline-flex items-center rounded-full px-3 py-1 font-semibold " + (
                sourceMode === "webhook"
                    ? "bg-emerald-100 text-emerald-800"
                    : sourceMode === "mock"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-slate-100 text-slate-700"
            );
        }
        if (bridgeSourceLabel) {
            const sourceLabel = estado?.bridge_ultimo_estado || "local";
            bridgeSourceLabel.textContent = "Fonte de dados: " + sourceLabel;
        }
    }

    async function requestDroneStatus(url, method) {
        const options = { method: method || "GET", headers: { "X-Requested-With": "XMLHttpRequest" } };
        if (method === "POST") {
            options.headers["X-CSRFToken"] = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
        }
        const response = await fetch(url, options);
        const data = await response.json();
        if (data.eventos) {
            data.eventos.forEach((evento) => appendLog(evento.tipo, evento.mensagem));
        }
        if (data.estado) {
            updateChip(data.estado.estado_label, data.estado.estado_conexao);
            renderBridgeHistory(data.estado.bridge_logs || []);
            renderBridgeStatusSummary(data.estado.bridge_status_summary);
            renderBridgeSourceInfo(data.estado);
        }
        return data;
    }

    if (btnTestarLigacao) {
        btnTestarLigacao.addEventListener("click", function () {
            requestDroneStatus(apiTestarUrl, "GET").catch(function () {
                appendLog("erro", "Não foi possível testar a ligação ao drone.");
            });
        });
    }

    if (btnProcurar) {
        btnProcurar.addEventListener("click", function () {
            requestDroneStatus(apiProcurarUrl, "POST").catch(function () {
                appendLog("erro", "Não foi possível iniciar a procura do drone.");
            });
        });
    }

    if (btnSincronizar) {
        btnSincronizar.addEventListener("click", function () {
            requestDroneStatus(apiEstadoUrl, "GET").then(function (data) {
                if (data.estado) {
                    appendLog("info", "Estado do drone sincronizado com sucesso.");
                }
            }).catch(function () {
                appendLog("erro", "Não foi possível sincronizar o estado do drone.");
            });
        });
    }

    if (!mapElement || !commandForm || typeof L === "undefined") {
        const quickCommandButton = document.querySelector("[data-drone-quick-command='rth']");
        if (quickCommandButton && commandForm) {
            quickCommandButton.addEventListener("click", function () {
                const tipoField = commandForm.querySelector("#id_comando-tipo_comando");
                if (tipoField) {
                    tipoField.value = "rth";
                }
                commandForm.submit();
            });
        }
        return;
    }

    const currentLat = parseFloat(mapElement.dataset.currentLat || "");
    const currentLon = parseFloat(mapElement.dataset.currentLon || "");
    const targetLat = parseFloat(mapElement.dataset.targetLat || "");
    const targetLon = parseFloat(mapElement.dataset.targetLon || "");
    const centerLat = Number.isFinite(currentLat) ? currentLat : (Number.isFinite(targetLat) ? targetLat : 39.5);
    const centerLon = Number.isFinite(currentLon) ? currentLon : (Number.isFinite(targetLon) ? targetLon : -8.0);

    const map = L.map(mapElement).setView([centerLat, centerLon], 15);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 20,
        attribution: "&copy; OpenStreetMap",
    }).addTo(map);

    let currentMarker = null;
    let targetMarker = null;

    if (Number.isFinite(currentLat) && Number.isFinite(currentLon)) {
        currentMarker = L.marker([currentLat, currentLon]).addTo(map).bindPopup("Posição atual do drone");
    }

    function setTargetMarker(lat, lon) {
        if (targetMarker) {
            targetMarker.setLatLng([lat, lon]);
        } else {
            targetMarker = L.marker([lat, lon], { draggable: true }).addTo(map).bindPopup("Alvo do drone");
            targetMarker.on("dragend", function (event) {
                const pos = event.target.getLatLng();
                writeTargetFields(pos.lat, pos.lng);
            });
        }
        writeTargetFields(lat, lon);
    }

    function writeTargetFields(lat, lon) {
        const latField = commandForm.querySelector("#id_comando-latitude_alvo");
        const lonField = commandForm.querySelector("#id_comando-longitude_alvo");
        const tipoField = commandForm.querySelector("#id_comando-tipo_comando");
        if (latField) latField.value = Number(lat).toFixed(6);
        if (lonField) lonField.value = Number(lon).toFixed(6);
        if (tipoField && !tipoField.value) {
            tipoField.value = "goto";
        }
    }

    if (Number.isFinite(targetLat) && Number.isFinite(targetLon)) {
        setTargetMarker(targetLat, targetLon);
    }

    map.on("click", function (event) {
        setTargetMarker(event.latlng.lat, event.latlng.lng);
    });

    const quickCommandButton = document.querySelector("[data-drone-quick-command='rth']");
    if (quickCommandButton) {
        quickCommandButton.addEventListener("click", function () {
            const tipoField = commandForm.querySelector("#id_comando-tipo_comando");
            if (tipoField) {
                tipoField.value = "rth";
            }
            commandForm.submit();
        });
    }

    requestDroneStatus(apiEstadoUrl, "GET").catch(function () {
        appendLog("erro", "Não foi possível obter o estado inicial do drone.");
    });

    window.setInterval(function () {
        requestDroneStatus(apiEstadoUrl, "GET").catch(function () {
            appendLog("erro", "Falhou a atualização automática do estado do drone.");
        });
    }, 8000);
})();
