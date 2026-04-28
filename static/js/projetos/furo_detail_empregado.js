(() => {
  const bindTabs = ({
    tabAId,
    tabBId,
    panelAId,
    panelBId,
  }) => {
    const tabA = document.getElementById(tabAId);
    const tabB = document.getElementById(tabBId);
    const panelA = document.getElementById(panelAId);
    const panelB = document.getElementById(panelBId);

    if (!tabA || !tabB || !panelA || !panelB) return;

    const showA = () => {
      panelA.classList.remove("hidden");
      panelB.classList.add("hidden");
      tabA.classList.add("btn-primary");
      tabA.classList.remove("btn-secondary");
      tabB.classList.add("btn-secondary");
      tabB.classList.remove("btn-primary");
    };

    const showB = () => {
      panelB.classList.remove("hidden");
      panelA.classList.add("hidden");
      tabB.classList.add("btn-primary");
      tabB.classList.remove("btn-secondary");
      tabA.classList.add("btn-secondary");
      tabA.classList.remove("btn-primary");
    };

    tabA.addEventListener("click", showA);
    tabB.addEventListener("click", showB);
    showA();
  };

  bindTabs({
    tabAId: "tab-meus-levantamentos",
    tabBId: "tab-todos-levantamentos",
    panelAId: "painel-meus-levantamentos",
    panelBId: "painel-todos-levantamentos",
  });

  bindTabs({
    tabAId: "tab-minhas-devolucoes",
    tabBId: "tab-todas-devolucoes",
    panelAId: "painel-minhas-devolucoes",
    panelBId: "painel-todas-devolucoes",
  });
})();
