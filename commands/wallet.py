from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import database.db as db

router = Router()

@router.message(Command("wallet"))
async def wallet(msg: Message):

    db_conn = await db.get_db()

    row = await db_conn.wallet.find_one({"user_id": msg.from_user.id})

    credits = row["credits"] if row else 0

    await msg.answer(
        f"💰 Wallet\n\nCredits: {credits}"
    )
