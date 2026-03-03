from typing import Any, Dict, List, Optional, Sequence, Union

from starlette.requests import Request
from starlette_admin import EnumField, IntegerField, StringField
from starlette_admin.views import BaseModelView

import db
from views.services import AttrDict

TYPE_CHOICES = [
    ("venue", "venue — Додаткові послуги"),
    ("offsite", "offsite — Аніматор на виїзд"),
    ("program", "program — Програми та аніматори"),
]


class CategoryView(BaseModelView):
    identity = "category"
    name = "Категорії"
    label = "Категорії"
    icon = "fa fa-folder"
    pk_attr = "id"

    fields = [
        IntegerField("id", label="ID", read_only=True, exclude_from_create=True),
        StringField("name", label="Назва", required=True),
        EnumField("type", label="Тип (для бота)", choices=TYPE_CHOICES, required=True),
    ]

    async def count(
        self,
        request: Request,
        where: Union[Dict[str, Any], str, None] = None,
    ) -> int:
        async with db.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM categories")

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Union[Dict[str, Any], str, None] = None,
        order_by: Optional[List[str]] = None,
    ) -> Sequence[Any]:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, name, type FROM categories ORDER BY id LIMIT $1 OFFSET $2",
                limit,
                skip,
            )
        return [AttrDict(r) for r in rows]

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, type FROM categories WHERE id=$1",
                int(pk),
            )
        return AttrDict(row) if row else None

    async def create(self, request: Request, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO categories (name, type) VALUES ($1, $2) RETURNING id",
                data["name"],
                data["type"],
            )
        return await self.find_by_pk(request, row["id"])

    async def edit(self, request: Request, pk: Any, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE categories SET name=$1, type=$2 WHERE id=$3",
                data["name"],
                data["type"],
                int(pk),
            )
        return await self.find_by_pk(request, pk)

    async def delete(self, request: Request, pks: List[Any]) -> Optional[int]:
        ids = [int(pk) for pk in pks]
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM categories WHERE id = ANY($1::int[])",
                ids,
            )
        return len(ids)
