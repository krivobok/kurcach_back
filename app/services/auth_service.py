from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import current_app

from ..models import User
from ..repositories import AuditRepository, ConflictError, NotFoundError, UserRepository, utcnow
from ..utils.security import hash_password, hash_token, new_token, verify_password
from ..utils.validators import validate_email, validate_username


class AuthError(RuntimeError):
    pass


class AuthService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.audit = AuditRepository()

    def register(
        self,
        username: str,
        password: str,
        display_name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
        account_type: str = "client",
        admin_code: str | None = None,
    ) -> dict[str, object]:
        username = validate_username(username)
        email = validate_email(email)
        is_admin = self._resolve_admin_flag(account_type, admin_code)
        if len(password) < 6:
            raise AuthError("Password must be at least 6 characters")
        try:
            user = self.users.create(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name or username,
                email=email,
                avatar_url=avatar_url,
                is_admin=is_admin,
                rating=current_app.config.get("DEFAULT_RATING", 1000),
            )
        except ConflictError as exc:
            raise AuthError(str(exc)) from exc
        self.audit.add(user.id, "register", "user", user.id, {"username": username, "account_type": "admin" if is_admin else "client"})
        return self._issue_session(user)

    def login(self, username: str, password: str) -> dict[str, object]:
        user = self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Invalid username or password")
        if user.status == "banned":
            raise AuthError("Account is banned by administrator")
        self.users.update_status(user.id, "online")
        self.audit.add(user.id, "login", "user", user.id)
        return self._issue_session(self.users.get_by_id(user.id))

    def authenticate_token(self, token: str | None) -> User | None:
        if not token:
            return None
        user = self.users.find_token_user(hash_token(token), utcnow())
        if user:
            if user.status == "banned":
                return None
            self.users.update_status(user.id, "online")
            return self.users.get_by_id(user.id)
        return None

    def logout(self, token: str | None, actor_id: int | None = None) -> bool:
        if not token:
            return False
        revoked = self.users.revoke_token(hash_token(token))
        if revoked:
            self.audit.add(actor_id, "logout", "auth_token", None)
        return revoked

    def profile(self, user_id: int) -> dict[str, object]:
        try:
            user = self.users.get_by_id(user_id)
        except NotFoundError as exc:
            raise AuthError("User not found") from exc
        return user.public()

    def update_profile(self, user_id: int, display_name: str | None, email: str | None, avatar_url: str | None) -> dict[str, object]:
        email = validate_email(email)
        try:
            user = self.users.update_profile(user_id, display_name, email, avatar_url)
        except ConflictError as exc:
            raise AuthError(str(exc)) from exc
        self.audit.add(user_id, "update_profile", "user", user_id)
        return user.public()

    def _issue_session(self, user: User) -> dict[str, object]:
        token = new_token()
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(current_app.config.get("TOKEN_TTL_SECONDS", 86400)))).replace(microsecond=0).isoformat()
        self.users.create_token(user.id, hash_token(token), expires_at)
        return {"token": token, "expires_at": expires_at, "user": user.public()}

    def _resolve_admin_flag(self, account_type: str, admin_code: str | None) -> bool:
        account_type = (account_type or "client").strip().lower()
        if account_type in {"client", "user", "player"}:
            return False
        if account_type != "admin":
            raise AuthError("Unknown account type")
        expected = str(current_app.config.get("ADMIN_REGISTRATION_CODE", "")).strip()
        if not expected or admin_code != expected:
            raise AuthError("Invalid admin registration code")
        return True
