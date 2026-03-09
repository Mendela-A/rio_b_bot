from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates, pwd_ctx


class AdminUsersView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Користувачі",
            icon="fa fa-users",
            path="/admin-users",
            methods=["GET", "POST"],
            name="admin_users",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if not request.session.get("is_superadmin"):
            return RedirectResponse("/admin", status_code=303)
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request, error=None, success=None)

    async def _render_page(self, request: Request, error: str | None, success: str | None) -> Response:
        async with db.pool.acquire() as conn:
            users = await conn.fetch(
                "SELECT id, username, is_active FROM admin_users ORDER BY id"
            )
        return _templates.TemplateResponse(
            "admin_users.html", {
                "request": request,
                "users": users,
                "current_user": request.session.get("username"),
                "error": error,
                "success": success,
            }
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "")
        current = request.session.get("username")

        async with db.pool.acquire() as conn:
            if action == "add":
                username = (form.get("username") or "").strip()
                password = (form.get("password") or "").strip()
                confirm = (form.get("confirm") or "").strip()
                if not username or not password:
                    return await self._render_page(request, error="Заповніть всі поля", success=None)
                if password != confirm:
                    return await self._render_page(request, error="Паролі не співпадають", success=None)
                exists = await conn.fetchval(
                    "SELECT 1 FROM admin_users WHERE username = $1", username
                )
                if exists:
                    return await self._render_page(request, error=f"Користувач «{username}» вже існує", success=None)
                hashed = pwd_ctx.hash(password)
                await conn.execute(
                    "INSERT INTO admin_users (username, password_hash) VALUES ($1, $2)",
                    username, hashed,
                )
                return await self._render_page(request, error=None, success=f"Користувача «{username}» додано")

            elif action == "change_own_password":
                old_password = (form.get("old_password") or "").strip()
                password = (form.get("password") or "").strip()
                confirm = (form.get("confirm") or "").strip()
                if not old_password or not password:
                    return await self._render_page(request, error="Заповніть всі поля", success=None)
                if password != confirm:
                    return await self._render_page(request, error="Нові паролі не співпадають", success=None)
                row = await conn.fetchrow(
                    "SELECT password_hash FROM admin_users WHERE username = $1", current
                )
                if not row or not pwd_ctx.verify(old_password, row["password_hash"]):
                    return await self._render_page(request, error="Невірний поточний пароль", success=None)
                hashed = pwd_ctx.hash(password)
                await conn.execute(
                    "UPDATE admin_users SET password_hash = $1 WHERE username = $2",
                    hashed, current,
                )
                return await self._render_page(request, error=None, success="Пароль успішно змінено")

            elif action == "change_password":
                username = (form.get("username") or "").strip()
                password = (form.get("password") or "").strip()
                confirm = (form.get("confirm") or "").strip()
                if not password:
                    return await self._render_page(request, error="Введіть новий пароль", success=None)
                if password != confirm:
                    return await self._render_page(request, error="Паролі не співпадають", success=None)
                hashed = pwd_ctx.hash(password)
                await conn.execute(
                    "UPDATE admin_users SET password_hash = $1 WHERE username = $2",
                    hashed, username,
                )
                return await self._render_page(request, error=None, success=f"Пароль для «{username}» змінено")

            elif action == "toggle":
                username = (form.get("username") or "").strip()
                if username == current:
                    return await self._render_page(request, error="Не можна деактивувати себе", success=None)
                await conn.execute(
                    "UPDATE admin_users SET is_active = NOT is_active WHERE username = $1",
                    username,
                )

            elif action == "delete":
                username = (form.get("username") or "").strip()
                if username == current:
                    return await self._render_page(request, error="Не можна видалити себе", success=None)
                await conn.execute(
                    "DELETE FROM admin_users WHERE username = $1", username
                )

        return RedirectResponse("/admin/admin-users", status_code=303)
