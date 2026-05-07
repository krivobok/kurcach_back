(function () {
    function submitMove(form) {
        const x = window.scrollX;
        const y = window.scrollY;
        const button = form.querySelector("button[type='submit']");
        if (button) {
            button.disabled = true;
        }

        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
            headers: { "X-Requested-With": "fetch" },
        })
            .then((response) => response.text())
            .then((html) => {
                const documentCopy = new DOMParser().parseFromString(html, "text/html");
                const freshRoom = documentCopy.querySelector("#room-content");
                const currentRoom = document.querySelector("#room-content");
                const currentMessages = document.querySelector(".flash-list");

                if (!freshRoom || !currentRoom) {
                    window.location.reload();
                    return;
                }

                currentRoom.innerHTML = freshRoom.innerHTML;
                if (currentMessages) {
                    currentMessages.remove();
                }
                window.scrollTo(x, y);
                requestAnimationFrame(function () { window.scrollTo(x, y); });
            })
            .catch(() => {
                window.location.href = form.action;
            });
    }

    document.addEventListener("submit", function (event) {
        const form = event.target.closest("form[data-async-move]");
        if (!form) {
            return;
        }
        event.preventDefault();
        submitMove(form);
    });
})();