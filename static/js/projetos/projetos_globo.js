(() => {
    if (typeof window.Cesium === "undefined") {
        return;
    }
    const config = document.getElementById("projetos-globo-config");
    const projetosData = document.getElementById("projetos_data");
    if (!config || !projetosData) {
        return;
    }

    const detailBaseUrl = config.dataset.projetoDetailBaseUrl || "";
    const detailPlaceholder = config.dataset.projetoDetailPlaceholder || "00000000-0000-0000-0000-000000000000";
    const projetos = JSON.parse(projetosData.textContent || "[]");

    const viewer = new window.Cesium.Viewer("cesiumContainer", {
        terrainProvider: window.Cesium.createWorldTerrain(),
        timeline: false,
        animation: false,
        sceneModePicker: true
    });

    projetos.forEach((projeto) => {
        if (!projeto.localizacao_lat || !projeto.localizacao_lon) {
            return;
        }
        viewer.entities.add({
            name: projeto.nome,
            position: window.Cesium.Cartesian3.fromDegrees(projeto.localizacao_lon, projeto.localizacao_lat, 100),
            point: { pixelSize: 12, color: window.Cesium.Color.RED },
            description: `<div class="globo-popup">
                <strong>${projeto.nome}</strong><br>
                <a href="${detailBaseUrl.replace(detailPlaceholder, projeto.id)}">Ver detalhes</a>
            </div>`
        });
    });

    if (viewer.entities.values.length > 0) {
        viewer.zoomTo(viewer.entities);
    }
})();
