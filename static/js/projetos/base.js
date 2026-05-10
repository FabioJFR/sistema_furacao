(() => {
    const THEME_STORAGE_KEY = "sf_theme_palette";
    const AJUDA_CONTEXTUAL_STORAGE_PREFIX = "sf_ajuda_contextual_dismissed:";
    const AVAILABLE_THEMES = ["industrial-blue", "earth-drill", "graphite-tech", "sandstone"];

    function applyTheme(themeName) {
        const safeTheme = AVAILABLE_THEMES.includes(themeName) ? themeName : "industrial-blue";
        document.documentElement.setAttribute("data-theme", safeTheme);
        return safeTheme;
    }

    function setupThemePicker() {
        const pickers = [...document.querySelectorAll("[data-theme-picker]")];
        const pickerTheme = pickers[0]?.value;
        const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
        const initialTheme = AVAILABLE_THEMES.includes(storedTheme)
            ? storedTheme
            : (AVAILABLE_THEMES.includes(pickerTheme) ? pickerTheme : "industrial-blue");

        const activeTheme = applyTheme(initialTheme);
        window.localStorage.setItem(THEME_STORAGE_KEY, activeTheme);

        pickers.forEach((picker) => {
            picker.value = activeTheme;
            const temaInput = picker.form?.querySelector('input[name$="-tema"], input[name="tema"]');
            if (temaInput) {
                temaInput.value = activeTheme === "graphite-tech" ? "escuro" : "claro";
            }
            picker.addEventListener("change", () => {
                const selectedTheme = applyTheme(picker.value);
                window.localStorage.setItem(THEME_STORAGE_KEY, selectedTheme);
                const targetTemaInput = picker.form?.querySelector('input[name$="-tema"], input[name="tema"]');
                if (targetTemaInput) {
                    targetTemaInput.value = selectedTheme === "graphite-tech" ? "escuro" : "claro";
                }
                pickers.forEach((otherPicker) => {
                    if (otherPicker !== picker) {
                        otherPicker.value = selectedTheme;
                    }
                });
                updatePalettePresetState(selectedTheme);
            });
        });

        updatePalettePresetState(activeTheme);
    }

    function updatePalettePresetState(themeName) {
        document.querySelectorAll("[data-theme-preset]").forEach((button) => {
            const isActive = button.getAttribute("data-theme-preset") === themeName;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    }

    function setupThemePresets() {
        const presetButtons = [...document.querySelectorAll("[data-theme-preset]")];
        if (!presetButtons.length) {
            return;
        }
        presetButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const targetTheme = button.getAttribute("data-theme-preset");
                const pickers = [...document.querySelectorAll("[data-theme-picker]")];
                pickers.forEach((picker) => {
                    picker.value = targetTheme;
                    picker.dispatchEvent(new Event("change", { bubbles: true }));
                });
            });
        });
    }

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

    function setupAjudaContextual() {
        const box = document.querySelector("[data-ajuda-contextual]");
        if (!box) {
            return;
        }

        const key = box.getAttribute("data-ajuda-contextual-key") || window.location.pathname;
        const storageKey = `${AJUDA_CONTEXTUAL_STORAGE_PREFIX}${key}`;
        const closeButton = box.querySelector("[data-ajuda-contextual-close]");

        if (window.sessionStorage.getItem(storageKey) === "1") {
            box.remove();
            return;
        }

        if (!closeButton) {
            return;
        }

        closeButton.addEventListener("click", () => {
            closeButton.blur();
            window.sessionStorage.setItem(storageKey, "1");
            box.style.opacity = "0";
            box.style.transform = "translateY(-10px)";
            window.setTimeout(() => {
                box.remove();
            }, 250);
        });
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

    function hasUsefulBackHistory() {
        if (!document.referrer) {
            return false;
        }
        try {
            const referrerUrl = new URL(document.referrer);
            const currentUrl = new URL(window.location.href);
            if (referrerUrl.origin !== currentUrl.origin) {
                return false;
            }
            return referrerUrl.href !== currentUrl.href;
        } catch (error) {
            return false;
        }
    }

    function isBackControl(element) {
        if (!element) {
            return false;
        }
        if (element.hasAttribute("data-history-back")) {
            return true;
        }
        if (element.closest(".dropdown")) {
            return false;
        }
        const text = (element.textContent || "").toLowerCase().trim();
        return /\bvoltar\b/.test(text);
    }

    function navigateBackOrFallback(element) {
        const fallbackHref = element.getAttribute("href") || element.getAttribute("data-history-fallback") || null;
        if (hasUsefulBackHistory() && window.history.length > 1) {
            window.history.back();
            return;
        }
        if (fallbackHref && fallbackHref !== "#" && !fallbackHref.startsWith("javascript:")) {
            window.location.assign(fallbackHref);
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

        const closeAjudaContextualButton = event.target.closest("[data-ajuda-contextual-close]");
        if (closeAjudaContextualButton) {
            event.preventDefault();
            const box = closeAjudaContextualButton.closest("[data-ajuda-contextual]");
            if (box) {
                const key = box.getAttribute("data-ajuda-contextual-key") || window.location.pathname;
                const storageKey = `${AJUDA_CONTEXTUAL_STORAGE_PREFIX}${key}`;
                window.sessionStorage.setItem(storageKey, "1");
                box.style.opacity = "0";
                box.style.transform = "translateY(-10px)";
                window.setTimeout(() => {
                    box.remove();
                }, 250);
            }
            return;
        }

        const historyBackButton = event.target.closest("[data-history-back]");
        if (historyBackButton) {
            event.preventDefault();
            navigateBackOrFallback(historyBackButton);
            return;
        }

        const genericBackControl = event.target.closest("a, button");
        if (genericBackControl && isBackControl(genericBackControl)) {
            event.preventDefault();
            navigateBackOrFallback(genericBackControl);
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

    setupThemePicker();
    setupThemePresets();
    setupAjudaContextual();
})();
