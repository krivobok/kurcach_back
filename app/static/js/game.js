const state = {
    token: localStorage.getItem("tttToken") || "",
    user: null,
    room: null,
    game: null,
    board: null,
};

const els = {
    authPanel: document.querySelector("#authPanel"),
    profilePanel: document.querySelector("#profilePanel"),
    profileName: document.querySelector("#profileName"),
    profileRating: document.querySelector("#profileRating"),
    profileRole: document.querySelector("#profileRole"),
    adminPanelLink: document.querySelector("#adminPanelLink"),
    username: document.querySelector("#username"),
    password: document.querySelector("#password"),
    accountType: document.querySelector("#accountType"),
    adminCode: document.querySelector("#adminCode"),
    adminCodeLabel: document.querySelector("#adminCodeLabel"),
    board: document.querySelector("#board"),
    message: document.querySelector("#message"),
    gameStatus: document.querySelector("#gameStatus"),
    roomName: document.querySelector("#roomName"),
    turnLabel: document.querySelector("#turnLabel"),
    symbolLabel: document.querySelector("#symbolLabel"),
    roomsList: document.querySelector("#roomsList"),
    leaderboard: document.querySelector("#leaderboard"),
    startAiBtn: document.querySelector("#startAiBtn"),
    createRoomBtn: document.querySelector("#createRoomBtn"),
    refreshBtn: document.querySelector("#refreshBtn"),
    roomsRefreshBtn: document.querySelector("#roomsRefreshBtn"),
    hintBtn: document.querySelector("#hintBtn"),
    surrenderBtn: document.querySelector("#surrenderBtn"),
    rematchBtn: document.querySelector("#rematchBtn"),
    loginBtn: document.querySelector("#loginBtn"),
    registerBtn: document.querySelector("#registerBtn"),
    logoutBtn: document.querySelector("#logoutBtn"),
};

const statusText = {
    waiting: "ожидает игроков",
    playing: "идёт игра",
    finished: "завершена",
};

const modeText = {
    public: "для двух игроков",
    private: "закрытая",
    ai: "с компьютером",
    matchmaking: "подбор соперника",
};

const errorText = {
    "Authentication required": "Сначала войдите в аккаунт.",
    "Invalid username or password": "Неверный логин или пароль.",
    "Invalid admin registration code": "Неверный код администратора.",
    "Account is banned by administrator": "Аккаунт заблокирован администратором.",
    "Room not found": "Комната не найдена.",
    "Room is closed": "Комната закрыта администратором.",
    "Room is not available for joining": "В эту комнату уже нельзя войти.",
    "Room is full": "Комната заполнена.",
    "Room is not active": "Комната не активна.",
    "Game is not active": "Игра уже завершена.",
    "Game not found": "Игра не найдена.",
    "Game is not current for this room": "Эта игра уже не является текущей для комнаты.",
    "Ready state can be changed only in waiting rooms": "Готовность можно менять только до начала игры.",
    "Rematch is available only after a finished game": "Реванш доступен только после завершённой партии.",
    "Current game is not finished yet": "Текущая партия ещё не завершена.",
    "Only room players can write to room chat": "Писать в чат могут только игроки комнаты.",
    "It is not this symbol's turn": "Сейчас ход другого игрока.",
    "Cell is already occupied": "Эта клетка уже занята.",
    "Move is outside the board": "Ход выходит за пределы поля.",
    "User does not play this game": "Этот аккаунт не участвует в игре.",
};

function translateError(message) {
    return errorText[message] || message || "Ошибка запроса.";
}

function setMessage(text, kind = "") {
    els.message.textContent = text || "";
    els.message.className = `message ${kind}`.trim();
}

function userSymbol() {
    if (!state.room || !state.user) {
        return null;
    }
    const player = (state.room.players || []).find((item) => item.user_id === state.user.id);
    return player ? player.symbol : null;
}

function authHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }
    return headers;
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: { ...authHeaders(), ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!data.ok) {
        throw new Error(translateError(data.error && data.error.message));
    }
    return data.data;
}

function requireLogin() {
    if (!state.user || !state.token) {
        setMessage("Сначала войдите или зарегистрируйтесь.", "error");
        return false;
    }
    return true;
}

function saveSession(data) {
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("tttToken", data.token);
    renderAuth();
}

async function register() {
    try {
        const data = await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({
                username: els.username.value.trim(),
                password: els.password.value,
                account_type: els.accountType.value,
                admin_code: els.accountType.value === "admin" ? els.adminCode.value : undefined,
            }),
        });
        saveSession(data);
        setMessage("Регистрация готова. Можно начинать игру.", "success");
        await refreshAll();
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function login() {
    try {
        const data = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                username: els.username.value.trim(),
                password: els.password.value,
            }),
        });
        saveSession(data);
        setMessage("Вы вошли в профиль.", "success");
        await refreshAll();
    } catch (error) {
        setMessage(error.message, "error");
    }
}

function logout() {
    state.token = "";
    state.user = null;
    state.room = null;
    state.game = null;
    state.board = null;
    localStorage.removeItem("tttToken");
    renderAuth();
    renderGame();
    setMessage("Вы вышли из профиля.");
}

async function restoreSession() {
    if (!state.token) {
        renderAuth();
        return;
    }
    try {
        state.user = await api("/api/auth/me");
    } catch (error) {
        localStorage.removeItem("tttToken");
        state.token = "";
    }
    renderAuth();
}

function renderAuth() {
    if (state.user) {
        els.authPanel.classList.add("hidden");
        els.profilePanel.classList.remove("hidden");
        els.profileName.textContent = state.user.display_name || state.user.username;
        els.profileRating.textContent = `Рейтинг: ${state.user.rating}`;
        els.profileRole.textContent = state.user.is_admin ? "Роль: администратор" : "Роль: клиент";
        els.adminPanelLink.classList.toggle("hidden", !state.user.is_admin);
    } else {
        els.authPanel.classList.remove("hidden");
        els.profilePanel.classList.add("hidden");
    }
}

async function startAiGame() {
    if (!requireLogin()) {
        return;
    }
    try {
        const name = `Игра ${state.user.display_name || state.user.username}`;
        const room = await api("/api/rooms", {
            method: "POST",
            body: JSON.stringify({ name, mode: "ai", board_size: 3, win_length: 3, symbol: "X" }),
        });
        setCurrentRoom(room);
        setMessage("Игра с компьютером началась.", "success");
        await refreshRooms();
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function createPublicRoom() {
    if (!requireLogin()) {
        return;
    }
    try {
        const name = `Комната ${state.user.display_name || state.user.username}`;
        const room = await api("/api/rooms", {
            method: "POST",
            body: JSON.stringify({ name, mode: "public", board_size: 3, win_length: 3, symbol: "X" }),
        });
        setCurrentRoom(room);
        setMessage("Комната создана. Второй игрок может присоединиться из списка комнат.", "success");
        await refreshRooms();
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function joinRoom(roomId) {
    if (!requireLogin()) {
        return;
    }
    try {
        const room = await api(`/api/rooms/${roomId}/join`, {
            method: "POST",
            body: JSON.stringify({ ready: true }),
        });
        setCurrentRoom(room);
        setMessage("Вы присоединились к комнате.", "success");
        await refreshRooms();
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function openRoom(roomId) {
    try {
        const room = await api(`/api/rooms/${roomId}`);
        setCurrentRoom(room);
        setMessage("Комната открыта.");
    } catch (error) {
        setMessage(error.message, "error");
    }
}

function setCurrentRoom(room) {
    state.room = room;
    state.game = room.game || null;
    state.board = state.game && state.game.board ? state.game.board : null;
    renderGame();
}

async function makeMove(row, col) {
    if (!requireLogin() || !state.game) {
        return;
    }
    if (state.game.status !== "playing") {
        setMessage("Эта партия уже завершена.");
        return;
    }
    const symbol = userSymbol();
    if (symbol && state.game.current_turn !== symbol) {
        setMessage("Сейчас ход соперника.");
        return;
    }
    try {
        const data = await api(`/api/games/${state.game.id}/moves`, {
            method: "POST",
            body: JSON.stringify({ row, col }),
        });
        state.game = data.game;
        state.board = data.board;
        renderGame();
        if (state.game.status === "finished") {
            await refreshLeaderboard();
            setMessage(resultMessage(state.game), "success");
        } else {
            setMessage("Ход принят.", "success");
        }
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function askHint() {
    if (!requireLogin() || !state.game) {
        return;
    }
    try {
        const data = await api(`/api/games/${state.game.id}/hint`);
        if (data.best) {
            setMessage(`Лучший ход: строка ${data.best.row + 1}, столбец ${data.best.col + 1}.`);
        }
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function surrender() {
    if (!requireLogin() || !state.game) {
        return;
    }
    try {
        const game = await api(`/api/games/${state.game.id}/surrender`, { method: "POST" });
        state.game = game;
        state.board = game.board || state.board;
        renderGame();
        await refreshLeaderboard();
        setMessage("Партия завершена.", "success");
    } catch (error) {
        setMessage(error.message, "error");
    }
}

async function rematch() {
    if (!requireLogin() || !state.room) {
        return;
    }
    try {
        const room = await api(`/api/rooms/${state.room.id}/rematch`, { method: "POST" });
        setCurrentRoom(room);
        setMessage("Новая партия началась.", "success");
    } catch (error) {
        setMessage(error.message, "error");
    }
}

function renderGame() {
    const size = state.game ? state.game.board_size : 3;
    const board = state.board || Array.from({ length: size }, () => Array(size).fill(""));
    const ownSymbol = userSymbol();
    els.board.style.setProperty("--board-size", size);
    els.board.innerHTML = "";

    for (let row = 0; row < size; row += 1) {
        for (let col = 0; col < size; col += 1) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "board-cell";
            cell.textContent = board[row][col] || "";
            cell.disabled = !state.game || state.game.status !== "playing" || Boolean(board[row][col]);
            if (ownSymbol && state.game && state.game.current_turn !== ownSymbol) {
                cell.disabled = true;
            }
            if (isWinningCell(row, col)) {
                cell.classList.add("win");
            }
            cell.addEventListener("click", () => makeMove(row, col));
            els.board.appendChild(cell);
        }
    }

    els.roomName.textContent = state.room ? state.room.name : "Комната не выбрана";
    els.turnLabel.textContent = state.game ? `Ход: ${state.game.current_turn}` : "Ход: -";
    els.symbolLabel.textContent = ownSymbol ? `Ваш знак: ${ownSymbol}` : "Ваш знак: -";
    els.hintBtn.disabled = !state.game || !ownSymbol || state.game.current_turn !== ownSymbol || state.game.status !== "playing";
    els.surrenderBtn.disabled = !state.game || state.game.status !== "playing";
    els.rematchBtn.disabled = !state.room || !state.game || state.game.status !== "finished";

    if (!state.game && state.room) {
        els.gameStatus.textContent = "Ожидаем второго игрока.";
    } else if (!state.game) {
        els.gameStatus.textContent = "Выберите режим игры или присоединитесь к комнате.";
    } else if (state.game.status === "finished") {
        els.gameStatus.textContent = resultMessage(state.game);
    } else if (ownSymbol && state.game.current_turn === ownSymbol) {
        els.gameStatus.textContent = "Ваш ход.";
    } else if (ownSymbol) {
        els.gameStatus.textContent = "Ход соперника.";
    } else {
        els.gameStatus.textContent = "Игра открыта для просмотра.";
    }
}

function isWinningCell(row, col) {
    if (!state.game || !Array.isArray(state.game.winning_line)) {
        return false;
    }
    return state.game.winning_line.some((cell) => cell[0] === row && cell[1] === col);
}

function resultMessage(game) {
    if (game.draw) {
        return "Ничья.";
    }
    if (game.winner_symbol) {
        return `Победил ${game.winner_symbol}.`;
    }
    return "Партия завершена.";
}

async function refreshRooms() {
    try {
        const rooms = await api("/api/rooms?limit=20");
        renderRooms(rooms);
    } catch (error) {
        setMessage(error.message, "error");
    }
}

function renderRooms(rooms) {
    els.roomsList.innerHTML = "";
    if (!rooms.length) {
        const empty = document.createElement("li");
        empty.className = "muted";
        empty.textContent = "Комнат пока нет.";
        els.roomsList.appendChild(empty);
        return;
    }

    rooms.forEach((room) => {
        const item = document.createElement("li");
        item.className = "room-item";

        const header = document.createElement("header");
        const title = document.createElement("strong");
        title.textContent = room.name;
        const status = document.createElement("span");
        status.className = "muted";
        status.textContent = statusText[room.status] || room.status;
        header.append(title, status);

        const meta = document.createElement("span");
        meta.className = "muted";
        meta.textContent = `${modeText[room.mode] || room.mode} · ${room.board_size}x${room.board_size}`;

        const actions = document.createElement("div");
        actions.className = "room-actions";
        const open = document.createElement("button");
        open.type = "button";
        open.className = "small ghost";
        open.textContent = "Открыть";
        open.addEventListener("click", () => openRoom(room.id));
        actions.appendChild(open);

        const alreadyInside = state.user && (room.players || []).some((player) => player.user_id === state.user.id);
        const canJoin = room.status === "waiting" && room.mode !== "ai" && !alreadyInside;
        if (canJoin) {
            const join = document.createElement("button");
            join.type = "button";
            join.className = "small";
            join.textContent = "Играть";
            join.addEventListener("click", () => joinRoom(room.id));
            actions.appendChild(join);
        }

        item.append(header, meta, actions);
        els.roomsList.appendChild(item);
    });
}

async function refreshLeaderboard() {
    try {
        const rows = await api("/api/leaderboard?limit=10");
        renderLeaderboard(rows);
    } catch (error) {
        setMessage(error.message, "error");
    }
}

function renderLeaderboard(rows) {
    els.leaderboard.innerHTML = "";
    if (!rows.length) {
        const empty = document.createElement("li");
        empty.textContent = "Пока нет игроков.";
        els.leaderboard.appendChild(empty);
        return;
    }
    rows.forEach((row, index) => {
        const item = document.createElement("li");
        const name = document.createElement("span");
        name.textContent = `${index + 1}. ${row.display_name}`;
        const rating = document.createElement("strong");
        rating.textContent = row.rating;
        item.append(name, rating);
        els.leaderboard.appendChild(item);
    });
}

async function refreshCurrentRoom() {
    if (!state.room) {
        return;
    }
    await openRoom(state.room.id);
}

async function refreshAll() {
    await Promise.all([refreshRooms(), refreshLeaderboard(), refreshCurrentRoom()]);
}

els.loginBtn.addEventListener("click", login);
els.registerBtn.addEventListener("click", register);
els.logoutBtn.addEventListener("click", logout);
els.accountType.addEventListener("change", () => {
    els.adminCodeLabel.classList.toggle("hidden", els.accountType.value !== "admin");
});
els.startAiBtn.addEventListener("click", startAiGame);
els.createRoomBtn.addEventListener("click", createPublicRoom);
els.refreshBtn.addEventListener("click", refreshAll);
els.roomsRefreshBtn.addEventListener("click", refreshRooms);
els.hintBtn.addEventListener("click", askHint);
els.surrenderBtn.addEventListener("click", surrender);
els.rematchBtn.addEventListener("click", rematch);

renderGame();
restoreSession().then(refreshAll);
