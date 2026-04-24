(() => {
    const overlay = document.getElementById("overlay");
    const modal = document.getElementById("modal");
    const modalImage = document.getElementById("modal_img");
    const closeButton = document.getElementById("furo-modal-close");

    function abrirModal(src) {
        if (!overlay || !modal || !modalImage) return;
        modalImage.src = src;
        modal.style.display = "block";
        overlay.style.display = "block";
    }

    function fecharModal() {
        if (!overlay || !modal) return;
        modal.style.display = "none";
        overlay.style.display = "none";
    }

    document.querySelectorAll("[data-modal-image]").forEach((image) => {
        image.addEventListener("click", () => {
            abrirModal(image.getAttribute("data-modal-image"));
        });
    });

    closeButton?.addEventListener("click", fecharModal);
    overlay?.addEventListener("click", fecharModal);

    if (typeof window.L === "undefined") {
        return;
    }
    const dataNode = document.getElementById("furo-data");
    const mapElement = document.getElementById("map");
    if (!dataNode || !mapElement) {
        return;
    }

    const furoMapa = JSON.parse(dataNode.textContent || "{}");
    const lat = Number(furoMapa.lat);
    const lon = Number(furoMapa.lon);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        mapElement.innerHTML = "<div class='furo-map-empty'>Sem coordenadas para mostrar o mapa.</div>";
        return;
    }

    const holeLatLng = [lat, lon];
    const map = window.L.map("map", { zoomControl: true }).setView(holeLatLng, 16);
    window.setTimeout(() => {
        map.invalidateSize();
        map.setView(holeLatLng, Math.max(map.getZoom(), 16), { animate: false });
    }, 200);

    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const marker = window.L.marker(holeLatLng)
        .addTo(map)
        .bindPopup(`
            <strong>${furoMapa.nome}</strong><br>
            Projeto: ${furoMapa.projeto || "-"}<br>
            Profundidade atual: ${furoMapa.profundidade_atual} m<br>
            Profundidade alvo inicial: ${furoMapa.profundidade_alvo_inicial} m<br>
            Profundidade alvo atual: ${furoMapa.profundidade_alvo_atual} m<br>
            Inclinação planeada inicial: ${furoMapa.inclinacao_planeada_inicial}°<br>
            Azimute planeado inicial: ${furoMapa.azimute_planeado_inicial}°
        `)
        .openPopup();

    map.whenReady(() => {
        map.setView(holeLatLng, 16, { animate: false });
        marker.openPopup();
    });
})();
