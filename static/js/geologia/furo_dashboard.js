document.addEventListener("DOMContentLoaded", function () {
    const cards = document.querySelectorAll("[data-geologia-card]");
    if (!cards.length) {
        return;
    }

    cards.forEach(function (card, index) {
        card.style.opacity = "0";
        card.style.transform = "translateY(10px)";

        window.setTimeout(function () {
            card.style.transition = "opacity 240ms ease, transform 240ms ease";
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        }, 60 * index);
    });
});

