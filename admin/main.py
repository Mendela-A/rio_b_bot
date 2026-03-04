import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.base import BaseAdmin

import db
from auth import MyAuthProvider
from db import lifespan
from views.bookings import BookingsView
from views.bot_texts import BotTextsView
from views.categories import CategoryView
from views.info_pages import InfoPageView
from views.services_editor import ServicesEditorView
from views.blocked_dates import BlockedDatesView
from views.settings import SettingsView
from views.admin_users import AdminUsersView

load_dotenv()

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "changeme-set-in-env")

_templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


class RioAdmin(BaseAdmin):
    async def _render_index(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            stats = {
                "services":   await conn.fetchval("SELECT COUNT(*) FROM services"),
                "categories": await conn.fetchval("SELECT COUNT(*) FROM categories"),
                "info_pages": await conn.fetchval("SELECT COUNT(*) FROM info_pages"),
                "bookings":   await conn.fetchval("SELECT COUNT(*) FROM bookings"),
            }
        return _templates.TemplateResponse(
            "dashboard.html", {"request": request, "stats": stats}
        )


app = FastAPI(lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

admin = RioAdmin(
    title="РІО Адмін",
    auth_provider=MyAuthProvider(),
    middlewares=[Middleware(SessionMiddleware, secret_key=SECRET_KEY)],
)

admin.add_view(ServicesEditorView())
admin.add_view(BookingsView())
admin.add_view(BotTextsView())
admin.add_view(CategoryView())
admin.add_view(InfoPageView())
admin.add_view(SettingsView())
admin.add_view(BlockedDatesView())
admin.add_view(AdminUsersView())
admin.mount_to(app)
