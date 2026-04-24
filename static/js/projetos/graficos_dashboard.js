(() => {
    if (typeof window.Chart === "undefined") {
        return;
    }

    const labelsDia = JSON.parse(document.getElementById("labels-dia-data")?.textContent || "[]");
    const metrosDia = JSON.parse(document.getElementById("metros-dia-data")?.textContent || "[]");
    const horasDia = JSON.parse(document.getElementById("horas-dia-data")?.textContent || "[]");
    const labelsEmpregados = JSON.parse(document.getElementById("labels-empregados-data")?.textContent || "[]");
    const metrosEmpregados = JSON.parse(document.getElementById("metros-empregados-data")?.textContent || "[]");
    const labelsFuros = JSON.parse(document.getElementById("labels-furos-data")?.textContent || "[]");
    const metrosFuros = JSON.parse(document.getElementById("metros-furos-data")?.textContent || "[]");
    const labelsProjetos = JSON.parse(document.getElementById("labels-projetos-data")?.textContent || "[]");
    const metrosProjetos = JSON.parse(document.getElementById("metros-projetos-data")?.textContent || "[]");
    const labelsDespesasDia = JSON.parse(document.getElementById("labels-despesas-dia-data")?.textContent || "[]");
    const valoresDespesasDia = JSON.parse(document.getElementById("valores-despesas-dia-data")?.textContent || "[]");
    const labelsDespesasCategoria = JSON.parse(document.getElementById("labels-despesas-categoria-data")?.textContent || "[]");
    const valoresDespesasCategoria = JSON.parse(document.getElementById("valores-despesas-categoria-data")?.textContent || "[]");
    const labelsDespesasProjeto = JSON.parse(document.getElementById("labels-despesas-projeto-data")?.textContent || "[]");
    const valoresDespesasProjeto = JSON.parse(document.getElementById("valores-despesas-projeto-data")?.textContent || "[]");

    new window.Chart(document.getElementById("graficoDia"), {
        type: "line",
        data: {
            labels: labelsDia,
            datasets: [
                { label: "Metros", data: metrosDia, borderWidth: 2, tension: 0.3 },
                { label: "Horas", data: horasDia, borderWidth: 2, tension: 0.3 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoEmpregados"), {
        type: "bar",
        data: { labels: labelsEmpregados, datasets: [{ label: "Metros", data: metrosEmpregados, borderWidth: 1 }] },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoFuros"), {
        type: "bar",
        data: { labels: labelsFuros, datasets: [{ label: "Metros", data: metrosFuros, borderWidth: 1 }] },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoProjetos"), {
        type: "bar",
        data: { labels: labelsProjetos, datasets: [{ label: "Metros", data: metrosProjetos, borderWidth: 1 }] },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoDespesasDia"), {
        type: "line",
        data: {
            labels: labelsDespesasDia,
            datasets: [{
                label: "Despesas (€)",
                data: valoresDespesasDia,
                borderColor: "#dc2626",
                backgroundColor: "rgba(220, 38, 38, 0.12)",
                fill: true,
                borderWidth: 2,
                tension: 0.3
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoDespesasCategoria"), {
        type: "doughnut",
        data: {
            labels: labelsDespesasCategoria,
            datasets: [{
                label: "Despesas (€)",
                data: valoresDespesasCategoria,
                backgroundColor: ["#dc2626", "#ea580c", "#d97706", "#0891b2", "#7c3aed", "#475569"]
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    new window.Chart(document.getElementById("graficoDespesasProjeto"), {
        type: "bar",
        data: {
            labels: labelsDespesasProjeto,
            datasets: [{ label: "Despesas (€)", data: valoresDespesasProjeto, backgroundColor: "#b91c1c", borderWidth: 1 }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });

    document.querySelectorAll("[data-sortable-table]").forEach((table) => {
        const headers = table.querySelectorAll("th[data-sort-type]");
        headers.forEach((header, columnIndex) => {
            header.addEventListener("click", () => {
                const tbody = table.querySelector("tbody");
                const rows = Array.from(tbody.querySelectorAll("tr")).filter((row) => row.children.length > 1);
                const currentDirection = header.dataset.sortDirection === "asc" ? "desc" : "asc";
                headers.forEach((item) => delete item.dataset.sortDirection);
                header.dataset.sortDirection = currentDirection;

                rows.sort((rowA, rowB) => {
                    const getValue = (row) => {
                        const cell = row.children[columnIndex];
                        if (!cell) return 0;
                        const raw = (cell.textContent || "").replace(/[€%\s]/g, "").replace(",", ".");
                        const value = Number(raw);
                        return Number.isNaN(value) ? raw.toLowerCase() : value;
                    };
                    const a = getValue(rowA);
                    const b = getValue(rowB);
                    if (typeof a === "number" && typeof b === "number") {
                        return currentDirection === "asc" ? a - b : b - a;
                    }
                    return currentDirection === "asc"
                        ? String(a).localeCompare(String(b))
                        : String(b).localeCompare(String(a));
                });

                rows.forEach((row) => tbody.appendChild(row));
            });
        });
    });

    document.querySelectorAll("[data-table-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            const tableName = button.dataset.tableFilter;
            const filter = button.dataset.filter;
            const table = document.querySelector(`[data-sortable-table="${tableName}"]`);
            if (!table) return;

            const buttons = document.querySelectorAll(`[data-table-filter="${tableName}"]`);
            buttons.forEach((item) => {
                item.style.opacity = item === button ? "1" : "0.7";
            });

            table.querySelectorAll("tbody tr").forEach((row) => {
                if (row.children.length <= 1) return;
                const margemTotal = Number(row.dataset.marginTotal || 0);
                const margemPercent = Number(row.dataset.marginPercent || 0);
                let visible = true;
                if (filter === "negativos") visible = margemTotal < 0;
                if (filter === "baixos") visible = margemTotal >= 0 && margemPercent < 15;
                if (filter === "positivos") visible = margemPercent >= 15;
                row.style.display = visible ? "" : "none";
            });
        });
    });
})();
