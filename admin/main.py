import os

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.base import BaseAdmin

from auth import MyAuthProvider
from db import lifespan
from views.categories import CategoryView
from views.info_pages import InfoPageView
from views.services import ServiceView, load_category_choices, load_parent_choices

load_dotenv()

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "changeme-set-in-env")


class RioAdmin(BaseAdmin):
    """BaseAdmin subclass that pre-fetches dynamic choices before form rendering."""

    async def _load_service_choices(self, request: Request) -> None:
        if request.path_params.get("identity") == "service":
            await load_category_choices(request)
            await load_parent_choices(request)

    async def _render_api(self, request: Request) -> Response:
        await self._load_service_choices(request)
        return await super()._render_api(request)

    async def _render_create(self, request: Request) -> Response:
        await self._load_service_choices(request)
        return await super()._render_create(request)

    async def _render_edit(self, request: Request) -> Response:
        await self._load_service_choices(request)
        return await super()._render_edit(request)


app = FastAPI(lifespan=lifespan)

admin = RioAdmin(
    title="РІО Адмін",
    auth_provider=MyAuthProvider(),
    middlewares=[Middleware(SessionMiddleware, secret_key=SECRET_KEY)],
)

admin.add_view(CategoryView())
admin.add_view(ServiceView())
admin.add_view(InfoPageView())
admin.mount_to(app)
