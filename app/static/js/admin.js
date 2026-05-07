const adminState = {
    token: localStorage.getItem("tttToken") || "",
    user: null,
};

const adminEls = {
    status: document.querySelector("#adminStatus"),
    content: document.querySelector("#adminContent"),
    username: document.querySelector("#adminUsername"),
    password: document.querySelector("#adminPassword"),
    code: document.querySelector("#adminCode"),
    login: document.querySelector("#adminLoginBtn"),
    register: document.querySelector("#adminRegisterBtn"),
    logout: document.querySelector("#adminLogoutBtn"),
    refresh: document.querySelector("#refreshAdminBtn"),
    users: document.querySelector("#adminUsers"),
    rooms: document.querySelector("#adminRooms"),
    audit: document.querySelector("#auditLog"),
    usersTotal: document.querySelector("#usersTotal"),
    roomsTotal: document.querySelector("#roomsTotal"),
    gamesPlaying: document.querySelector("#gamesPlaying"),
    gamesFinished: document.querySelector("#gamesFinished"),
};

const roleText = {
    admin: "администратор",
    client: "клиент",
};

const userStatusText = {
    online: "онлайн",
    offline: "офлайн",
    banned: "заблокирован",
};

const roomStatusText = {
    waiting: "ожидает игроков",
    playing: "идёт игра",
    finished: "завершена",
    closed: "закрыта администратором",
};

const roomModeText = {
    public: "для двух игроков",
    private: "закрытая",
    ai: "с компьютером",
    matchmaking: "подбор соперника",
};

const actionText = {
    register: "Регистрация",
    login: "Вход",
    logout: "Выход",
    update_profile: "Обновление профиля",
    create_room: "Создание комнаты",
    join_room: "Вход в комнату",
    leave_room: "Выход из комнаты",
    surrender: "Сдача партии",
    rematch: "Реванш",
    admin_set_role: "Изменение роли",
    admin_set_status: "Изменение статуса пользователя",
    admin_revoke_tokens: "Отзыв токенов",
    admin_delete_user: "Удаление пользователя",
    admin_set_room_status: "Изменение статуса комнаты",
    admin_delete_room: "Удаление комнаты",
};

const errorText = {
    "Authentication required": "Нужно войти в аккаунт.",
    "Admin access required": "У аккаунта нет прав администратора.",
    "Invalid username or password": "Неверный логин или пароль.",
    "Invalid admin registration code": "Неверный код администратора.",
    "Account is banned by administrator": "Аккаунт заблокирован администратором.",
    "Admin cannot delete own account": "Администратор не может удалить свой аккаунт.",
    "Admin cannot ban own account": "Администратор не может заблокировать свой аккаунт.",
    "Admin cannot remove own admin role": "Нельзя снять права администратора с самого себя.",
    "Room not found": "Комната не найдена.",
    "User not found": "Пользователь не найден.",
    "Unsupported room status": "Неподдерживаемый статус комнаты.",
    "Unsupported user status": "Неподдерживаемый статус пользователя.",
};

function translateError(message) {
    return errorText[message] || message || "Ошибка запроса.";
}

function adminMessage(text, isError = false) {
    adminEls.status.textContent = text;
    adminEls.status.className = isError ? "message error" : "muted";
}

function adminHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (adminState.token) {
        headers.Authorization = `Bearer ${adminState.token}`;
    }
    return headers;
}

async function adminApi(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: { ...adminHeaders(), ...(options.headers || {}) },
    });
    const data = await response.json();
    if (!data.ok) {
        throw new Error(translateError(data.error && data.error.message));
    }
    return data.data;
}

async function adminLogin() {
    try {
        const data = await adminApi("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username: adminEls.username.value.trim(), password: adminEls.password.value }),
        });
        saveAdminSession(data);
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function adminRegister() {
    try {
        const data = await adminApi("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({
                username: adminEls.username.value.trim(),
                password: adminEls.password.value,
                display_name: "Администратор",
                account_type: "admin",
                admin_code: adminEls.code.value,
            }),
        });
        saveAdminSession(data);
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

function saveAdminSession(data) {
    adminState.token = data.token;
    adminState.user = data.user;
    localStorage.setItem("tttToken", data.token);
}

function adminLogout() {
    adminState.token = "";
    adminState.user = null;
    localStorage.removeItem("tttToken");
    adminEls.content.classList.add("hidden");
    adminMessage("Вы вышли из админ-панели.");
}

async function restoreAdmin() {
    if (!adminState.token) {
        adminMessage("Войдите под администратором.");
        return;
    }
    try {
        adminState.user = await adminApi("/api/auth/me");
        await loadAdminPanel();
    } catch (error) {
        adminLogout();
    }
}

async function loadAdminPanel() {
    if (!adminState.user || !adminState.user.is_admin) {
        adminEls.content.classList.add("hidden");
        adminMessage("У этого аккаунта нет прав администратора.", true);
        return;
    }
    adminEls.content.classList.remove("hidden");
    adminMessage(`Вы вошли как администратор: ${adminState.user.display_name || adminState.user.username}`);
    const [dashboard, users, rooms, audit] = await Promise.all([
        adminApi("/api/admin/dashboard"),
        adminApi("/api/admin/users?limit=100"),
        adminApi("/api/admin/rooms?limit=100"),
        adminApi("/api/admin/audit?limit=30"),
    ]);
    renderDashboard(dashboard);
    renderUsers(users);
    renderRooms(rooms);
    renderAudit(audit);
}

function renderDashboard(data) {
    adminEls.usersTotal.textContent = data.users_total;
    adminEls.roomsTotal.textContent = data.rooms_total;
    adminEls.gamesPlaying.textContent = data.games_playing;
    adminEls.gamesFinished.textContent = data.games_finished;
}

function renderUsers(users) {
    adminEls.users.innerHTML = "";
    users.forEach((user) => {
        const row = document.createElement("div");
        row.className = "admin-row";
        const info = document.createElement("div");
        const role = roleText[user.role] || user.role;
        const status = userStatusText[user.status] || user.status;
        info.innerHTML = `<strong>${user.display_name}</strong><span>@${user.username} · ${role} · ${status} · рейтинг ${user.rating}</span>`;
        const actions = document.createElement("div");
        actions.className = "admin-actions";

        const roleButton = document.createElement("button");
        roleButton.type = "button";
        roleButton.className = "small secondary";
        roleButton.textContent = user.is_admin ? "Сделать клиентом" : "Сделать администратором";
        roleButton.addEventListener("click", () => setUserRole(user.id, !user.is_admin));

        const banButton = document.createElement("button");
        banButton.type = "button";
        banButton.className = user.status === "banned" ? "small" : "small danger";
        banButton.textContent = user.status === "banned" ? "Разблокировать" : "Заблокировать";
        banButton.addEventListener("click", () => setUserStatus(user.id, user.status === "banned" ? "offline" : "banned"));

        const revokeButton = document.createElement("button");
        revokeButton.type = "button";
        revokeButton.className = "small ghost";
        revokeButton.textContent = "Отозвать токены";
        revokeButton.addEventListener("click", () => revokeTokens(user.id));

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "small danger";
        removeButton.textContent = "Удалить";
        removeButton.addEventListener("click", () => deleteUser(user.id));

        actions.append(roleButton, banButton, revokeButton, removeButton);
        row.append(info, actions);
        adminEls.users.appendChild(row);
    });
}

function renderRooms(rooms) {
    adminEls.rooms.innerHTML = "";
    rooms.forEach((room) => {
        const row = document.createElement("div");
        row.className = "admin-row";
        const info = document.createElement("div");
        const mode = roomModeText[room.mode] || room.mode;
        const status = roomStatusText[room.status] || room.status;
        info.innerHTML = `<strong>${room.name}</strong><span>${mode} · ${status} · ${room.board_size}x${room.board_size} · игроков ${room.players.length}</span>`;
        const actions = document.createElement("div");
        actions.className = "admin-actions";

        const finishButton = document.createElement("button");
        finishButton.type = "button";
        finishButton.className = "small ghost";
        finishButton.textContent = "Завершить";
        finishButton.addEventListener("click", () => setRoomStatus(room.id, "finished"));

        const closeButton = document.createElement("button");
        closeButton.type = "button";
        closeButton.className = "small danger";
        closeButton.textContent = "Закрыть";
        closeButton.addEventListener("click", () => setRoomStatus(room.id, "closed"));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "small danger";
        deleteButton.textContent = "Удалить комнату";
        deleteButton.addEventListener("click", () => deleteRoom(room.id));

        actions.append(finishButton, closeButton, deleteButton);
        row.append(info, actions);
        adminEls.rooms.appendChild(row);
    });
}

function renderAudit(rows) {
    adminEls.audit.innerHTML = "";
    rows.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "admin-row";
        const info = document.createElement("div");
        const action = actionText[entry.action] || entry.action;
        const entity = entry.entity_type === "user" ? "пользователь" : entry.entity_type === "room" ? "комната" : entry.entity_type;
        info.innerHTML = `<strong>${action}</strong><span>${entity} #${entry.entity_id || "-"} · автор #${entry.actor_id || "-"} · ${entry.created_at}</span>`;
        row.appendChild(info);
        adminEls.audit.appendChild(row);
    });
}

async function setUserRole(userId, isAdmin) {
    try {
        await adminApi(`/api/admin/users/${userId}/role`, { method: "PATCH", body: JSON.stringify({ is_admin: isAdmin }) });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function setUserStatus(userId, status) {
    try {
        await adminApi(`/api/admin/users/${userId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function revokeTokens(userId) {
    try {
        await adminApi(`/api/admin/users/${userId}/tokens/revoke`, { method: "POST" });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function deleteUser(userId) {
    try {
        await adminApi(`/api/admin/users/${userId}`, { method: "DELETE" });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function setRoomStatus(roomId, status) {
    try {
        await adminApi(`/api/admin/rooms/${roomId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

async function deleteRoom(roomId) {
    try {
        await adminApi(`/api/admin/rooms/${roomId}`, { method: "DELETE" });
        await loadAdminPanel();
    } catch (error) {
        adminMessage(error.message, true);
    }
}

adminEls.login.addEventListener("click", adminLogin);
adminEls.register.addEventListener("click", adminRegister);
adminEls.logout.addEventListener("click", adminLogout);
adminEls.refresh.addEventListener("click", loadAdminPanel);
restoreAdmin();
