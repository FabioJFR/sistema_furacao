(function () {
    const messagesContainer = document.getElementById("chat-messages-container");
    const composerForm = document.getElementById("chat-composer-form");
    const input = document.getElementById("id_pergunta");

    if (!messagesContainer) {
        return;
    }

    const scrollToLatest = (behavior = "auto") => {
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior,
        });
    };

    if ("scrollRestoration" in window.history) {
        window.history.scrollRestoration = "manual";
    }

    window.addEventListener("load", () => {
        scrollToLatest("auto");
        if (input) {
            input.focus();
        }
    });

    if (composerForm) {
        composerForm.addEventListener("submit", () => {
            scrollToLatest("auto");
        });
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-chat-prompt]");
        if (!button || !composerForm || !input) {
            return;
        }
        event.preventDefault();
        const prompt = (button.getAttribute("data-chat-prompt") || "").trim();
        if (!prompt) {
            return;
        }
        input.value = prompt;
        scrollToLatest("auto");
        if (typeof composerForm.requestSubmit === "function") {
            composerForm.requestSubmit();
        } else {
            composerForm.submit();
        }
    });
})();
