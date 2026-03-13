import io
import logging
import os
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.base import BaseAdmin
from starlette_admin.views import CustomView

import db
from auth import MyAuthProvider
from db import lifespan
from shared import templates as _templates, MAX_IMAGE_WIDTH, IMAGE_QUALITY, MAX_UPLOAD_SIZE
from views.bookings import BookingsView
from views.bot_texts import BotTextsView
from views.categories import CategoryView
from views.info_pages import InfoPageView
from views.services_editor import ServicesEditorView
from views.blocked_dates import BlockedDatesView
from views.settings import SettingsView
from views.admin_users import AdminUsersView
from views.broadcast import BroadcastView
from views.change_password import ChangePasswordView
from views.ai_qa import AiQaView
from views.ai_settings import AiSettingsView
from views.ai_usage import AiUsageView

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("ADMIN_SECRET_KEY must be set in environment")

DB_HOST     = os.getenv("DB_HOST", "postgres")
DB_USER     = os.getenv("DB_USER", "")
DB_NAME     = os.getenv("DB_NAME", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
UPLOADS_DIR = Path("/app/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
        return response


class DashboardView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Головна",
            icon="fa fa-home",
            path="/",
            methods=["GET"],
            name="index",
            add_to_menu=False,
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="strict")
app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads",
)
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)


@app.get("/health")
async def health():
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse({"status": "error"}, status_code=503)


@app.get("/admin/export-db")
async def export_db(request: Request):
    if not request.session.get("is_superadmin"):
        return RedirectResponse("/admin/login")

    result = subprocess.run(
        ["pg_dump", "-h", DB_HOST, "-U", DB_USER, DB_NAME],
        env={"PGPASSWORD": DB_PASSWORD, "PATH": os.environ.get("PATH", "")},
        capture_output=True,
    )

    if result.returncode != 0:
        logger.error("pg_dump failed: %s", result.stderr.decode())
        return JSONResponse({"error": "Експорт не вдався"}, status_code=500)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"rio_{ts}.sql", result.stdout)
        if UPLOADS_DIR.exists():
            for photo in UPLOADS_DIR.iterdir():
                if photo.is_file() and photo.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    zf.write(photo, f"uploads/{photo.name}")

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=rio_{ts}.zip"},
    )


admin = BaseAdmin(
    title="РІО Адмін",
    auth_provider=MyAuthProvider(),
    middlewares=[Middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="strict")],
    index_view=DashboardView(),
)

admin.add_view(ServicesEditorView())
admin.add_view(BookingsView())
admin.add_view(BotTextsView())
admin.add_view(CategoryView())
admin.add_view(InfoPageView())
admin.add_view(SettingsView())
admin.add_view(BlockedDatesView())
admin.add_view(AdminUsersView())
admin.add_view(BroadcastView())
admin.add_view(ChangePasswordView())
admin.add_view(AiQaView())
admin.add_view(AiSettingsView())
admin.add_view(AiUsageView())
admin.mount_to(app)


@app.post("/api/upload-photo")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    if not request.session.get("username"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return JSONResponse({"error": "Невірний тип файлу"}, status_code=400)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        return JSONResponse({"error": "Файл занадто великий (макс. 5 МБ)"}, status_code=413)

    img = Image.open(io.BytesIO(contents))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if img.width > MAX_IMAGE_WIDTH:
        ratio = MAX_IMAGE_WIDTH / img.width
        img = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)

    filename = uuid4().hex + ".webp"
    filepath = UPLOADS_DIR / filename
    img.save(str(filepath), "WEBP", quality=IMAGE_QUALITY)

    return JSONResponse({"url": f"/uploads/{filename}"})


@app.post("/api/category/move")
async def move_category(request: Request):
    if not request.session.get("username"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    cat_id = int(data["id"])
    direction = data["direction"]

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id FROM categories ORDER BY sort_order NULLS LAST, id"
        )
        ids = [r["id"] for r in rows]
        idx = ids.index(cat_id)

        if direction == "up" and idx == 0:
            return JSONResponse({"ok": True})
        if direction == "down" and idx == len(ids) - 1:
            return JSONResponse({"ok": True})

        swap_idx = idx - 1 if direction == "up" else idx + 1
        async with conn.transaction():
            for i, r in enumerate(rows):
                await conn.execute("UPDATE categories SET sort_order=$1 WHERE id=$2", i + 1, r["id"])
            await conn.execute("UPDATE categories SET sort_order=$1 WHERE id=$2", swap_idx + 1, cat_id)
            await conn.execute("UPDATE categories SET sort_order=$1 WHERE id=$2", idx + 1, ids[swap_idx])

    return JSONResponse({"ok": True})


@app.post("/api/service/move")
async def move_service(request: Request):
    if not request.session.get("username"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = await request.json()
    service_id = int(data["id"])
    direction = data["direction"]

    async with db.pool.acquire() as conn:
        svc = await conn.fetchrow(
            "SELECT id, category_id, parent_id FROM services WHERE id=$1", service_id
        )
        if not svc:
            return JSONResponse({"error": "not found"}, status_code=404)

        siblings = await conn.fetch(
            """SELECT id FROM services
               WHERE category_id=$1 AND parent_id IS NOT DISTINCT FROM $2
               ORDER BY sort_order NULLS LAST, id""",
            svc["category_id"], svc["parent_id"],
        )
        ids = [s["id"] for s in siblings]
        idx = ids.index(service_id)

        if direction == "up" and idx == 0:
            return JSONResponse({"ok": True})
        if direction == "down" and idx == len(ids) - 1:
            return JSONResponse({"ok": True})

        swap_idx = idx - 1 if direction == "up" else idx + 1
        async with conn.transaction():
            for i, s in enumerate(siblings):
                await conn.execute("UPDATE services SET sort_order=$1 WHERE id=$2", i + 1, s["id"])
            await conn.execute("UPDATE services SET sort_order=$1 WHERE id=$2", swap_idx + 1, service_id)
            await conn.execute("UPDATE services SET sort_order=$1 WHERE id=$2", idx + 1, ids[swap_idx])

    return JSONResponse({"ok": True})
