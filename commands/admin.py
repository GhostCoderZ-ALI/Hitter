from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

import database.db as db
from config import OWNER_IDS

router = Router()


async def is_admin(uid):

    if uid in OWNER_IDS:
        return True

    return await db.is_admin(uid)


# ADMIN PANEL

@router.message(Command("admin"))
async def admin_panel(msg: Message):

    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Only admins can access admin panel.")
        return

    text = """
👑 ADMIN CONTROL PANEL

User Management
/ban
/unban
/user
/users

Admin Management
/addadmin
/removeadmin
/admins

Plans
/setplan
/upgrade
/gencode
/codes
/revoke

Bot
/stats
/broadcast
/resetstats
/maintenance

System
/whoami
"""

    await msg.answer(text)


# WHOAMI

@router.message(Command("whoami"))
async def whoami(msg: Message):

    uid = msg.from_user.id

    if await is_admin(uid):

        await msg.answer(
            "👑 Admin detected.\n\n"
            "Plans are for mortals.\n"
            "You are above this system."
        )

    else:

        await msg.answer("User role detected.")


# ADD ADMIN

@router.message(Command("addadmin"))
async def add_admin(msg: Message):

    if msg.from_user.id not in OWNER_IDS:
        return

    try:
        uid = int(msg.text.split()[1])
    except:
        await msg.answer("Usage: /addadmin USER_ID")
        return

    await db.add_admin(uid)

    await msg.answer("Admin added.")


# REMOVE ADMIN

@router.message(Command("removeadmin"))
async def remove_admin(msg: Message):

    if msg.from_user.id not in OWNER_IDS:
        return

    try:
        uid = int(msg.text.split()[1])
    except:
        await msg.answer("Usage: /removeadmin USER_ID")
        return

    await db.remove_admin(uid)

    await msg.answer("Admin removed.")


# LIST ADMINS

@router.message(Command("admins"))
async def admins(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    admins = await db.get_all_admins()

    text = "👑 ADMINS\n\n"

    for a in admins:
        text += f"{a}\n"

    await msg.answer(text)


# BAN

@router.message(Command("ban"))
async def ban(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    if msg.reply_to_message:
        uid = msg.reply_to_message.from_user.id
    else:
        try:
            uid = int(msg.text.split()[1])
        except:
            await msg.answer("Usage: /ban USER_ID or reply")
            return

    await db.ban_user(uid)

    await msg.answer("User banned.")


# UNBAN

@router.message(Command("unban"))
async def unban(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    try:
        uid = int(msg.text.split()[1])
    except:
        await msg.answer("Usage: /unban USER_ID")
        return

    await db.unban_user(uid)

    await msg.answer("User unbanned.")


# USER INFO

@router.message(Command("user"))
async def user(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    try:
        uid = int(msg.text.split()[1])
    except:
        await msg.answer("Usage: /user USER_ID")
        return

    info = await db.get_user_info(uid)

    if not info:
        await msg.answer("User not found.")
        return

    await msg.answer(str(info))


# GLOBAL STATS

@router.message(Command("stats"))
async def stats(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    s = await db.get_global_stats()

    text = f"""
BOT STATS

Users: {s['users']}
Checks: {s['checks']}
Charged: {s['charged']}
Live: {s['live']}
Banned: {s['banned']}
Codes: {s['active_codes']}
"""

    await msg.answer(text)


# RESET STATS

@router.message(Command("resetstats"))
async def resetstats(msg: Message):

    if msg.from_user.id not in OWNER_IDS:
        return

    await db.reset_global_stats()

    await msg.answer("Stats reset.")


# BROADCAST

@router.message(Command("broadcast"))
async def broadcast(msg: Message):

    if not await is_admin(msg.from_user.id):
        return

    try:
        text = msg.text.split(" ",1)[1]
    except:
        await msg.answer("Usage: /broadcast message")
        return

    users = await db.get_all_user_ids()

    sent = 0

    for u in users:

        try:
            await msg.bot.send_message(u, text)
            sent += 1
        except:
            pass

    await msg.answer(f"Broadcast sent to {sent} users.")


# MAINTENANCE

@router.message(Command("maintenance"))
async def maintenance(msg: Message):

    if msg.from_user.id not in OWNER_IDS:
        return

    try:
        mode = msg.text.split()[1]
    except:
        await msg.answer("Usage: /maintenance on/off")
        return

    if mode not in ["on","off"]:
        await msg.answer("Use on/off")
        return

    await db.set_setting("maintenance", mode)

    await msg.answer(f"Maintenance → {mode}")@router.callback_query(F.data == "admin_code")
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
