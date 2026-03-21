from datetime import date

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.views import CustomView

import db
from shared import templates as _templates


class ChildrenView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="База іменинників",
            icon="fa fa-birthday-cake",
            path="/children",
            methods=["GET"],
            name="children",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        raw = request.query_params.get("month", "")
        month_filter = raw if raw.isdigit() and 1 <= int(raw) <= 12 else ""
        where = "AND EXTRACT(MONTH FROM b.birthday_person_date) = $1" if month_filter else ""

        async with db.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT b.id, b.full_name, b.phone,
                       b.birthday_person_name, b.birthday_person_date,
                       b.booking_date
                FROM bookings b
                WHERE b.birthday_person_name IS NOT NULL
                  AND b.birthday_person_date IS NOT NULL
                  {where}
                ORDER BY EXTRACT(MONTH FROM b.birthday_person_date),
                         EXTRACT(DAY FROM b.birthday_person_date)
            """, *([int(month_filter)] if month_filter else []))

        return _templates.TemplateResponse("children.html", {
            "request": request,
            "children": [dict(r) for r in rows],
            "month_filter": month_filter,
            "now_month": date.today().month,
        })
