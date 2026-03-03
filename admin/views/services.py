from typing import Any, Dict, List, Optional, Sequence, Union

from starlette.requests import Request
from starlette_admin import (
    BooleanField,
    DecimalField,
    EnumField,
    IntegerField,
    StringField,
    TextAreaField,
)
from starlette_admin.views import BaseModelView

import db

# Static category list — matches seed data in init.sql
CATEGORY_CHOICES = [
    ("1", "Додаткові послуги (venue)"),
    ("2", "Аніматор на виїзд (offsite)"),
    ("3", "Програми та аніматори (program)"),
]

# Query used in find_all and find_by_pk:
# - LEFT JOIN brings parent name
# - ORDER BY groups children right after their parent
_SELECT = """
    SELECT
        s.id, s.category_id, s.name, s.price, s.description,
        s.sort_order, s.parent_id, s.is_active,
        p.name AS parent_name
    FROM services s
    LEFT JOIN services p ON s.parent_id = p.id
"""
_ORDER = """
    ORDER BY
        COALESCE(s.parent_id, s.id),   -- group child under parent
        s.parent_id NULLS FIRST,        -- parent row before children
        s.sort_order,
        s.id
"""


async def load_parent_choices(request: Request) -> None:
    """Fetch top-level services and store them in request.state for the form."""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name FROM services WHERE parent_id IS NULL"
            " ORDER BY sort_order, id"
        )
    request.state.parent_choices = [("", "— без батька —")] + [
        (str(r["id"]), r["name"]) for r in rows
    ]


def _parent_choices_loader(request: Request):
    """Sync loader that reads choices pre-fetched into request.state."""
    return getattr(request.state, "parent_choices", [("", "— без батька —")])


class AttrDict(dict):
    """Dict that also supports attribute access — required by starlette-admin."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


class ServiceView(BaseModelView):
    identity = "service"
    name = "Послуги"
    label = "Послуги"
    icon = "fa fa-star"
    pk_attr = "id"

    fields = [
        IntegerField("id", label="ID", read_only=True, exclude_from_create=True),
        EnumField(
            "category_id",
            label="Категорія",
            choices=CATEGORY_CHOICES,
            coerce=int,
            required=True,
        ),
        StringField("name", label="Назва", required=True),
        DecimalField("price", label="Ціна (грн)", required=True),
        TextAreaField("description", label="Опис", required=False),
        IntegerField("sort_order", label="Порядок сортування", required=False),
        EnumField(
            "parent_id",
            label="Батьківська послуга",
            choices_loader=_parent_choices_loader,
            coerce=lambda v: int(v) if v else None,
            required=False,
            exclude_from_list=True,    # list показує parent_name
            exclude_from_detail=True,  # detail теж показує parent_name
        ),
        # Read-only column: shows parent name in list/detail, hidden in forms
        StringField(
            "parent_name",
            label="Батько",
            read_only=True,
            exclude_from_create=True,
            exclude_from_edit=True,
        ),
        BooleanField("is_active", label="Активна"),
    ]

    async def count(
        self,
        request: Request,
        where: Union[Dict[str, Any], str, None] = None,
    ) -> int:
        q = "SELECT COUNT(*) FROM services"
        params: list = []
        if isinstance(where, str) and where:
            q += " WHERE name ILIKE $1"
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
        q = _SELECT
        params: list = []
        if isinstance(where, str) and where:
            q += " WHERE s.name ILIKE $1"
            params.append(f"%{where}%")
        q += _ORDER
        q += f" LIMIT {limit} OFFSET {skip}"
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(q, *params)
        return [_to_attrdict(r) for r in rows]

    async def find_by_pk(self, request: Request, pk: Any) -> Any:
        q = _SELECT + " WHERE s.id=$1"
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(q, int(pk))
        return _to_attrdict(row) if row else None

    async def create(self, request: Request, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO services
                    (category_id, name, price, description, sort_order, parent_id, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                int(data["category_id"]),
                data["name"],
                float(data.get("price") or 0),
                data.get("description") or None,
                int(data.get("sort_order") or 0),
                _optional_int(data.get("parent_id")),
                bool(data.get("is_active", True)),
            )
        return await self.find_by_pk(None, row["id"])  # type: ignore[arg-type]

    async def edit(self, request: Request, pk: Any, data: Dict) -> Any:
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE services
                SET category_id=$1, name=$2, price=$3, description=$4,
                    sort_order=$5, parent_id=$6, is_active=$7
                WHERE id=$8
                """,
                int(data["category_id"]),
                data["name"],
                float(data.get("price") or 0),
                data.get("description") or None,
                int(data.get("sort_order") or 0),
                _optional_int(data.get("parent_id")),
                bool(data.get("is_active", True)),
                int(pk),
            )
        return await self.find_by_pk(None, pk)  # type: ignore[arg-type]

    async def delete(self, request: Request, pks: List[Any]) -> Optional[int]:
        ids = [int(pk) for pk in pks]
        async with db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM services WHERE id = ANY($1::int[])",
                ids,
            )
        return len(ids)


def _to_attrdict(row: Any) -> AttrDict:
    d = AttrDict(row)
    # EnumField with coerce=int expects string choice key
    if d.get("category_id") is not None:
        d["category_id"] = str(d["category_id"])
    # Convert Decimal price to float for DecimalField
    if d.get("price") is not None:
        d["price"] = float(d["price"])
    # parent_id shown as string in EnumField (matches choices keys)
    if d.get("parent_id") is not None:
        d["parent_id"] = str(d["parent_id"])
    return d


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "" or value == 0:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
