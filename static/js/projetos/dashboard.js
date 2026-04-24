(() => {
    if (typeof window.Cesium === "undefined" || typeof window.L === "undefined") {
        return;
    }

    const config = document.getElementById("dashboard-config");
    const projetosData = document.getElementById("projetos-data");
    const cesiumContainer = document.getElementById("cesiumContainer");
    const leafletContainer = document.getElementById("leafletContainer");
    if (!config || !projetosData || !cesiumContainer || !leafletContainer) {
        return;
    }

    const projetoDetailPlaceholder = config.dataset.detailPlaceholder || "00000000-0000-0000-0000-000000000000";
    const projetoDetailBaseUrl = config.dataset.detailBaseUrl || "";
    const projetos = JSON.parse(projetosData.textContent || "[]");

    function detailUrl(id) {
        return projetoDetailBaseUrl.replace(projetoDetailPlaceholder, String(id));
    }

    function corProjetoCesium(status) {
        if (status === "ativo") return window.Cesium.Color.GREEN;
        if (status === "pausado") return window.Cesium.Color.YELLOW;
        if (status === "concluido") return window.Cesium.Color.BLUE;
        return window.Cesium.Color.RED;
    }

    function corProjetoLeaflet(status) {
        if (status === "ativo") return "green";
        if (status === "pausado") return "orange";
        if (status === "concluido") return "blue";
        return "red";
    }

    const infoBox = document.getElementById("projetoAtualInfo");
    const prevBtn = document.getElementById("prevProjetoBtn");
    const nextBtn = document.getElementById("nextProjetoBtn");
    const abrirBtn = document.getElementById("abrirProjetoBtn");
    const alternarBtn = document.getElementById("alternarMapaBtn");

    let modoMapa = "globo";
    let projetoIndex = 0;
    const projetosComPino = [];

    window.Cesium.Ion.defaultAccessToken = "COLOCA_AQUI_O_TEU_TOKEN";

    const viewer = new window.Cesium.Viewer("cesiumContainer", {
        timeline: false,
        animation: false,
        sceneModePicker: true,
        infoBox: false,
        selectionIndicator: true,
        navigationHelpButton: false,
        baseLayerPicker: false,
        homeButton: true,
        geocoder: false,
        shouldAnimate: false,
        terrainProvider: new window.Cesium.EllipsoidTerrainProvider(),
    });

    viewer.scene.globe.enableLighting = false;
    viewer.scene.globe.baseColor = window.Cesium.Color.WHITE;
    viewer.scene.skyBox.show = true;
    viewer.scene.backgroundColor = window.Cesium.Color.BLACK;
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 500000;
    viewer.imageryLayers.removeAll();
    viewer.imageryLayers.addImageryProvider(
        new window.Cesium.UrlTemplateImageryProvider({
            url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            credit: "© OpenStreetMap contributors"
        })
    );

    const map = window.L.map("leafletContainer").setView([39.5, -8.0], 6);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    projetos.forEach((projeto) => {
        const lat = projeto.localizacao_lat;
        const lon = projeto.localizacao_lon;
        if (lat === null || lon === null || Number.isNaN(lat) || Number.isNaN(lon)) {
            return;
        }

        const entity = viewer.entities.add({
            position: window.Cesium.Cartesian3.fromDegrees(lon, lat, 0),
            point: {
                pixelSize: 14,
                color: corProjetoCesium(projeto.status),
                outlineColor: window.Cesium.Color.WHITE,
                outlineWidth: 2
            },
            label: {
                text: projeto.nome || "Projeto",
                font: "14px sans-serif",
                style: window.Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: window.Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new window.Cesium.Cartesian2(0, -18),
                scale: 0.8
            },
            name: projeto.nome,
            projetoId: projeto.id
        });

        const circleMarker = window.L.circleMarker([lat, lon], {
            radius: 8,
            color: "#ffffff",
            weight: 2,
            fillColor: corProjetoLeaflet(projeto.status),
            fillOpacity: 0.95
        }).addTo(map);

        circleMarker.bindPopup(`
            <strong>${projeto.nome}</strong><br>
            ${projeto.cidade || "-"}, ${projeto.pais || "-"}<br>
            Status: ${projeto.status || "-"}
        `);

        circleMarker.on("click", () => selecionarProjetoPorId(projeto.id, true));
        circleMarker.on("dblclick", () => {
            window.location.href = detailUrl(projeto.id);
        });

        projetosComPino.push({
            ...projeto,
            entity,
            leafletMarker: circleMarker
        });
    });

    function atualizarPainelProjeto() {
        if (!infoBox || !prevBtn || !nextBtn || !abrirBtn) {
            return;
        }
        if (!projetosComPino.length) {
            infoBox.innerHTML = "Sem projetos com coordenadas.";
            abrirBtn.disabled = true;
            prevBtn.disabled = true;
            nextBtn.disabled = true;
            abrirBtn.style.opacity = "0.5";
            prevBtn.style.opacity = "0.5";
            nextBtn.style.opacity = "0.5";
            return;
        }

        const projeto = projetosComPino[projetoIndex];
        infoBox.innerHTML = `
            <strong>${projeto.nome}</strong><br>
            Cidade: ${projeto.cidade || "-"}<br>
            País: ${projeto.pais || "-"}<br>
            Status: ${projeto.status || "-"}
        `;
        abrirBtn.disabled = false;
        prevBtn.disabled = false;
        nextBtn.disabled = false;
        abrirBtn.style.opacity = "1";
        prevBtn.style.opacity = "1";
        nextBtn.style.opacity = "1";
    }

    function focarProjetoAtual() {
        if (!projetosComPino.length) {
            return;
        }
        const projeto = projetosComPino[projetoIndex];
        if (modoMapa === "globo") {
            viewer.flyTo(projeto.entity, {
                offset: new window.Cesium.HeadingPitchRange(0, -1.35, 1800000),
                duration: 3.2
            });
            viewer.selectedEntity = projeto.entity;
        } else {
            map.flyTo([projeto.localizacao_lat, projeto.localizacao_lon], 9);
            projeto.leafletMarker.openPopup();
        }
        atualizarPainelProjeto();
    }

    function selecionarProjetoPorId(id, focar = false) {
        const idx = projetosComPino.findIndex((projeto) => projeto.id === id);
        if (idx < 0) {
            return;
        }
        projetoIndex = idx;
        atualizarPainelProjeto();
        if (focar) {
            focarProjetoAtual();
        }
    }

    prevBtn?.addEventListener("click", () => {
        if (!projetosComPino.length) return;
        projetoIndex = (projetoIndex - 1 + projetosComPino.length) % projetosComPino.length;
        focarProjetoAtual();
    });

    nextBtn?.addEventListener("click", () => {
        if (!projetosComPino.length) return;
        projetoIndex = (projetoIndex + 1) % projetosComPino.length;
        focarProjetoAtual();
    });

    abrirBtn?.addEventListener("click", () => {
        if (!projetosComPino.length) return;
        window.location.href = detailUrl(projetosComPino[projetoIndex].id);
    });

    alternarBtn?.addEventListener("click", () => {
        if (modoMapa === "globo") {
            modoMapa = "plano";
            cesiumContainer.style.display = "none";
            leafletContainer.style.display = "block";
            alternarBtn.innerText = "Globo";
            window.setTimeout(() => map.invalidateSize(), 200);
        } else {
            modoMapa = "globo";
            leafletContainer.style.display = "none";
            cesiumContainer.style.display = "block";
            alternarBtn.innerText = "Mapa Plano";
        }
        focarProjetoAtual();
    });

    viewer.selectedEntityChanged.addEventListener((entity) => {
        if (!entity?.projetoId) {
            return;
        }
        selecionarProjetoPorId(entity.projetoId, false);
    });

    viewer.screenSpaceEventHandler.setInputAction((click) => {
        const pickedObject = viewer.scene.pick(click.position);
        if (window.Cesium.defined(pickedObject) && pickedObject.id?.projetoId) {
            window.location.href = detailUrl(pickedObject.id.projetoId);
        }
    }, window.Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

    if (projetosComPino.length > 0) {
        atualizarPainelProjeto();
        viewer.camera.setView({
            destination: window.Cesium.Cartesian3.fromDegrees(-8.0, 39.5, 10000000),
            orientation: {
                heading: 0.0,
                pitch: -Math.PI / 2.2,
                roll: 0.0
            }
        });
        window.setTimeout(() => {
            focarProjetoAtual();
        }, 1800);
    } else {
        atualizarPainelProjeto();
        viewer.camera.setView({
            destination: window.Cesium.Cartesian3.fromDegrees(0, 20, 12000000)
        });
    }
})();
