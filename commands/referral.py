from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("ref"))
async def ref(msg: Message):

    bot = await msg.bot.get_me()

    link = f"https://t.me/{bot.username}?start={msg.from_user.id}"

    await msg.answer(
        f"👥 Referral Link\n\n{link}\n\nReward: 1 credit per user"
    )
