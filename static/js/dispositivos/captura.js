(() => {
    const root = document.getElementById("captura-root");
    if (!root) {
        return;
    }

    const btnIniciarProcura = document.getElementById("btn-iniciar-procura");
    const btnPararProcura = document.getElementById("btn-parar-procura");
    const btnIniciarBluetooth = document.getElementById("btn-iniciar-bluetooth");
    const btnPararBluetooth = document.getElementById("btn-parar-bluetooth");
    const btnTestar = document.getElementById("btn-testar-leitura");
    const selectDispositivo = document.getElementById("dispositivo_id");
    const logBox = document.getElementById("device-debug-log");
    const portList = document.getElementById("device-port-list");
    const bluetoothList = document.getElementById("device-bluetooth-list");
    const payloadTexto = document.getElementById("device-payload-texto");
    const payloadHex = document.getElementById("device-payload-hex");
    const payloadTextoLabel = document.getElementById("device-payload-texto-label");
    const payloadHexLabel = document.getElementById("device-payload-hex-label");
    const payloadMeta = document.getElementById("device-debug-meta");
    const statusChip = document.getElementById("device-search-status");
    const bluetoothStatusChip = document.getElementById("device-bluetooth-status");
    const discoveredList = document.getElementById("device-discovered-list");
    const wbSessaoSelect = document.getElementById("wb_sessao_importacao_id");
    const wbServiceUuidInput = document.getElementById("wb_service_uuid");
    const wbCharUuidInput = document.getElementById("wb_char_uuid");
    const wbDetectBtn = document.getElementById("btn-web-bluetooth-detect");
    const wbConnectBtn = document.getElementById("btn-web-bluetooth-connect");
    const wbSendBtn = document.getElementById("btn-web-bluetooth-send");
    const wbStatus = document.getElementById("wb-status");
    const csrfToken = document.querySelector("#captura-form input[name=csrfmiddlewaretoken]")?.value;

    const procurarUsbUrl = root.dataset.apiProcurarUsbUrl || "";
    const procurarBluetoothUrl = root.dataset.apiProcurarBluetoothUrl || "";
    const testarUsbUrl = root.dataset.apiTestarUsbUrl || "";
    const inspecionarBluetoothUrl = root.dataset.apiInspecionarBluetoothUrl || "";
    const guardarDispositivoUrl = root.dataset.apiGuardarDispositivoUrl || "";
    const escutarDispositivoUrl = root.dataset.apiEscutarDispositivoUrl || "";
    const webBluetoothPreviewUrl = root.dataset.apiWebBluetoothPreviewUrl || "";

    if (
        !procurarUsbUrl ||
        !procurarBluetoothUrl ||
        !testarUsbUrl ||
        !inspecionarBluetoothUrl ||
        !guardarDispositivoUrl ||
        !escutarDispositivoUrl
    ) {
        return;
    }

    let procuraTimer = null;
    let procuraAtiva = false;
    let bluetoothTimer = null;
    let bluetoothAtivo = false;
    const discoveredDevices = new Map();
    let latestBluetoothDevices = [];
    let highlightedBluetoothAddress = "";
    let webBluetoothPayloadTexto = "";
    let webBluetoothFilename = "";

    function updateStatus(target, label, tone) {
        target.textContent = label;
        target.className = `device-status-chip device-status-chip--${tone}`;
    }

    function appendLog(message, type = "info") {
        const line = document.createElement("div");
        line.className = `device-debug-line device-debug-line--${type}`;
        line.textContent = message;
        logBox.appendChild(line);
        logBox.scrollTop = logBox.scrollHeight;
    }

    function resetPayload() {
        payloadTextoLabel.textContent = "Texto";
        payloadHexLabel.textContent = "Hex";
        payloadTexto.textContent = "Sem dados ainda.";
        payloadHex.textContent = "Sem dados ainda.";
        payloadMeta.innerHTML = "";
    }

    function setWbStatus(message, tone = "info") {
        if (!wbStatus) {
            return;
        }
        wbStatus.textContent = message;
        wbStatus.className = tone === "error"
            ? "text-xs text-red-700 mt-2"
            : tone === "success"
                ? "text-xs text-green-700 mt-2"
                : "text-xs text-gray-500 mt-2";
    }

    function renderPorts(portas) {
        if (!portas.length) {
            portList.innerHTML = '<div class="device-empty-state">Nenhuma porta encontrada.</div>';
            return;
        }

        portList.innerHTML = portas.map((porta) => `
            <div class="device-port-card">
                <p class="device-port-name">${porta.device || "-"}</p>
                <p class="device-port-description">${porta.description || "Sem descrição"}</p>
                <p class="device-port-meta">${porta.manufacturer || ""} ${porta.product || ""}</p>
                <div class="device-port-actions">
                    <button
                        type="button"
                        class="device-btn device-btn--secondary device-btn--small"
                        data-action="guardar-dispositivo"
                        data-channel="usb_serial"
                        data-identifier="${porta.device || ""}"
                        data-name="${porta.product || porta.description || porta.device || "USB/Serial"}"
                        data-description="${porta.description || ""}"
                        data-baudrate="115200">
                        Guardar dispositivo
                    </button>
                    <button
                        type="button"
                        class="device-btn device-btn--info device-btn--small"
                        data-action="escutar-dispositivo"
                        data-channel="usb_serial"
                        data-identifier="${porta.device || ""}"
                        data-name="${porta.product || porta.description || porta.device || "USB/Serial"}"
                        data-baudrate="115200">
                        Escutar
                    </button>
                </div>
            </div>
        `).join("");
    }

    function updateDiscoveredDevices(channel, items) {
        items.forEach((item) => {
            const key = channel === "usb"
                ? `usb:${item.device || item.name || Math.random()}`
                : `bluetooth:${item.address || item.name || Math.random()}`;

            discoveredDevices.set(key, {
                channel,
                title: channel === "usb" ? (item.device || item.name || "USB/Serial") : (item.name || "Bluetooth"),
                subtitle: channel === "usb"
                    ? (item.description || "Sem descrição")
                    : (item.address || "Sem endereço"),
                address: channel === "usb" ? "" : (item.address || ""),
                meta: channel === "usb"
                    ? [item.manufacturer, item.product, item.serial_number].filter(Boolean).join(" · ")
                    : [`RSSI: ${item.rssi ?? "-"}`, item.details].filter(Boolean).join(" · "),
                kindLabel: channel === "usb"
                    ? "USB"
                    : (item.tipo_label || "Bluetooth"),
                kindTone: channel === "usb"
                    ? "usb"
                    : (item.tipo_detectado === "candidato_medicao" ? "candidate" : "generic"),
                kindDetail: channel === "usb"
                    ? "Porta detetada no sistema."
                    : (item.tipo_detalhe || "Dispositivo Bluetooth detetado."),
                reasons: channel === "usb" ? [] : (item.motivos || []),
                isHighlighted: channel === "bluetooth" && item.address && item.address === highlightedBluetoothAddress,
            });
        });

        renderDiscoveredDevices();
    }

    function renderDiscoveredDevices() {
        const items = Array.from(discoveredDevices.values());
        if (!items.length) {
            discoveredList.innerHTML = '<div class="device-empty-state">Ainda não foram encontrados dispositivos.</div>';
            return;
        }

        discoveredList.innerHTML = items.map((item) => `
            <div class="device-discovered-card ${item.isHighlighted ? "device-discovered-card--highlighted" : ""}">
                <div class="device-discovered-top">
                    <div class="device-chip-group">
                        <span class="device-meta-chip device-meta-chip--${item.kindTone}">${item.kindLabel}</span>
                        ${item.isHighlighted ? `<span class="device-meta-chip device-meta-chip--best">Melhor candidato</span>` : ""}
                    </div>
                </div>
                <p class="device-port-name">${item.title}</p>
                <p class="device-port-description">${item.subtitle}</p>
                <p class="device-port-meta">${item.meta || "Sem metadados adicionais"}</p>
                <p class="device-port-note">${item.kindDetail}</p>
                ${item.reasons.length ? `<p class="device-port-reasons">Sinais: ${item.reasons.join(" · ")}</p>` : ""}
                <div class="device-port-actions">
                    <button
                        type="button"
                        class="device-btn device-btn--secondary device-btn--small"
                        data-action="guardar-dispositivo"
                        data-channel="${item.channel === "bluetooth" ? "bluetooth" : "usb_serial"}"
                        data-identifier="${item.channel === "bluetooth" ? (item.address || "") : (item.title || "")}"
                        data-name="${item.title}"
                        data-description="${item.subtitle || ""}">
                        Guardar dispositivo
                    </button>
                    <button
                        type="button"
                        class="device-btn device-btn--info device-btn--small"
                        data-action="escutar-dispositivo"
                        data-channel="bluetooth"
                        data-identifier="${item.address || ""}"
                        data-name="${item.title}">
                        Escutar
                    </button>
                    <button
                        type="button"
                        class="device-btn device-btn--secondary device-btn--small"
                        data-action="${item.channel === "bluetooth" ? "inspecionar-bluetooth" : "escutar-dispositivo"}"
                        data-channel="${item.channel === "bluetooth" ? "bluetooth" : "usb_serial"}"
                        data-address="${item.address || ""}"
                        data-identifier="${item.channel === "bluetooth" ? (item.address || "") : (item.title || "")}"
                        data-name="${item.title}">
                        ${item.channel === "bluetooth" ? "Inspecionar" : "Escutar"}
                    </button>
                </div>
            </div>
        `).join("");
    }

    function renderBluetooth(dispositivos) {
        latestBluetoothDevices = dispositivos;

        if (!dispositivos.length) {
            bluetoothList.innerHTML = '<div class="device-empty-state">Nenhum dispositivo Bluetooth encontrado.</div>';
            return;
        }

        bluetoothList.innerHTML = dispositivos.map((device) => `
            <div class="device-port-card ${device.address === highlightedBluetoothAddress ? "device-port-card--highlighted" : ""}">
                <div class="device-port-top">
                    <p class="device-port-name">${device.name || "Sem nome"}</p>
                    <div class="device-chip-group">
                        <span class="device-meta-chip device-meta-chip--${device.tipo_detectado === "candidato_medicao" ? "candidate" : "generic"}">
                            ${device.tipo_label || "Bluetooth"}
                        </span>
                        ${device.address === highlightedBluetoothAddress ? `<span class="device-meta-chip device-meta-chip--best">Melhor candidato</span>` : ""}
                    </div>
                </div>
                <p class="device-port-description">${device.address || "-"}</p>
                <p class="device-port-meta">RSSI: ${device.rssi ?? "-"} ${device.details ? `· ${device.details}` : ""}</p>
                <p class="device-port-note">${device.tipo_detalhe || "Dispositivo Bluetooth detetado."}</p>
                ${(device.motivos || []).length ? `<p class="device-port-reasons">Sinais: ${(device.motivos || []).join(" · ")}</p>` : ""}
                <div class="device-port-actions">
                    <button
                        type="button"
                        class="device-btn device-btn--secondary device-btn--small"
                        data-action="guardar-dispositivo"
                        data-channel="bluetooth"
                        data-identifier="${device.address || ""}"
                        data-name="${device.name || "Sem nome"}"
                        data-description="${device.tipo_detalhe || "Dispositivo Bluetooth"}">
                        Guardar dispositivo
                    </button>
                    <button
                        type="button"
                        class="device-btn device-btn--info device-btn--small"
                        data-action="escutar-dispositivo"
                        data-channel="bluetooth"
                        data-identifier="${device.address || ""}"
                        data-name="${device.name || "Sem nome"}">
                        Escutar
                    </button>
                    <button
                        type="button"
                        class="device-btn device-btn--secondary device-btn--small"
                        data-action="inspecionar-bluetooth"
                        data-address="${device.address || ""}"
                        data-name="${device.name || "Sem nome"}">
                        Inspecionar
                    </button>
                </div>
            </div>
        `).join("");
    }

    function renderLeitura(leitura) {
        payloadTextoLabel.textContent = "Texto";
        payloadHexLabel.textContent = leitura.parece_csv ? "Hex / CSV" : "Hex";
        payloadTexto.textContent = leitura.payload_texto || "Sem conteúdo em texto.";
        payloadHex.textContent = leitura.parece_csv
            ? `${leitura.payload_hex || "Sem conteúdo hexadecimal."}\n\nCSV preview:\n${JSON.stringify(leitura.csv_preview || [], null, 2)}`
            : (leitura.payload_hex || "Sem conteúdo hexadecimal.");
        payloadMeta.innerHTML = `
            <span class="device-meta-chip">Porta: ${leitura.porta || "-"}</span>
            <span class="device-meta-chip">Baudrate: ${leitura.baudrate}</span>
            <span class="device-meta-chip">Bytes: ${leitura.total_bytes}</span>
            <span class="device-meta-chip">Timeout: ${leitura.timeout}s</span>
            ${leitura.parece_csv ? '<span class="device-meta-chip device-meta-chip--candidate">CSV detetado</span>' : ""}
        `;
    }

    function renderInspecaoBluetooth(inspecao) {
        const services = inspecao.services || [];
        const manufacturerData = inspecao.manufacturer_data || {};
        const advertisedUuids = inspecao.advertised_uuids || [];

        payloadTextoLabel.textContent = "Resumo Bluetooth";
        payloadHexLabel.textContent = "Serviços / características";
        payloadMeta.innerHTML = `
            <span class="device-meta-chip device-meta-chip--${inspecao.tipo_detectado === "candidato_medicao" ? "candidate" : "generic"}">${inspecao.tipo_label || "Bluetooth"}</span>
            <span class="device-meta-chip">Endereço: ${inspecao.address || "-"}</span>
            <span class="device-meta-chip">RSSI: ${inspecao.rssi ?? "-"}</span>
            <span class="device-meta-chip">Ligado: ${inspecao.connected ? "Sim" : "Não"}</span>
            <span class="device-meta-chip">Serviços: ${services.length}</span>
        `;

        payloadTexto.textContent = JSON.stringify({
            nome: inspecao.name,
            endereco: inspecao.address,
            classificacao: inspecao.tipo_label,
            detalhe: inspecao.tipo_detalhe,
            sinais: inspecao.motivos || [],
            manufacturer_data: manufacturerData,
            advertised_uuids: advertisedUuids,
        }, null, 2);

        payloadHex.textContent = services.length
            ? services.map((service) => {
                const chars = (service.characteristics || []).map((char) =>
                    `  - ${char.uuid}${char.properties?.length ? ` [${char.properties.join(", ")}]` : ""}${char.description ? ` ${char.description}` : ""}`
                ).join("\n");
                return `${service.uuid}${service.description ? ` ${service.description}` : ""}${chars ? `\n${chars}` : ""}`;
            }).join("\n\n")
            : "Sem serviços BLE visíveis.";
    }

    function definirMelhorCandidatoBluetooth(inspecao) {
        if (!inspecao?.address) {
            return;
        }

        const services = inspecao.services || [];
        const score = (
            (inspecao.tipo_detectado === "candidato_medicao" ? 3 : 0) +
            (services.length > 0 ? 2 : 0) +
            ((inspecao.advertised_uuids || []).length > 0 ? 1 : 0) +
            (Object.keys(inspecao.manufacturer_data || {}).length > 0 ? 1 : 0)
        );

        if (score < 2) {
            return;
        }

        highlightedBluetoothAddress = inspecao.address;
        appendLog(`Dispositivo marcado como melhor candidato: ${inspecao.name || inspecao.address}.`, "sucesso");

        latestBluetoothDevices = latestBluetoothDevices.map((device) => (
            device.address === inspecao.address
                ? {
                    ...device,
                    tipo_detectado: inspecao.tipo_detectado,
                    tipo_label: inspecao.tipo_label,
                    tipo_detalhe: inspecao.tipo_detalhe,
                    motivos: inspecao.motivos || [],
                }
                : device
        ));

        renderBluetooth(latestBluetoothDevices);
        updateDiscoveredDevices("bluetooth", latestBluetoothDevices);
    }

    async function procurarPortas() {
        if (!procuraAtiva) {
            return;
        }
        portList.innerHTML = '<div class="device-empty-state">A procurar portas...</div>';

        try {
            const response = await fetch(procurarUsbUrl);
            const data = await response.json();

            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));
            renderPorts(data.portas || []);
            updateDiscoveredDevices("usb", data.portas || []);
        } catch (error) {
            appendLog(`Erro ao procurar portas: ${error}`, "erro");
            portList.innerHTML = '<div class="device-empty-state">Não foi possível obter a lista de portas.</div>';
        }
    }

    function iniciarProcura() {
        if (procuraAtiva) {
            appendLog("A procura USB já está em curso.", "info");
            return;
        }

        procuraAtiva = true;
        btnIniciarProcura.disabled = true;
        btnPararProcura.disabled = false;
        updateStatus(statusChip, "USB a procurar", "running");
        appendLog("Procura USB iniciada.", "info");
        appendLog("A procurar portas USB/serial em intervalos regulares...", "info");
        procurarPortas();
        procuraTimer = window.setInterval(procurarPortas, 4000);
    }

    function pararProcura() {
        if (!procuraAtiva) {
            appendLog("A procura USB já se encontra parada.", "info");
            return;
        }

        procuraAtiva = false;
        btnIniciarProcura.disabled = false;
        btnPararProcura.disabled = true;
        updateStatus(statusChip, "USB parado", "idle");
        if (procuraTimer) {
            window.clearInterval(procuraTimer);
            procuraTimer = null;
        }
        appendLog("Procura USB parada pelo utilizador.", "info");
    }

    async function procurarBluetooth() {
        if (!bluetoothAtivo) {
            return;
        }

        bluetoothList.innerHTML = '<div class="device-empty-state">A procurar dispositivos Bluetooth...</div>';

        try {
            const response = await fetch(procurarBluetoothUrl);
            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));
            renderBluetooth(data.dispositivos || []);
            updateDiscoveredDevices("bluetooth", data.dispositivos || []);
        } catch (error) {
            appendLog(`Erro ao procurar Bluetooth: ${error}`, "erro");
            bluetoothList.innerHTML = '<div class="device-empty-state">Não foi possível obter a lista Bluetooth.</div>';
            updateStatus(bluetoothStatusChip, "Bluetooth erro", "error");
        }
    }

    function iniciarBluetooth() {
        if (bluetoothAtivo) {
            appendLog("A procura Bluetooth já está em curso.", "info");
            return;
        }

        bluetoothAtivo = true;
        btnIniciarBluetooth.disabled = true;
        btnPararBluetooth.disabled = false;
        updateStatus(bluetoothStatusChip, "Bluetooth a procurar", "running");
        appendLog("Procura Bluetooth iniciada.", "info");
        appendLog("A procurar dispositivos Bluetooth em intervalos regulares...", "info");
        procurarBluetooth();
        bluetoothTimer = window.setInterval(procurarBluetooth, 6000);
    }

    function pararBluetooth() {
        if (!bluetoothAtivo) {
            appendLog("A procura Bluetooth já se encontra parada.", "info");
            return;
        }

        bluetoothAtivo = false;
        btnIniciarBluetooth.disabled = false;
        btnPararBluetooth.disabled = true;
        updateStatus(bluetoothStatusChip, "Bluetooth parado", "idle");
        if (bluetoothTimer) {
            window.clearInterval(bluetoothTimer);
            bluetoothTimer = null;
        }
        appendLog("Procura Bluetooth parada pelo utilizador.", "info");
    }

    async function testarLeitura() {
        const dispositivoId = selectDispositivo.value;
        if (!dispositivoId) {
            appendLog("Selecione um dispositivo antes de testar a leitura.", "erro");
            return;
        }

        appendLog("A preparar teste de leitura USB...", "info");
        resetPayload();

        try {
            const formData = new FormData();
            formData.append("dispositivo_id", dispositivoId);
            updateStatus(statusChip, "USB a ler", "running");

            const response = await fetch(testarUsbUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });

            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));

            if (data.ok && data.leitura) {
                renderLeitura(data.leitura);
                updateStatus(statusChip, procuraAtiva ? "USB a procurar" : "USB parado", procuraAtiva ? "running" : "idle");
            } else {
                updateStatus(statusChip, "USB erro", "error");
            }
        } catch (error) {
            appendLog(`Erro ao testar leitura: ${error}`, "erro");
            updateStatus(statusChip, "USB erro", "error");
        }
    }

    async function inspecionarBluetooth(address, name) {
        if (!address) {
            appendLog("O dispositivo Bluetooth não tem endereço disponível para inspeção.", "erro");
            return;
        }

        appendLog(`A iniciar inspeção Bluetooth para ${name || address}...`, "info");
        updateStatus(bluetoothStatusChip, "Bluetooth a inspecionar", "running");
        resetPayload();

        try {
            const formData = new FormData();
            formData.append("address", address);
            formData.append("name", name || "");

            const response = await fetch(inspecionarBluetoothUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });

            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));

            if (data.ok && data.inspecao) {
                renderInspecaoBluetooth(data.inspecao);
                definirMelhorCandidatoBluetooth(data.inspecao);
                updateStatus(
                    bluetoothStatusChip,
                    bluetoothAtivo ? "Bluetooth a procurar" : "Bluetooth parado",
                    bluetoothAtivo ? "running" : "idle"
                );
            } else {
                updateStatus(bluetoothStatusChip, "Bluetooth erro", "error");
            }
        } catch (error) {
            appendLog(`Erro ao inspecionar Bluetooth: ${error}`, "erro");
            updateStatus(bluetoothStatusChip, "Bluetooth erro", "error");
        }
    }

    async function guardarDispositivoEncontrado(payload) {
        const furoId = document.getElementById("furo_id")?.value;
        appendLog(`A guardar dispositivo encontrado: ${payload.name || payload.identifier}.`, "info");

        try {
            const formData = new FormData();
            formData.append("canal", payload.channel);
            formData.append("identifier", payload.identifier || "");
            formData.append("name", payload.name || "");
            formData.append("description", payload.description || "");
            formData.append("baudrate", payload.baudrate || "115200");
            formData.append("furo_id", furoId || "");

            const response = await fetch(guardarDispositivoUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });
            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));
        } catch (error) {
            appendLog(`Erro ao guardar dispositivo: ${error}`, "erro");
        }
    }

    async function escutarDispositivoEncontrado(payload) {
        appendLog(`A iniciar escuta do dispositivo ${payload.name || payload.identifier}.`, "info");
        resetPayload();

        try {
            const formData = new FormData();
            formData.append("canal", payload.channel);
            formData.append("identifier", payload.identifier || "");
            formData.append("name", payload.name || "");
            formData.append("baudrate", payload.baudrate || "115200");

            const response = await fetch(escutarDispositivoUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });
            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));

            if (data.ok && data.modo === "usb_serial" && data.leitura) {
                renderLeitura(data.leitura);
                updateStatus(statusChip, procuraAtiva ? "USB a procurar" : "USB parado", procuraAtiva ? "running" : "idle");
            } else if (data.ok && data.modo === "bluetooth" && data.inspecao) {
                renderInspecaoBluetooth(data.inspecao);
                definirMelhorCandidatoBluetooth(data.inspecao);
                updateStatus(
                    bluetoothStatusChip,
                    bluetoothAtivo ? "Bluetooth a procurar" : "Bluetooth parado",
                    bluetoothAtivo ? "running" : "idle"
                );
            }
        } catch (error) {
            appendLog(`Erro ao escutar dispositivo: ${error}`, "erro");
        }
    }

    function _formatUuid(input) {
        const texto = (input || "").trim().toLowerCase();
        if (!texto) return "";
        if (texto.length === 4 || texto.length === 8) {
            return `0000${texto.slice(-4)}-0000-1000-8000-00805f9b34fb`;
        }
        return texto;
    }

    async function detetarUuidsWebBluetooth() {
        if (!navigator.bluetooth) {
            appendLog("Web Bluetooth não suportado neste navegador.", "erro");
            setWbStatus("Web Bluetooth não suportado. Usa Chrome ou Edge em HTTPS.", "error");
            return;
        }

        wbDetectBtn.disabled = true;
        setWbStatus("A tentar detetar UUIDs automaticamente...", "info");
        appendLog("A abrir seletor Bluetooth para deteção de UUIDs.", "info");

        try {
            const commonServices = [
                "device_information",
                "battery_service",
                "0000180a-0000-1000-8000-00805f9b34fb",
                "0000180f-0000-1000-8000-00805f9b34fb",
            ];
            const device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: commonServices,
            });
            const server = await device.gatt.connect();
            const services = await server.getPrimaryServices();

            if (!services.length) {
                setWbStatus("Dispositivo ligado, mas sem services acessíveis nesta sessão.", "error");
                appendLog("Sem services BLE acessíveis. Pode exigir UUIDs específicos do fabricante.", "erro");
                return;
            }

            let foundService = "";
            let foundCharacteristic = "";
            for (const service of services) {
                const chars = await service.getCharacteristics();
                const preferred = chars.find((c) => c.properties.read || c.properties.notify);
                if (preferred) {
                    foundService = service.uuid;
                    foundCharacteristic = preferred.uuid;
                    break;
                }
            }

            if (!foundService || !foundCharacteristic) {
                setWbStatus("UUIDs não detetados automaticamente. Preenche manualmente.", "error");
                appendLog("Foram encontrados services, mas nenhuma characteristic legível/notificável.", "erro");
                return;
            }

            wbServiceUuidInput.value = foundService;
            wbCharUuidInput.value = foundCharacteristic;
            setWbStatus("UUIDs detetados com sucesso. Já podes clicar em ligar.", "success");
            appendLog(`UUIDs detetados: service ${foundService}, characteristic ${foundCharacteristic}.`, "sucesso");
        } catch (error) {
            appendLog(`Falha na deteção automática de UUIDs: ${error}`, "erro");
            setWbStatus(`Falha ao detetar UUIDs: ${error}`, "error");
        } finally {
            wbDetectBtn.disabled = false;
        }
    }

    async function lerViaWebBluetooth() {
        if (!navigator.bluetooth) {
            appendLog("Este navegador não suporta Web Bluetooth.", "erro");
            setWbStatus("Web Bluetooth não suportado neste navegador.", "error");
            return;
        }

        const serviceUuid = _formatUuid(wbServiceUuidInput?.value);
        const charUuid = _formatUuid(wbCharUuidInput?.value);
        if (!serviceUuid || !charUuid) {
            appendLog("Define Service UUID e Characteristic UUID antes de ligar.", "erro");
            setWbStatus("Faltam UUIDs BLE para leitura.", "error");
            return;
        }

        wbConnectBtn.disabled = true;
        setWbStatus("A ligar ao dispositivo Bluetooth...", "info");
        appendLog(`A iniciar Web Bluetooth para service ${serviceUuid}...`, "info");

        try {
            const device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [serviceUuid],
            });
            const server = await device.gatt.connect();
            const service = await server.getPrimaryService(serviceUuid);
            const characteristic = await service.getCharacteristic(charUuid);
            const value = await characteristic.readValue();

            const bytes = new Uint8Array(value.buffer);
            const decoder = new TextDecoder("utf-8");
            const texto = decoder.decode(bytes).trim();
            webBluetoothPayloadTexto = texto;
            webBluetoothFilename = `webbluetooth_${device.name || "dispositivo"}_${Date.now()}.csv`;

            payloadTextoLabel.textContent = "Web Bluetooth (texto)";
            payloadHexLabel.textContent = "Web Bluetooth (hex)";
            payloadTexto.textContent = texto || "Leitura vazia.";
            payloadHex.textContent = Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join(" ");
            payloadMeta.innerHTML = `
                <span class="device-meta-chip">Origem: Web Bluetooth</span>
                <span class="device-meta-chip">Dispositivo: ${device.name || "Sem nome"}</span>
                <span class="device-meta-chip">Service: ${serviceUuid}</span>
                <span class="device-meta-chip">Characteristic: ${charUuid}</span>
                <span class="device-meta-chip">Bytes: ${bytes.length}</span>
            `;

            appendLog("Leitura via Web Bluetooth concluída com sucesso.", "sucesso");
            setWbStatus("Leitura concluída. Podes enviar para pré-visualização.", "success");
            wbSendBtn.disabled = !texto;
        } catch (error) {
            appendLog(`Erro no Web Bluetooth: ${error}`, "erro");
            setWbStatus(`Falha Web Bluetooth: ${error}`, "error");
            wbSendBtn.disabled = true;
        } finally {
            wbConnectBtn.disabled = false;
        }
    }

    async function enviarLeituraWebBluetooth() {
        if (!webBluetoothPreviewUrl) {
            setWbStatus("Endpoint de preview indisponível nesta versão do servidor.", "error");
            appendLog("Endpoint Web Bluetooth preview não configurado no backend.", "erro");
            return;
        }
        const sessaoId = wbSessaoSelect?.value || "";
        if (!sessaoId) {
            setWbStatus("Seleciona a sessão de destino.", "error");
            appendLog("Web Bluetooth: sessão de destino não selecionada.", "erro");
            return;
        }
        if (!webBluetoothPayloadTexto.trim()) {
            setWbStatus("Não existe leitura para enviar.", "error");
            appendLog("Web Bluetooth: leitura vazia, nada para enviar.", "erro");
            return;
        }

        wbSendBtn.disabled = true;
        setWbStatus("A enviar leitura para pré-visualização...", "info");
        try {
            const formData = new FormData();
            formData.append("sessao_importacao_id", sessaoId);
            formData.append("payload_texto", webBluetoothPayloadTexto);
            formData.append("nome_ficheiro", webBluetoothFilename || `webbluetooth_${Date.now()}.csv`);

            const response = await fetch(webBluetoothPreviewUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData,
            });
            const data = await response.json();
            (data.eventos || []).forEach((evento) => appendLog(evento.mensagem, evento.tipo || "info"));

            if (!data.ok) {
                setWbStatus("Falha ao enviar leitura para pré-visualização.", "error");
                wbSendBtn.disabled = false;
                return;
            }

            setWbStatus("Pré-visualização criada com sucesso. A recarregar página...", "success");
            window.location.reload();
        } catch (error) {
            appendLog(`Erro ao enviar leitura Web Bluetooth: ${error}`, "erro");
            setWbStatus(`Erro ao enviar: ${error}`, "error");
            wbSendBtn.disabled = false;
        }
    }

    btnIniciarProcura?.addEventListener("click", iniciarProcura);
    btnPararProcura?.addEventListener("click", pararProcura);
    btnIniciarBluetooth?.addEventListener("click", iniciarBluetooth);
    btnPararBluetooth?.addEventListener("click", pararBluetooth);
    btnTestar?.addEventListener("click", testarLeitura);
    wbDetectBtn?.addEventListener("click", detetarUuidsWebBluetooth);
    wbConnectBtn?.addEventListener("click", lerViaWebBluetooth);
    wbSendBtn?.addEventListener("click", enviarLeituraWebBluetooth);

    bluetoothList?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-action='inspecionar-bluetooth']");
        if (button) {
            inspecionarBluetooth(button.dataset.address, button.dataset.name);
            return;
        }
        const saveButton = event.target.closest("[data-action='guardar-dispositivo']");
        if (saveButton) {
            guardarDispositivoEncontrado({
                channel: saveButton.dataset.channel,
                identifier: saveButton.dataset.identifier,
                name: saveButton.dataset.name,
                description: saveButton.dataset.description,
                baudrate: saveButton.dataset.baudrate,
            });
            return;
        }
        const listenButton = event.target.closest("[data-action='escutar-dispositivo']");
        if (listenButton) {
            escutarDispositivoEncontrado({
                channel: listenButton.dataset.channel,
                identifier: listenButton.dataset.identifier,
                name: listenButton.dataset.name,
                baudrate: listenButton.dataset.baudrate,
            });
        }
    });

    discoveredList?.addEventListener("click", (event) => {
        const inspectButton = event.target.closest("[data-action='inspecionar-bluetooth']");
        if (inspectButton) {
            inspecionarBluetooth(inspectButton.dataset.address, inspectButton.dataset.name);
            return;
        }
        const saveButton = event.target.closest("[data-action='guardar-dispositivo']");
        if (saveButton) {
            guardarDispositivoEncontrado({
                channel: saveButton.dataset.channel,
                identifier: saveButton.dataset.identifier,
                name: saveButton.dataset.name,
                description: saveButton.dataset.description,
                baudrate: saveButton.dataset.baudrate,
            });
            return;
        }
        const listenButton = event.target.closest("[data-action='escutar-dispositivo']");
        if (listenButton) {
            escutarDispositivoEncontrado({
                channel: listenButton.dataset.channel,
                identifier: listenButton.dataset.identifier,
                name: listenButton.dataset.name,
                baudrate: listenButton.dataset.baudrate,
            });
        }
    });

    portList?.addEventListener("click", (event) => {
        const saveButton = event.target.closest("[data-action='guardar-dispositivo']");
        if (saveButton) {
            guardarDispositivoEncontrado({
                channel: saveButton.dataset.channel,
                identifier: saveButton.dataset.identifier,
                name: saveButton.dataset.name,
                description: saveButton.dataset.description,
                baudrate: saveButton.dataset.baudrate,
            });
            return;
        }
        const listenButton = event.target.closest("[data-action='escutar-dispositivo']");
        if (listenButton) {
            escutarDispositivoEncontrado({
                channel: listenButton.dataset.channel,
                identifier: listenButton.dataset.identifier,
                name: listenButton.dataset.name,
                baudrate: listenButton.dataset.baudrate,
            });
        }
    });
})();
