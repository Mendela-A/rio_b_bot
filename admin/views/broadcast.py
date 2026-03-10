import asyncio
import io
import logging
import os
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette_admin.views import CustomView

import db
from shared import templates as _templates, MAX_IMAGE_WIDTH, IMAGE_QUALITY, MAX_UPLOAD_SIZE

logger = logging.getLogger(__name__)

UPLOADS_DIR = Path("/app/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


_MENU_KEYBOARD = {
    "inline_keyboard": [[{"text": "🏠 Головне меню", "callback_data": "main_menu"}]]
}


async def _send_one(client: httpx.AsyncClient, bot_token: str, uid: int, text: str, photo_url: str | None, base_url: str) -> None:
    if photo_url:
        full_url = base_url.rstrip("/") + photo_url if photo_url.startswith("/") else photo_url
        resp = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            json={"chat_id": uid, "photo": full_url, "caption": text, "parse_mode": "HTML", "reply_markup": _MENU_KEYBOARD},
            timeout=10,
        )
    else:
        resp = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": uid, "text": text, "parse_mode": "HTML", "reply_markup": _MENU_KEYBOARD},
            timeout=10,
        )

    if resp.status_code == 403:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_active = FALSE WHERE telegram_id = $1", uid
            )
        raise RuntimeError("bot_blocked")

    resp.raise_for_status()


async def _do_broadcast(broadcast_id: int, text: str, photo_url: str | None, base_url: str) -> None:
    bot_token = os.getenv("BOT_TOKEN", "")
    sent = 0
    failed = 0

    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id FROM users WHERE is_active = TRUE")
        user_ids = [r["telegram_id"] for r in rows]

        async with httpx.AsyncClient() as client:
            for batch in _chunks(user_ids, 25):
                tasks = [_send_one(client, bot_token, uid, text, photo_url, base_url) for uid in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, Exception):
                        failed += 1
                    else:
                        sent += 1
                if len(user_ids) > 25:
                    await asyncio.sleep(1)

        status = "done"
    except Exception:
        status = "failed"

    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE broadcasts
            SET status = $1, sent_count = $2, failed_count = $3, finished_at = NOW()
            WHERE id = $4
            """,
            status, sent, failed, broadcast_id,
        )


class BroadcastView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Розсилка",
            icon="fa fa-bullhorn",
            path="/broadcast",
            methods=["GET", "POST"],
            name="broadcast",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        if request.method == "POST":
            return await self._handle_post(request)
        return await self._render_page(request)

    async def _render_page(self, request: Request) -> Response:
        async with db.pool.acquire() as conn:
            user_count = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_active = TRUE"
            )
            broadcasts = await conn.fetch(
                "SELECT id, text, photo_url, status, sent_count, failed_count, created_at, finished_at "
                "FROM broadcasts ORDER BY created_at DESC LIMIT 20"
            )
            users = await conn.fetch(
                "SELECT telegram_id, first_name, username, last_seen_at, created_at "
                "FROM users WHERE is_active = TRUE "
                "ORDER BY last_seen_at DESC"
            )

        started = request.query_params.get("started") == "1"
        return _templates.TemplateResponse(
            "broadcast.html",
            {
                "request": request,
                "user_count": user_count,
                "broadcasts": [dict(b) for b in broadcasts],
                "users": [dict(u) for u in users],
                "started": started,
            },
        )

    async def _handle_post(self, request: Request) -> Response:
        form = await request.form()
        text = (form.get("text") or "").strip()
        if not text:
            return RedirectResponse("/admin/broadcast", status_code=303)

        # Handle optional photo upload
        photo_url = None
        photo_file = form.get("photo")
        if photo_file and hasattr(photo_file, "filename") and photo_file.filename:
            contents = await photo_file.read()
            if contents:
                if len(contents) > MAX_UPLOAD_SIZE:
                    logger.warning("Broadcast photo too large (%d bytes), skipping", len(contents))
                else:
                    try:
                        img = Image.open(io.BytesIO(contents))
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        if img.width > MAX_IMAGE_WIDTH:
                            ratio = MAX_IMAGE_WIDTH / img.width
                            img = img.resize((MAX_IMAGE_WIDTH, int(img.height * ratio)), Image.LANCZOS)
                        filename = uuid4().hex + ".webp"
                        img.save(str(UPLOADS_DIR / filename), "WEBP", quality=IMAGE_QUALITY)
                        photo_url = f"/uploads/{filename}"
                    except Exception:
                        logger.exception("Failed to process broadcast photo")

        async with db.pool.acquire() as conn:
            broadcast_id = await conn.fetchval(
                "INSERT INTO broadcasts (text, photo_url, status) VALUES ($1, $2, 'running') RETURNING id",
                text, photo_url,
            )

        base_url = os.getenv("ADMIN_BASE_URL", "")
        task = BackgroundTask(_do_broadcast, broadcast_id, text, photo_url, base_url)
        return RedirectResponse("/admin/broadcast?started=1", status_code=303, background=task)
