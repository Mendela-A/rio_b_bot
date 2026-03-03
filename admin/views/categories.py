import os

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)

TYPE_LABELS = {
    "venue":   "venue — Додаткові послуги",
    "offsite": "offsite — Аніматор на виїзд",
    "program": "program — Програми та аніматори",
}


class CategoryView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Категорії",
            icon="fa fa-folder",
            path="/categories",
            methods=["GET", "POST"],
            name="categories",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name, type FROM categories ORDER BY id")
        categories = [dict(r) for r in rows]
        return _templates.TemplateResponse(
            "categories.html",
            {"request": request, "categories": categories, "type_labels": TYPE_LABELS},
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "save")
        cid = int(form.get("id") or 0)

        async with db.pool.acquire() as conn:
            if action == "delete":
                await conn.execute("DELETE FROM categories WHERE id=$1", cid)
            elif cid == 0:
                await conn.execute(
                    "INSERT INTO categories (name, type) VALUES ($1, $2)",
                    form["name"].strip(), form["type"],
                )
            else:
                await conn.execute(
                    "UPDATE categories SET name=$1, type=$2 WHERE id=$3",
                    form["name"].strip(), form["type"], cid,
                )

        return RedirectResponse("/admin/categories", status_code=303)
