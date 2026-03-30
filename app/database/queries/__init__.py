"""Re-export all query functions for backward compatibility."""

from app.database.queries.services import (
    get_services_by_type,
    get_child_services,
    get_services_for_ai,
    get_service_by_id,
    get_info_pages,
    get_info_page_by_id,
)
from app.database.queries.users import (
    upsert_user,
    get_all_active_user_ids,
    get_menu_message_id,
    set_menu_message_id,
)
from app.database.queries.settings import (
    get_setting,
    get_entry_tariff,
    get_blocked_dates,
    get_blocked_weekdays,
    create_inquiry,
)
from app.database.queries.cart import (
    cart_add,
    cart_get,
    cart_remove,
    cart_clear,
)
from app.database.queries.bookings import (
    get_booking_by_id,
    update_booking_status,
    get_user_bookings,
    get_booking_items_for_bookings,
    create_booking,
    create_booking_items,
    get_booking_items,
    create_change_request,
    create_change_items,
    get_change_request,
    get_change_items,
    get_pending_change_for_booking,
    update_change_request_status,
    apply_change_request,
    get_stats,
    get_bookings_in_range,
    get_bookings_new,
)
from app.database.queries.ai import (
    get_ai_qa_pairs,
    get_ai_history,
    append_ai_history,
    clear_ai_history,
    get_ai_history_last_age_hours,
    trim_ai_history,
    log_ai_usage,
    get_ai_usage_stats,
)

__all__ = [
    "get_services_by_type", "get_child_services", "get_services_for_ai", "get_service_by_id",
    "get_info_pages", "get_info_page_by_id",
    "upsert_user", "get_all_active_user_ids", "get_menu_message_id", "set_menu_message_id",
    "get_setting", "get_entry_tariff", "get_blocked_dates", "get_blocked_weekdays", "create_inquiry",
    "cart_add", "cart_get", "cart_remove", "cart_clear",
    "get_booking_by_id", "update_booking_status", "get_user_bookings", "get_booking_items_for_bookings",
    "create_booking", "create_booking_items", "get_booking_items",
    "create_change_request", "create_change_items", "get_change_request", "get_change_items",
    "get_pending_change_for_booking", "update_change_request_status", "apply_change_request",
    "get_stats", "get_bookings_in_range", "get_bookings_new",
    "get_ai_qa_pairs", "get_ai_history", "append_ai_history", "clear_ai_history",
    "get_ai_history_last_age_hours", "trim_ai_history", "log_ai_usage", "get_ai_usage_stats",
]
