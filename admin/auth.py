from typing import Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

import db
from shared import pwd_ctx


class MyAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash, is_superadmin FROM admin_users WHERE username = $1 AND is_active = TRUE",
                username,
            )
        if row and pwd_ctx.verify(password, row["password_hash"]):
            request.session.update({
                "username": username,
                "is_superadmin": bool(row["is_superadmin"]),
            })
            return response
        raise LoginFailed("Невірний логін або пароль")

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get("username")
        if not username:
            return False
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT is_superadmin FROM admin_users WHERE username = $1 AND is_active = TRUE",
                username,
            )
        if not row:
            return False
        # Backfill is_superadmin into session if missing (e.g. after migration)
        if "is_superadmin" not in request.session:
            request.session["is_superadmin"] = bool(row["is_superadmin"])
        return True

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(app_title="РІО Адмін")

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        username = request.session.get("username", "")
        return AdminUser(username=username)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response
