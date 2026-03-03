import os
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


class MyAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            request.session.update({"username": username})
            return response
        raise LoginFailed("Невірний логін або пароль")

    async def is_authenticated(self, request: Request) -> bool:
        return request.session.get("username") == ADMIN_USER

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(app_title="РІО Адмін")

    def get_admin_user(self, request: Request) -> Optional[AdminUser]:
        username = request.session.get("username", "")
        return AdminUser(username=username)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response
