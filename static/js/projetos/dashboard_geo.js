(() => {
    const config = document.getElementById("dashboard-geo-config");
    const canvas = document.getElementById("grafico");
    if (!config || !canvas || typeof window.Chart === "undefined") {
        return;
    }

    const medicoesJsonUrl = config.dataset.medicoesUrl || "";
    let chart;

    async function carregarDados() {
        if (!medicoesJsonUrl) {
            return;
        }
        try {
            const response = await fetch(medicoesJsonUrl);
            const data = await response.json();
            const labels = data.map((item) => item.profundidade);
            const dureza = data.map((item) => item.dureza);

            if (chart) {
                chart.data.labels = labels;
                chart.data.datasets[0].data = dureza;
                chart.update();
                return;
            }

            chart = new window.Chart(canvas, {
                type: "line",
                data: {
                    labels,
                    datasets: [{
                        label: "Dureza da Rocha",
                        data: dureza,
                        borderColor: "#2563eb",
                        backgroundColor: "rgba(37,99,235,0.1)",
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            title: { display: true, text: "Dureza" },
                            ticks: { color: "#1f2937" }
                        },
                        x: {
                            title: { display: true, text: "Profundidade (m)" },
                            ticks: { color: "#1f2937" }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: { color: "#1f2937" }
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Erro ao carregar dados:", error);
        }
    }

    carregarDados();
    window.setInterval(carregarDados, 5000);
})();
