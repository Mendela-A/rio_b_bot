from typing import Any, Dict, List, Optional, Sequence, Union

from starlette.requests import Request
from starlette_admin import IntegerField, StringField, TextAreaField
from starlette_admin.views import BaseModelView

import db


class AttrDict(dict):
    """Dict that also supports attribute access — required by starlette-admin."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class InfoPageView(BaseModelView):
    identity = "info_page"
    name = "Інфо-сторінки"
    label = "Інфо-сторінки"
    icon = "fa fa-info-circle"
    pk_attr = "id"

    fields = [
        IntegerField("id", label="ID", read_only=True, exclude_from_create=True),
        StringField("title", label="Заголовок", required=True),
        TextAreaField("content", label="Зміст", required=True),
        IntegerField("sort_order", label="Порядок сортування", required=False),
    ]

    async def count(
        self,
        request: Request,
        where: Union[Dict[str, Any], str, None] = None,
    ) -> int:
        q = "SELECT COUNT(*) FROM info_pages"
        params: list = []
        if isinstance(where, str) and where:
            q += " WHERE title ILIKE $1"
            params.append(f"%{where}%")
        async with db.pool.acquire() as conn:
            return await conn.fetchval(q, *params)

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Union[Dict[str, Any], str, None] = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        q = "SELECT * FROM info_pages"
        params: list = []
        if isinstance(where, str) and where:
            q += " WHERE title ILIKE $1"
            params.append(f"%{where}%")
        q += " ORDER BY sort_order, id"
        q += f" LIMIT {limit} OFFSET {skip}"
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(q, *params)
        return [AttrDict(r) for r in rows]

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM info_pages WHERE id=$1", int(pk))
        return AttrDict(row) if row else None

    async def create(self, request: Request, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO info_pages (title, content, sort_order)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                data["title"],
                data["content"],
                int(data.get("sort_order") or 0),
            )
        return AttrDict(row)

    async def edit(self, request: Request, pk: Any, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE info_pages
                SET title=$1, content=$2, sort_order=$3
                WHERE id=$4
                RETURNING *
                """,
                data["title"],
                data["content"],
                int(data.get("sort_order") or 0),
                int(pk),
            )
        return AttrDict(row)

    async def delete(self, request: Request, pks: List[Any]) -> Optional[int]:
        ids = [int(pk) for pk in pks]
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM info_pages WHERE id = ANY($1::int[])",
                ids,
            )
        return len(ids)
