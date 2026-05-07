const output = document.querySelector("#output");
const tokenInput = document.querySelector("#token");

function value(id) {
    return document.querySelector(`#${id}`).value.trim();
}

function show(data) {
    output.textContent = JSON.stringify(data, null, 2);
}

async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (tokenInput.value.trim()) {
        headers.Authorization = `Bearer ${tokenInput.value.trim()}`;
    }
    const response = await fetch(path, { ...options, headers });
    const data = await response.json();
    show(data);
    if (data.ok && data.data && data.data.token) {
        tokenInput.value = data.data.token;
    }
    return data;
}

document.addEventListener("click", async (event) => {
    const action = event.target.dataset.action;
    if (!action) {
        return;
    }
    if (action === "register") {
        await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ username: value("username"), password: value("password") }),
        });
    }
    if (action === "login") {
        await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username: value("username"), password: value("password") }),
        });
    }
    if (action === "create-ai-room") {
        await api("/api/rooms", {
            method: "POST",
            body: JSON.stringify({ name: value("roomName"), mode: "ai", board_size: 3, win_length: 3 }),
        });
    }
    if (action === "leaderboard") {
        await api("/api/leaderboard");
    }
});
