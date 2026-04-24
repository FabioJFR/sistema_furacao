(() => {
    function closeMessage(button) {
        const box = button?.closest(".msg-box");
        if (!box) {
            return;
        }
        box.style.opacity = "0";
        box.style.transform = "translateY(-10px)";
        window.setTimeout(() => {
            box.remove();
        }, 300);
    }

    function closeAllDropdowns() {
        document.querySelectorAll(".nav-item.open").forEach((item) => {
            item.classList.remove("open");
        });
        document.querySelectorAll('.nav-item button[aria-expanded="true"]').forEach((btn) => {
            btn.setAttribute("aria-expanded", "false");
        });
    }

    function closeMobileMenu() {
        const menu = document.getElementById("topNavMenu");
        const toggle = document.querySelector("[data-menu-toggle]");
        if (menu?.classList.contains("active")) {
            menu.classList.remove("active");
        }
        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }
    }

    function toggleMenu() {
        const menu = document.getElementById("topNavMenu");
        const toggle = document.querySelector("[data-menu-toggle]");
        if (!menu) {
            return;
        }
        const isActive = menu.classList.toggle("active");
        if (toggle) {
            toggle.setAttribute("aria-expanded", isActive ? "true" : "false");
        }
    }

    function toggleDropdown(button) {
        const item = button.closest(".nav-item");
        if (!item) {
            return;
        }
        const isOpen = item.classList.contains("open");
        closeAllDropdowns();
        if (!isOpen) {
            item.classList.add("open");
            button.setAttribute("aria-expanded", "true");
        }
    }

    document.addEventListener("click", (event) => {
        const menuToggle = event.target.closest("[data-menu-toggle]");
        if (menuToggle) {
            event.preventDefault();
            event.stopPropagation();
            toggleMenu();
            return;
        }

        const dropdownToggle = event.target.closest("[data-dropdown-toggle]");
        if (dropdownToggle) {
            event.preventDefault();
            event.stopPropagation();
            toggleDropdown(dropdownToggle);
            return;
        }

        const closeMessageButton = event.target.closest("[data-close-message]");
        if (closeMessageButton) {
            event.preventDefault();
            closeMessage(closeMessageButton);
            return;
        }

        const historyBackButton = event.target.closest("[data-history-back]");
        if (historyBackButton) {
            event.preventDefault();
            window.history.back();
            return;
        }

        closeAllDropdowns();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }
        closeAllDropdowns();
        closeMobileMenu();
    });

    document.querySelectorAll("#topNavMenu a").forEach((link) => {
        link.addEventListener("click", () => {
            closeMobileMenu();
            closeAllDropdowns();
        });
    });

    document.querySelectorAll("[data-confirm-submit]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.getAttribute("data-confirm-submit") || "Confirmar ação?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("[data-auto-submit-on-change]").forEach((input) => {
        input.addEventListener("change", () => {
            const form = input.form;
            if (form) {
                form.requestSubmit();
            }
        });
    });
})();
