from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates, pwd_ctx


class ChangePasswordView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Змінити пароль",
            icon="fa fa-key",
            path="/change-password",
            methods=["GET", "POST"],
            name="change_password",
            add_to_menu=False,
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return _templates.TemplateResponse(
            "change_password.html", {"request": request, "error": None, "success": None}
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        old_password = (form.get("old_password") or "").strip()
        password = (form.get("password") or "").strip()
        confirm = (form.get("confirm") or "").strip()
        current = request.session.get("username")

        def fail(msg):
            return _templates.TemplateResponse(
                "change_password.html", {"request": request, "error": msg, "success": None}
            )

        if not old_password or not password:
            return fail("Заповніть всі поля")
        if password != confirm:
            return fail("Нові паролі не співпадають")

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash FROM admin_users WHERE username = $1", current
            )
            if not row or not pwd_ctx.verify(old_password, row["password_hash"]):
                return fail("Невірний поточний пароль")
            hashed = pwd_ctx.hash(password)
            await conn.execute(
                "UPDATE admin_users SET password_hash = $1 WHERE username = $2",
                hashed, current,
            )

        return _templates.TemplateResponse(
            "change_password.html", {"request": request, "error": None, "success": "Пароль успішно змінено"}
        )
