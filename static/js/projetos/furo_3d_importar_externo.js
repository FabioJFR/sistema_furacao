(() => {
    if (typeof window.Plotly === "undefined") {
        return;
    }
    const dataNode = document.getElementById("imported-trace-data");
    const plotContainer = document.getElementById("plot-3d");
    if (!dataNode || !plotContainer) {
        return;
    }

    const config = document.getElementById("furo-3d-import-config");
    const filename = config?.dataset.pngFilename || "trajetoria-importada-3d";
    const importedTrace = JSON.parse(dataNode.textContent || "{}");
    const exportPngBtn = document.getElementById("exportPngBtn");

    if (!importedTrace.x || !importedTrace.x.length) {
        return;
    }

    const trace = {
        x: importedTrace.x,
        y: importedTrace.y,
        z: importedTrace.z,
        mode: "lines+markers",
        type: "scatter3d",
        name: importedTrace.name || "Trajetória importada",
        line: { width: 7, color: "#7c3aed" },
        marker: { size: 4, color: "#a855f7" },
        hovertemplate: "X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra></extra>",
    };

    window.Plotly.newPlot(plotContainer, [trace], {
        margin: { l: 0, r: 0, b: 0, t: 10 },
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        scene: {
            bgcolor: "#f8fafc",
            xaxis: { title: "X", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            yaxis: { title: "Y", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            zaxis: { title: "Z", backgroundcolor: "#f8fafc", gridcolor: "#d1d5db", zerolinecolor: "#9ca3af" },
            camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } }
        }
    }, {
        responsive: true,
        displaylogo: false,
    }).then((plot) => {
        exportPngBtn?.addEventListener("click", () => {
            window.Plotly.downloadImage(plot, {
                format: "png",
                filename,
                width: 1600,
                height: 900,
                scale: 2
            });
        });
    });
})();
