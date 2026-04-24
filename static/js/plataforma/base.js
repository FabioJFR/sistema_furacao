(() => {
    document.querySelectorAll("[data-message-close]").forEach((button) => {
        button.addEventListener("click", () => {
            const message = button.closest("[data-message]");
            if (message) {
                message.remove();
            }
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

    document.querySelectorAll("[data-history-back]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            window.history.back();
        });
    });

    document.querySelectorAll("[data-auto-submit-on-change]").forEach((input) => {
        input.addEventListener("change", () => {
            if (input.form) {
                input.form.requestSubmit();
            }
        });
    });
})();
