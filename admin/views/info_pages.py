import os

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


class InfoPageView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Інфо-сторінки",
            icon="fa fa-info-circle",
            path="/info-pages",
            methods=["GET", "POST"],
            name="info_pages",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, content, sort_order FROM info_pages ORDER BY sort_order, id"
            )
        pages = [dict(r) for r in rows]
        return _templates.TemplateResponse(
            "info_pages.html",
            {"request": request, "pages": pages},
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "save")
        pid = int(form.get("id") or 0)

        async with db.pool.acquire() as conn:
            if action == "delete":
                await conn.execute("DELETE FROM info_pages WHERE id=$1", pid)
            elif pid == 0:
                await conn.execute(
                    "INSERT INTO info_pages (title, content, sort_order) VALUES ($1, $2, $3)",
                    form["title"].strip(),
                    form["content"].strip(),
                    int(form.get("sort_order") or 0),
                )
            else:
                await conn.execute(
                    "UPDATE info_pages SET title=$1, content=$2, sort_order=$3 WHERE id=$4",
                    form["title"].strip(),
                    form["content"].strip(),
                    int(form.get("sort_order") or 0),
                    pid,
                )

        return RedirectResponse("/admin/info-pages", status_code=303)
