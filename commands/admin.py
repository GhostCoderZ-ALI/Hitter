from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode

import database.db as db
from config import OWNER_IDS

router = Router()


def is_owner(uid: int):
    return uid in OWNER_IDS


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton(text="🎟 Generate Code", callback_data="admin_code")
        ],
        [
            InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban"),
            InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
        ]
    ])


@router.message(Command("admin"))
async def admin_panel(msg: Message):

    if not is_owner(msg.from_user.id):
        return

    text = """
👑 ADMIN PANEL

Select an action below.
"""

    await msg.answer(text, reply_markup=admin_kb(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin_stats")
async def admin_stats(query: CallbackQuery):

    stats = await db.get_global_stats()

    text = f"""
📊 BOT STATS

Users: {stats['users']}
Checks: {stats['checks']}
Charged: {stats['charged']}
Live: {stats['live']}
Banned: {stats['banned']}
Codes: {stats['active_codes']}
"""

    await query.message.edit_text(text, reply_markup=admin_kb())
    await query.answer()


@router.callback_query(F.data == "admin_code")
async def admin_code(query: CallbackQuery):

    text = """
🎟 Generate Redeem Code

Send command:

/gencode plan days hits uses

Example:
/gencode vip 7 100 10
"""

    await query.message.edit_text(text, reply_markup=admin_kb())
    await query.answer()


@router.message(Command("gencode"))
async def gencode(msg: Message):

    if not is_owner(msg.from_user.id):
        return

    try:
        args = msg.text.split()

        plan = args[1]
        days = int(args[2])
        hits = int(args[3])
        uses = int(args[4])

    except:
        await msg.answer("Usage:\n/gencode PLAN DAYS HITS USES")
        return

    code = await db.create_redeem_code(plan, days, hits, uses, msg.from_user.id)

    await msg.answer(f"🎟 Code Generated:\n<code>{code}</code>", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin_ban")
async def admin_ban(query: CallbackQuery):

    text = """
🚫 Ban User

Send command:

/ban USER_ID
"""

    await query.message.edit_text(text, reply_markup=admin_kb())
    await query.answer()


@router.message(Command("ban"))
async def ban_user(msg: Message):

    if not is_owner(msg.from_user.id):
        return

    try:
        user_id = int(msg.text.split()[1])
    except:
        await msg.answer("Usage:\n/ban USER_ID")
        return

    await db.ban_user(user_id)

    await msg.answer("User banned.")


@router.callback_query(F.data == "admin_unban")
async def admin_unban(query: CallbackQuery):

    text = """
✅ Unban User

Send command:

/unban USER_ID
"""

    await query.message.edit_text(text, reply_markup=admin_kb())
    await query.answer()


@router.message(Command("unban"))
async def unban_user(msg: Message):

    if not is_owner(msg.from_user.id):
        return

    try:
        user_id = int(msg.text.split()[1])
    except:
        await msg.answer("Usage:\n/unban USER_ID")
        return

    await db.unban_user(user_id)

    await msg.answer("User unbanned.")


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(query: CallbackQuery):

    text = """
📢 Broadcast Message

Send:

/broadcast your message
"""

    await query.message.edit_text(text, reply_markup=admin_kb())
    await query.answer()


@router.message(Command("broadcast"))
async def broadcast(msg: Message):

    if not is_owner(msg.from_user.id):
        return

    try:
        text = msg.text.split(" ",1)[1]
    except:
        await msg.answer("Usage:\n/broadcast message")
        return

    users = await db.get_all_user_ids()

    sent = 0

    for u in users:
        try:
            await msg.bot.send_message(u, text)
            sent += 1
        except:
            pass

    await msg.answer(f"Broadcast sent to {sent} users")
