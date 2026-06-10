(() => {
    if (typeof window.L === "undefined") {
        return;
    }
    const mapContainer = document.getElementById("map");
    const projetoDataNode = document.getElementById("projeto-data");
    const furosDataNode = document.getElementById("furos-data");
    const config = document.getElementById("projeto-detail-config");
    if (!mapContainer || !projetoDataNode || !furosDataNode || !config) {
        return;
    }

    const furoPlaceholder = config.dataset.furoPlaceholder || "00000000-0000-0000-0000-000000000000";
    const furoSlugPlaceholder = config.dataset.furoSlugPlaceholder || "furo-slug-placeholder";
    const furoDetailBaseUrl = config.dataset.furoDetailBaseUrl || "";
    const empresaContexto = config.dataset.empresaContexto || "";
    const projetoMapa = JSON.parse(projetoDataNode.textContent || "{}");
    const furos = JSON.parse(furosDataNode.textContent || "[]")
        .map((furo) => ({ ...furo, lat: Number(furo.lat), lon: Number(furo.lon) }))
        .filter((furo) => Number.isFinite(furo.lat) && Number.isFinite(furo.lon));

    function furoDetailUrl(id, slug) {
        const url = furoDetailBaseUrl
            .replace(furoPlaceholder, String(id))
            .replace(furoSlugPlaceholder, String(slug || id));
        if (empresaContexto) {
            return `${url}?empresa_contexto=${encodeURIComponent(empresaContexto)}`;
        }
        return url;
    }

    let centroLat = Number(projetoMapa.lat);
    let centroLon = Number(projetoMapa.lon);
    if ((!Number.isFinite(centroLat) || !Number.isFinite(centroLon)) && furos.length) {
        centroLat = furos[0].lat;
        centroLon = furos[0].lon;
    }
    if (!Number.isFinite(centroLat) || !Number.isFinite(centroLon)) {
        centroLat = 39.5;
        centroLon = -8.0;
    }

    const map = window.L.map("map").setView([centroLat, centroLon], 12);
    window.setTimeout(() => map.invalidateSize(), 200);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    const projetoLat = Number(projetoMapa.lat);
    const projetoLon = Number(projetoMapa.lon);
    if (Number.isFinite(projetoLat) && Number.isFinite(projetoLon)) {
        window.L.marker([projetoLat, projetoLon])
            .addTo(map)
            .bindPopup(`<strong>${projetoMapa.nome || "Projeto"}</strong><br>${projetoMapa.cidade || "-"}, ${projetoMapa.pais || "-"}`);
    }

    const info = document.getElementById("furoInfo");
    const prevBtn = document.getElementById("prevFuroBtn");
    const nextBtn = document.getElementById("nextFuroBtn");
    const abrirBtn = document.getElementById("abrirFuroBtn");
    let furoIndex = 0;

    furos.forEach((furo, index) => {
        const marker = window.L.circleMarker([furo.lat, furo.lon], {
            radius: 8,
            color: "#ffffff",
            weight: 2,
            fillColor: "#2563eb",
            fillOpacity: 0.95
        }).addTo(map);

        marker.bindPopup(`
            <strong>${furo.nome}</strong><br>
            Profundidade atual: ${furo.profundidade_atual} m<br>
            Inclinação: ${furo.inclinacao}°<br>
            Azimute: ${furo.azimute}°
        `);

        marker.on("click", () => selecionarFuro(index, true));
        marker.on("dblclick", () => {
            window.location.href = furoDetailUrl(furo.id, furo.slug);
        });

        furo.marker = marker;
    });

    function resetarMarcadores() {
        furos.forEach((furo) => {
            if (!furo.marker) return;
            furo.marker.setStyle({
                radius: 8,
                color: "#ffffff",
                weight: 2,
                fillColor: "#2563eb",
                fillOpacity: 0.95
            });
        });
    }

    function destacarFuroAtual() {
        if (!furos.length) return;
        resetarMarcadores();
        const furo = furos[furoIndex];
        furo.marker.setStyle({
            radius: 11,
            color: "#111827",
            weight: 3,
            fillColor: "#f59e0b",
            fillOpacity: 1
        });
    }

    function atualizarInfo() {
        if (!info || !prevBtn || !nextBtn || !abrirBtn) return;
        if (!furos.length) {
            info.innerHTML = "Sem furos com coordenadas.";
            abrirBtn.disabled = true;
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            return;
        }
        const furo = furos[furoIndex];
        info.innerHTML = `
            <strong>${furo.nome}</strong><br>
            Profundidade atual: ${furo.profundidade_atual} m |
            Inclinação: ${furo.inclinacao}° |
            Azimute: ${furo.azimute}°
        `;
        abrirBtn.disabled = false;
        prevBtn.disabled = false;
        nextBtn.disabled = false;
    }

    function focarFuro() {
        if (!furos.length) return;
        const furo = furos[furoIndex];
        map.flyTo([furo.lat, furo.lon], 14, { duration: 1.2 });
        destacarFuroAtual();
        furo.marker.openPopup();
        atualizarInfo();
    }

    function selecionarFuro(index, focar = true) {
        if (!furos.length) return;
        furoIndex = index;
        destacarFuroAtual();
        atualizarInfo();
        if (focar) {
            const furo = furos[furoIndex];
            map.flyTo([furo.lat, furo.lon], 14, { duration: 1.2 });
            furo.marker.openPopup();
        }
    }

    prevBtn?.addEventListener("click", () => {
        if (!furos.length) return;
        furoIndex = (furoIndex - 1 + furos.length) % furos.length;
        focarFuro();
    });

    nextBtn?.addEventListener("click", () => {
        if (!furos.length) return;
        furoIndex = (furoIndex + 1) % furos.length;
        focarFuro();
    });

    abrirBtn?.addEventListener("click", () => {
        if (!furos.length) return;
        const furo = furos[furoIndex];
        window.location.href = furoDetailUrl(furo.id, furo.slug);
    });

    if (furos.length > 0) {
        const bounds = window.L.latLngBounds(furos.map((furo) => [furo.lat, furo.lon]));
        map.fitBounds(bounds.pad(0.2));
        selecionarFuro(0, false);
    } else {
        atualizarInfo();
    }
})();
