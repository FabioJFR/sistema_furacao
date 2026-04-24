(() => {
    if (typeof window.Cesium === "undefined") {
        return;
    }
    const config = document.getElementById("globo-config");
    const projetosData = document.getElementById("projetos-data");
    if (!config || !projetosData) {
        return;
    }

    const token = config.dataset.cesiumToken || "";
    const detailBaseUrl = config.dataset.projetoDetailBaseUrl || "";
    const detailPlaceholder = config.dataset.projetoDetailPlaceholder || "00000000-0000-0000-0000-000000000000";
    const projetos = JSON.parse(projetosData.textContent || "[]");

    window.Cesium.Ion.defaultAccessToken = token;

    const viewer = new window.Cesium.Viewer("cesiumContainer", {
        terrainProvider: window.Cesium.createWorldTerrain(),
        timeline: false,
        animation: false,
        baseLayerPicker: true,
        geocoder: false,
        homeButton: true,
        sceneModePicker: true,
        navigationHelpButton: false
    });

    const pinBuilder = new window.Cesium.PinBuilder();
    projetos.forEach((projeto) => {
        if (projeto.localizacao_lat === null || projeto.localizacao_lon === null || Number.isNaN(projeto.localizacao_lat) || Number.isNaN(projeto.localizacao_lon)) {
            return;
        }

        const pin = pinBuilder.fromColor(window.Cesium.Color.BLUE, 48).toDataURL();
        viewer.entities.add({
            name: projeto.nome,
            position: window.Cesium.Cartesian3.fromDegrees(projeto.localizacao_lon, projeto.localizacao_lat, projeto.altitude || 0),
            billboard: {
                image: pin,
                verticalOrigin: window.Cesium.VerticalOrigin.BOTTOM
            },
            label: {
                text: projeto.nome,
                font: "14px sans-serif",
                fillColor: window.Cesium.Color.WHITE,
                outlineColor: window.Cesium.Color.BLACK,
                outlineWidth: 2,
                style: window.Cesium.LabelStyle.FILL_AND_OUTLINE,
                verticalOrigin: window.Cesium.VerticalOrigin.TOP,
                pixelOffset: new window.Cesium.Cartesian2(0, -40)
            },
            description: `
                <div class="globo-popup">
                    <h3 class="globo-popup-title">📁 ${projeto.nome}</h3>
                    <p class="globo-popup-location">📍 ${projeto.cidade || "-"} ${projeto.pais || ""}</p>
                    <p class="globo-popup-status">📊 Estado: ${projeto.status || "-"}</p>
                    <a href="${detailBaseUrl.replace(detailPlaceholder, projeto.id)}" class="globo-popup-link">🔍 Ver Projeto</a>
                </div>
            `
        });
    });

    if (projetos.length > 0) {
        viewer.zoomTo(viewer.entities);
    }

    const handler = new window.Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click) => {
        const picked = viewer.scene.pick(click.position);
        if (window.Cesium.defined(picked) && picked.id) {
            viewer.selectedEntity = picked.id;
            viewer.flyTo(picked.id, {
                duration: 1.5,
                offset: new window.Cesium.HeadingPitchRange(0, -0.5, 500)
            });
        }
    }, window.Cesium.ScreenSpaceEventType.LEFT_CLICK);
})();
