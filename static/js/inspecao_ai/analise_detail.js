(() => {
    const zoom = document.getElementById("image-zoom");
    const contrast = document.getElementById("image-contrast");
    const brightness = document.getElementById("image-brightness");
    const images = [
        document.getElementById("analise-imagem-original"),
        document.getElementById("analise-imagem-processada"),
    ].filter(Boolean);

    function applyViewAdjustments() {
        const scale = zoom ? Number(zoom.value || 1) : 1;
        const contrastValue = contrast ? Number(contrast.value || 1) : 1;
        const brightnessValue = brightness ? Number(brightness.value || 1) : 1;
        images.forEach((image) => {
            image.style.transform = `scale(${scale})`;
            image.style.filter = `contrast(${contrastValue}) brightness(${brightnessValue})`;
        });
    }

    function applyPriorityOverlays() {
        document.querySelectorAll(".ai-priority-overlay").forEach((overlay) => {
            const left = Number(overlay.dataset.left || 0);
            const top = Number(overlay.dataset.top || 0);
            const rightEdge = Number(overlay.dataset.rightEdge || 100);
            const bottomEdge = Number(overlay.dataset.bottomEdge || 100);
            overlay.style.left = `${left}%`;
            overlay.style.top = `${top}%`;
            overlay.style.right = `calc(100% - ${rightEdge}%)`;
            overlay.style.bottom = `calc(100% - ${bottomEdge}%)`;
        });
    }

    [zoom, contrast, brightness].filter(Boolean).forEach((input) => {
        input.addEventListener("input", applyViewAdjustments);
    });
    applyPriorityOverlays();
    applyViewAdjustments();
})();
