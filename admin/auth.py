from typing import Optional

from passlib.context import CryptContext
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

import db

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
                "SELECT password_hash FROM admin_users WHERE username = $1 AND is_active = TRUE",
                username,
            )
        if row and pwd_ctx.verify(password, row["password_hash"]):
            request.session.update({"username": username})
            return response
        raise LoginFailed("Невірний логін або пароль")

    async def is_authenticated(self, request: Request) -> bool:
        username = request.session.get("username")
        if not username:
            return False
        async with db.pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM admin_users WHERE username = $1 AND is_active = TRUE",
                username,
            )
        return bool(exists)

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(app_title="РІО Адмін")

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        username = request.session.get("username", "")
        return AdminUser(username=username)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response
