(() => {
    const config = document.getElementById("projeto-list-config");
    const dataNode = document.getElementById("projetos-data");
    const mapElement = document.getElementById("map");
    if (!config || !dataNode || !mapElement || typeof window.L === "undefined") {
        return;
    }

    const projetoDetailPlaceholder = config.dataset.detailPlaceholder || "00000000-0000-0000-0000-000000000000";
    const projetoDetailBaseUrl = config.dataset.detailBaseUrl || "";
    const projetos = JSON.parse(dataNode.textContent || "[]");
    const map = window.L.map("map").setView([0, 0], 2);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    let projetoIndex = 0;
    const marcadores = [];
    const info = document.getElementById("projetoInfo");
    const prevBtn = document.getElementById("prevProjetoBtn");
    const nextBtn = document.getElementById("nextProjetoBtn");
    const abrirBtn = document.getElementById("abrirProjetoBtn");

    function projetoDetailUrl(projeto) {
        const url = projetoDetailBaseUrl.replace(projetoDetailPlaceholder, String(projeto.id));
        if (config.dataset.visaoGlobal === "true" && projeto.empresa_id) {
            return `${url}?empresa_contexto=${encodeURIComponent(projeto.empresa_id)}`;
        }
        return url;
    }

    projetos.forEach((projeto, index) => {
        if (projeto.localizacao_lat === null || projeto.localizacao_lon === null) {
            return;
        }
        const marker = window.L.circleMarker([projeto.localizacao_lat, projeto.localizacao_lon], {
            radius: 8,
            color: "#ffffff",
            weight: 2,
            fillColor: "#2563eb",
            fillOpacity: 0.95
        }).addTo(map);

        marker.bindPopup(`<strong>${projeto.nome}</strong><br>${projeto.cidade || "-"}, ${projeto.pais || "-"}`);
        marker.on("click", () => selecionarProjeto(index, true));
        marker.on("dblclick", () => {
            window.location.href = projetoDetailUrl(projeto);
        });
        marcadores.push({ index, marker });
    });

    function resetarCards() {
        document.querySelectorAll(".projeto-card").forEach((element) => {
            element.classList.remove("projeto-card-selected");
        });
    }

    function destacarCardAtual() {
        resetarCards();
        const element = document.getElementById(`projeto-${projetoIndex}`);
        if (element) {
            element.classList.add("projeto-card-selected");
        }
    }

    function resetarMarcadores() {
        marcadores.forEach((item) => {
            item.marker.setStyle({
                radius: 8,
                color: "#ffffff",
                weight: 2,
                fillColor: "#2563eb",
                fillOpacity: 0.95
            });
        });
    }

    function destacarMarcadorAtual() {
        resetarMarcadores();
        const item = marcadores.find((markerItem) => markerItem.index === projetoIndex);
        if (!item) {
            return;
        }
        item.marker.setStyle({
            radius: 11,
            color: "#111827",
            weight: 3,
            fillColor: "#f59e0b",
            fillOpacity: 1
        });
    }

    function atualizarInfo() {
        if (!info || !prevBtn || !nextBtn || !abrirBtn) {
            return;
        }
        if (!projetos.length) {
            info.innerHTML = "Sem projetos.";
            abrirBtn.disabled = true;
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            return;
        }
        const projeto = projetos[projetoIndex];
        info.innerHTML = `
            <a href="${projetoDetailUrl(projeto)}" class="projeto-map-link">
                ${projeto.nome}
            </a><br>
            Cliente: ${projeto.cliente || "-"} |
            Cidade: ${projeto.cidade || "-"} |
            País: ${projeto.pais || "-"}
        `;
        abrirBtn.disabled = false;
    }

    function focarProjeto() {
        const projeto = projetos[projetoIndex];
        destacarCardAtual();
        destacarMarcadorAtual();
        atualizarInfo();
        if (projeto.localizacao_lat === null || projeto.localizacao_lon === null) {
            return;
        }
        map.flyTo([projeto.localizacao_lat, projeto.localizacao_lon], 7, { duration: 1.2 });
        const item = marcadores.find((markerItem) => markerItem.index === projetoIndex);
        if (item) {
            item.marker.openPopup();
        }
    }

    function selecionarProjeto(index, focar = true) {
        projetoIndex = index;
        destacarCardAtual();
        destacarMarcadorAtual();
        atualizarInfo();
        if (focar) {
            focarProjeto();
        }
    }

    prevBtn?.addEventListener("click", () => {
        if (!projetos.length) {
            return;
        }
        projetoIndex = (projetoIndex - 1 + projetos.length) % projetos.length;
        focarProjeto();
    });

    nextBtn?.addEventListener("click", () => {
        if (!projetos.length) {
            return;
        }
        projetoIndex = (projetoIndex + 1) % projetos.length;
        focarProjeto();
    });

    abrirBtn?.addEventListener("click", () => {
        if (!projetos.length) {
            return;
        }
        window.location.href = projetoDetailUrl(projetos[projetoIndex]);
    });

    document.querySelectorAll(".projeto-card").forEach((card, index) => {
        card.addEventListener("click", () => selecionarProjeto(index, true));
        card.addEventListener("dblclick", () => {
            window.location.href = projetoDetailUrl(projetos[index]);
        });
    });

    const bounds = projetos
        .filter((projeto) => projeto.localizacao_lat !== null && projeto.localizacao_lon !== null)
        .map((projeto) => [projeto.localizacao_lat, projeto.localizacao_lon]);
    if (bounds.length) {
        map.fitBounds(bounds, { padding: [30, 30] });
    }
    if (projetos.length) {
        selecionarProjeto(0, false);
    }
})();
