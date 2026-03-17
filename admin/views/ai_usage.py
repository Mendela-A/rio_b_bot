import logging

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.views import CustomView

import db
from shared import templates as _templates

logger = logging.getLogger(__name__)

_DEFAULT_NO_ANSWER_PHRASE = "немає цієї інформації"

# USD за 1M токенів: (input, output)
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-3-haiku-20240307":    (0.25,  1.25),
    "claude-haiku-4-5-20251001":  (0.80,  4.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
}
_DEFAULT_PRICES = (0.80, 4.00)


def _calc_cost(inp: int, out: int, prices: tuple[float, float]) -> float:
    return (inp * prices[0] + out * prices[1]) / 1_000_000


class AiUsageView(CustomView):
    def __init__(self) -> None:
        super().__init__(
            label="Аналітика",
            icon="fa fa-chart-bar",
            path="/ai-usage",
            methods=["GET"],
            name="ai_usage",
        )

    async def render(self, request: Request, templates) -> Response:  # noqa: ARG002
        async with db.pool.acquire() as conn:
            settings_rows = await conn.fetch(
                "SELECT key, value FROM settings WHERE key = ANY($1::text[])",
                ["ai_no_answer_phrase", "ai_model"],
            )
            settings = {r["key"]: r["value"] for r in settings_rows}
            no_answer_phrase = f"%{settings.get('ai_no_answer_phrase', _DEFAULT_NO_ANSWER_PHRASE)}%"
            current_model = settings.get("ai_model", "claude-haiku-4-5-20251001")
            prices = _MODEL_PRICES.get(current_model)
            if prices is None:
                logger.warning("Unknown ai_model in settings: %r, using default prices", current_model)
                prices = _DEFAULT_PRICES

            # --- Токени ---
            summary_row = await conn.fetchrow(
                "SELECT SUM(input_tokens) AS total_in, SUM(output_tokens) AS total_out, "
                "COUNT(*) AS total_requests, "
                "SUM(cache_write_tokens) AS total_cache_write, SUM(cache_read_tokens) AS total_cache_read, "
                "COUNT(DISTINCT telegram_id) AS unique_users, "
                "AVG(response_ms) AS avg_response_ms "
                "FROM ai_usage_log"
            )
            daily_rows = await conn.fetch(
                "SELECT DATE(created_at) AS day, SUM(input_tokens) AS inp, SUM(output_tokens) AS out, "
                "SUM(cache_write_tokens) AS cache_write, SUM(cache_read_tokens) AS cache_read, "
                "AVG(response_ms) AS avg_ms "
                "FROM ai_usage_log GROUP BY day ORDER BY day DESC LIMIT 14"
            )

            # --- Топ запитань ---
            top_questions = await conn.fetch(
                "SELECT content, COUNT(*) AS cnt "
                "FROM ai_chat_history WHERE role = 'user' "
                "GROUP BY content ORDER BY cnt DESC LIMIT 30"
            )

            # --- Запитання без відповіді ---
            # Шукаємо assistant-повідомлення з фразою "немає цієї інформації"
            # і дістаємо user-повідомлення, що передували їм
            unanswered = await conn.fetch(
                """
                SELECT DISTINCT ON (h_user.content)
                    h_user.content      AS question,
                    h_user.telegram_id,
                    h_assistant.created_at
                FROM ai_chat_history h_assistant
                JOIN LATERAL (
                    SELECT content, telegram_id
                    FROM ai_chat_history
                    WHERE telegram_id = h_assistant.telegram_id
                      AND role = 'user'
                      AND created_at < h_assistant.created_at
                    ORDER BY created_at DESC
                    LIMIT 1
                ) h_user ON true
                WHERE h_assistant.role = 'assistant'
                  AND h_assistant.content ILIKE $1
                ORDER BY h_user.content, h_assistant.created_at DESC
                LIMIT 50
                """,
                no_answer_phrase,
            )

        total_in = int(summary_row["total_in"] or 0)
        total_out = int(summary_row["total_out"] or 0)
        total_requests = int(summary_row["total_requests"] or 0)
        total_cache_write = int(summary_row["total_cache_write"] or 0)
        total_cache_read = int(summary_row["total_cache_read"] or 0)
        unique_users = int(summary_row["unique_users"] or 0)
        avg_response_ms = int(summary_row["avg_response_ms"]) if summary_row["avg_response_ms"] is not None else None
        total_cost = _calc_cost(total_in, total_out, prices)

        cache_total = total_cache_write + total_cache_read
        cache_hit_rate = (total_cache_read / cache_total * 100) if cache_total > 0 else 0.0
        # Cache read costs 10% of input price — 90% savings per cached token
        cache_savings = total_cache_read * prices[0] * 0.9 / 1_000_000

        daily = []
        for r in daily_rows:
            inp = int(r["inp"] or 0)
            out = int(r["out"] or 0)
            cw = int(r["cache_write"] or 0)
            cr = int(r["cache_read"] or 0)
            avg_ms = int(r["avg_ms"]) if r["avg_ms"] is not None else None
            daily.append({
                "day": r["day"],
                "inp": inp,
                "out": out,
                "cache_write": cw,
                "cache_read": cr,
                "total_tokens": inp + out,
                "cost": _calc_cost(inp, out, prices),
                "avg_ms": avg_ms,
            })

        return _templates.TemplateResponse(
            "ai_usage.html",
            {
                "request": request,
                "total_in": total_in,
                "total_out": total_out,
                "total_requests": total_requests,
                "unique_users": unique_users,
                "avg_response_ms": avg_response_ms,
                "total_cache_write": total_cache_write,
                "total_cache_read": total_cache_read,
                "cache_hit_rate": cache_hit_rate,
                "cache_savings": cache_savings,
                "total_cost": total_cost,
                "daily": daily,
                "top_questions": [dict(r) for r in top_questions],
                "unanswered": [dict(r) for r in unanswered],
                "current_model": current_model,
                "price_in": prices[0],
                "price_out": prices[1],
            },
        )
