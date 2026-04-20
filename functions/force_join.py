"""Force join — disabled in this build."""
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup


async def check_force_join(bot: Bot, uid: int) -> bool:
    return True


async def force_join_keyboard(bot=None, uid=None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


FORCE_JOIN_MSG = "MADAR CHOD CHUP KAR LUND LELE MERA OM.MC "
