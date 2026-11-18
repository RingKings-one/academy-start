import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery

logger = logging.getLogger("callback")


class CallbackLogMiddleware(BaseMiddleware):
    """
    Только логирование callback_data.
    answer() намеренно НЕ вызываем здесь —
    отвечаем в хендлерах (чтобы можно было show_alert / текст).
    """

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("user")
        user_id = user.telegram_id if user else event.from_user.id
        logger.info(
            "callback | user=%s | data=%s",
            user_id,
            event.data,
        )
        return await handler(event, data)
