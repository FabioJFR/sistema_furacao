(() => {
    if (typeof window.Chart === "undefined") {
        return;
    }

    const labelsNode = document.getElementById("grafico-labels");
    const metrosNode = document.getElementById("grafico-metros");
    const horasNode = document.getElementById("grafico-horas");
    const produtividadeNode = document.getElementById("grafico-produtividade");
    if (!labelsNode || !metrosNode || !horasNode || !produtividadeNode) {
        return;
    }

    const labels = JSON.parse(labelsNode.textContent || "[]");
    const dadosMetros = JSON.parse(metrosNode.textContent || "[]");
    const dadosHoras = JSON.parse(horasNode.textContent || "[]");
    const dadosProdutividade = JSON.parse(produtividadeNode.textContent || "[]");

    new window.Chart(document.getElementById("graficoMetros"), {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Metros",
                data: dadosMetros,
                borderWidth: 2,
                tension: 0.3
            }]
        },
        options: { responsive: true }
    });

    new window.Chart(document.getElementById("graficoHoras"), {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Horas",
                data: dadosHoras,
                borderWidth: 2,
                tension: 0.3
            }]
        },
        options: { responsive: true }
    });

    new window.Chart(document.getElementById("graficoProdutividade"), {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "m/h",
                data: dadosProdutividade,
                borderWidth: 1
            }]
        },
        options: { responsive: true }
    });
})();
