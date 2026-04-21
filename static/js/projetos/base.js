function fecharMensagem(el) {
    const box = el.parentElement;
    if (!box) return;

    box.style.opacity = "0";
    box.style.transform = "translateY(-10px)";

    setTimeout(() => {
        box.remove();
    }, 300);
}

function toggleMenu() {
    const menu = document.getElementById("topNavMenu");
    const toggle = document.querySelector(".menu-toggle");

    if (!menu) return;

    const isActive = menu.classList.toggle("active");

    if (toggle) {
        toggle.setAttribute("aria-expanded", isActive ? "true" : "false");
    }
}

function closeAllDropdowns() {
    document.querySelectorAll(".nav-item.open").forEach((item) => {
        item.classList.remove("open");
    });

    document.querySelectorAll('.nav-item button[aria-expanded="true"]').forEach((btn) => {
        btn.setAttribute("aria-expanded", "false");
    });
}

function toggleDropdown(event, el) {
    event.preventDefault();
    event.stopPropagation();

    const item = el.closest(".nav-item");
    if (!item) return;

    const isOpen = item.classList.contains("open");

    closeAllDropdowns();

    if (!isOpen) {
        item.classList.add("open");
        el.setAttribute("aria-expanded", "true");
    }
}

document.addEventListener("click", function () {
    closeAllDropdowns();
});

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        closeAllDropdowns();

        const menu = document.getElementById("topNavMenu");
        const toggle = document.querySelector(".menu-toggle");

        if (menu && menu.classList.contains("active")) {
            menu.classList.remove("active");
        }

        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }
    }
});

document.querySelectorAll("#topNavMenu a").forEach((link) => {
    link.addEventListener("click", () => {
        const menu = document.getElementById("topNavMenu");
        const toggle = document.querySelector(".menu-toggle");

        if (menu && menu.classList.contains("active")) {
            menu.classList.remove("active");
        }

        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }

        closeAllDropdowns();
    });
});

