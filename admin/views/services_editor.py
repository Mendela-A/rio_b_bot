import os
from typing import Optional

from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db

_templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "..", "templates")
)


class ServicesEditorView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Редактор послуг",
            icon="fa fa-list-alt",
            path="/services-editor",
            methods=["GET", "POST"],
            name="services_editor",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    # ------------------------------------------------------------------ #
    # GET                                                                  #
    # ------------------------------------------------------------------ #

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            categories = await conn.fetch(
                "SELECT id, name FROM categories ORDER BY id"
            )
            services = await conn.fetch(
                """
                SELECT id, category_id, parent_id, name, price, description, is_active
                FROM services
                ORDER BY parent_id NULLS FIRST, id
                """
            )

        data = []
        for cat in categories:
            cat_svcs = [dict(s) for s in services if s["category_id"] == cat["id"]]
            children_map: dict[int, list] = {}
            for s in cat_svcs:
                if s["parent_id"] is not None:
                    children_map.setdefault(s["parent_id"], []).append(s)
            parents = [
                {**s, "children": children_map.get(s["id"], [])}
                for s in cat_svcs
                if s["parent_id"] is None
            ]
            data.append({"id": cat["id"], "name": cat["name"], "services": parents})

        return _templates.TemplateResponse(
            "services_editor.html",
            {"request": request, "data": data},
        )

    # ------------------------------------------------------------------ #
    # POST                                                                 #
    # ------------------------------------------------------------------ #

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("_action", "save")

        if action == "delete":
            await self._delete(int(form["id"]))
        else:
            await self._save(form)

        return RedirectResponse("/admin/services-editor", status_code=303)

    async def _save(self, form) -> None:
        sid = int(form.get("id") or 0)
        category_id = int(form["category_id"])
        parent_id = _int_or_none(form.get("parent_id"))
        name = form["name"].strip()
        price = _float_or_none(form.get("price"))
        description = form.get("description", "").strip() or None
        is_active = form.get("is_active") == "on"

        async with db.pool.acquire() as conn:
            if sid == 0:
                await conn.execute(
                    """
                    INSERT INTO services (category_id, parent_id, name, price, description, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    category_id, parent_id, name, price, description, is_active,
                )
            else:
                await conn.execute(
                    """
                    UPDATE services
                    SET name=$1, price=$2, description=$3, is_active=$4
                    WHERE id=$5
                    """,
                    name, price, description, is_active, sid,
                )

    async def _delete(self, service_id: int) -> None:
        async with db.pool.acquire() as conn:
            await conn.execute("DELETE FROM services WHERE id=$1", service_id)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _int_or_none(value) -> Optional[int]:
    try:
        v = int(value)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _float_or_none(value) -> Optional[float]:
    try:
        v = float(value)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None
