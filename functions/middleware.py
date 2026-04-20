from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config import OWNER_IDS
import database.db as db


class MaintenanceMiddleware(BaseMiddleware):

    async def __call__(self, handler, event, data):

        user = event.from_user

        if not user:
            return await handler(event, data)

        if user.id in OWNER_IDS:
            return await handler(event, data)

        mode = await db.get_setting("maintenance", "off")

        if mode == "on":

            if isinstance(event, Message):
                await event.answer(
                    "⚙️ Bot under maintenance.\n\nTry again later."
                )

            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Bot under maintenance",
                    show_alert=True
                )

            return

        return await handler(event, data)
