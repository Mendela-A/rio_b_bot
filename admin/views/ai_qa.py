from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates


class AiQaView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="База знань",
            icon="fa fa-robot",
            path="/ai-qa",
            methods=["GET", "POST"],
            name="ai_qa",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            pairs = await conn.fetch(
                "SELECT id, question, answer, is_active, sort_order "
                "FROM ai_qa_pairs ORDER BY sort_order, id"
            )
            next_sort = await conn.fetchval(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM ai_qa_pairs"
            )
        return _templates.TemplateResponse(
            "ai_qa.html",
            {
                "request": request,
                "pairs": [dict(p) for p in pairs],
                "next_sort": next_sort,
                "saved": request.query_params.get("saved"),
                "deleted": request.query_params.get("deleted"),
            },
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        action = form.get("action", "")

        async with db.pool.acquire() as conn:
            if action == "delete":
                pair_id = int(form.get("id", 0))
                if pair_id:
                    await conn.execute("DELETE FROM ai_qa_pairs WHERE id=$1", pair_id)
                return RedirectResponse("/admin/ai-qa?deleted=1", status_code=303)

            elif action == "save":
                pair_id = form.get("id", "").strip()
                question = (form.get("question") or "").strip()
                answer = (form.get("answer") or "").strip()
                is_active = form.get("is_active") == "on"
                sort_order = int(form.get("sort_order") or 0)

                if not question or not answer:
                    return RedirectResponse("/admin/ai-qa", status_code=303)

                if pair_id:
                    await conn.execute(
                        "UPDATE ai_qa_pairs SET question=$1, answer=$2, is_active=$3, sort_order=$4 WHERE id=$5",
                        question, answer, is_active, sort_order, int(pair_id),
                    )
                else:
                    if not form.get("sort_order", "").strip():
                        sort_order = await conn.fetchval(
                            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM ai_qa_pairs"
                        )
                    await conn.execute(
                        "INSERT INTO ai_qa_pairs (question, answer, is_active, sort_order) VALUES ($1,$2,$3,$4)",
                        question, answer, is_active, sort_order,
                    )
                return RedirectResponse("/admin/ai-qa?saved=1", status_code=303)

        return RedirectResponse("/admin/ai-qa", status_code=303)
