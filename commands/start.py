"""Home screen, settings, help, credits, redeem, myhits, ping (premium theme, same logic)"""
import time
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject

import database.db as db
from config import (
    OWNER_IDS, FREE_DAILY_LIMIT, BOT_NAME, BOT_USERNAME,
    PLAN_PRICES, SUPPORT_USERNAME, OWNER_USERNAME
)
from functions.emojis import EMOJI, EMOJI_PLAIN

_bot_start_time = time.time()

router = Router()

NO_PREVIEW = {"is_disabled": True}

def _kb(*rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
            for row in rows
        ]
    )


async def _home_screen(target, user, edit=False):
    uid = user.id
    plan = await db.get_user_plan(uid)

    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited"
        plan_line = f"{EMOJI['charged']} <b>{plan['label']}</b> • {hpd_str} • Exp {plan['expiry']}"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        plan_line = f"{EMOJI['free']} <b>Free Plan</b> • {hits}/{FREE_DAILY_LIMIT} hits ({remaining} left)"

    fname = user.first_name or "User"

    text = (
        f"╭━━━ {EMOJI['welcome']} <b>{BOT_NAME}</b>\n\n"
        f"👤 <b>User:</b> {fname}\n"
        f"💳 <b>Plan:</b> {plan_line}\n\n"
        f"⚡ Tap <b>Start Checking</b> to see hit instructions.\n"
        f"╰━━━━━━━━━━━━"
    )

    rows = [
        [("⚡ Start Checking", "home_help"), ("💳 Credits", "home_credits")],
        [("📊 My Hits", "home_myhits"), ("⚙ Settings", "home_settings")],
        [("🏆 Ranking", "home_ranking"), ("💾 Saved BINs", "home_bins")],
        [("📞 Contact Support", "home_contact")],
    ]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
            for row in rows
        ]
    )

    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.message(Command("start", prefix="/."))
async def cmd_start(msg: Message):
    uid = msg.from_user.id
    await db.upsert_user(uid, msg.from_user.username, msg.from_user.first_name)
    if await db.is_banned(uid):
        await msg.answer(f"{EMOJI['ban']} <b>You are banned.</b>", parse_mode=ParseMode.HTML)
        return
    await _home_screen(msg, msg.from_user)


@router.callback_query(F.data == "home_main")
async def cb_home_main(query: CallbackQuery):
    await _home_screen(query.message, query.from_user, edit=True)
    await query.answer()


@router.callback_query(F.data == "home_help")
async def cb_home_help(query: CallbackQuery):
    text = (
        f"╭━━━ {EMOJI['bolt']} <b>HIT COMMAND GUIDE</b>\n\n"
        f"<b>Single card:</b>\n"
        f"<code>/hit &lt;url&gt; cc|mm|yy|cvv</code>\n\n"
        f"<b>Multiple cards:</b>\n"
        f"<code>/hit &lt;url&gt;</code>\n"
        f"<code>cc1|mm|yy|cvv</code>\n"
        f"<code>cc2|mm|yy|cvv</code>\n\n"
        f"<b>Auto-generate from BIN:</b>\n"
        f"<code>/hit &lt;url&gt; bin6+</code>\n\n"
        f"<b>From file:</b>\n"
        f"Reply to a .txt file with\n"
        f"<code>/hit &lt;url&gt;</code>\n\n"
        f"━━━ {EMOJI['search']} <b>TOOLS</b>\n"
        f"<code>/gen &lt;bin&gt; [count]</code> — Generate cards\n"
        f"<code>/bin &lt;bin6&gt;</code> — BIN lookup\n"
        f"<code>/myhits</code> — Your hit history\n"
        f"<code>/redeem &lt;code&gt;</code> — Redeem access code\n"
        f"╰━━━━━━━━━━━━"
    )
    kb = _kb([("⬅ Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_credits")
async def cb_home_credits(query: CallbackQuery):
    uid = query.from_user.id
    plan = await db.get_user_plan(uid)

    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else f"Unlimited {EMOJI['infinity']}"
        text = (
            f"╭━━━ {EMOJI['card']} <b>CREDITS</b>\n\n"
            f"Plan → <b>{plan['label']}</b>\n"
            f"Hits → {hpd_str}\n"
            f"Expires → {plan['expiry']}\n"
            f"╰━━━━━━━━━━━━"
        )
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        text = (
            f"╭━━━ {EMOJI['card']} <b>CREDITS</b>\n\n"
            f"Plan → Free\n"
            f"Hits → {hits}/{FREE_DAILY_LIMIT} ({remaining} left)\n\n"
            f"<i>Contact {OWNER_USERNAME} for premium.</i>\n"
            f"╰━━━━━━━━━━━━"
        )

    kb = _kb([("⬅ Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.message(Command("myhits", prefix="/."))
async def cmd_myhits(msg: Message):
    await _show_myhits(msg, msg.from_user.id)


@router.callback_query(F.data == "home_myhits")
async def cb_home_myhits(query: CallbackQuery):
    await _show_myhits(query.message, query.from_user.id, edit=True)
    await query.answer()


async def _show_myhits(target, uid, edit=False):
    logs = await db.get_user_logs(uid, limit=20)
    stats = await db.get_user_hit_stats(uid)

    header = (
        f"╭━━━ {EMOJI['stats']} <b>MY HITS</b>\n\n"
        f"Total → <code>{stats['total']}</code>\n"
        f"Charged → <code>{stats['charged']}</code>\n"
        f"╰━━━━━━━━━━━━\n"
    )

    if logs:
        lines = []
        for h in logs[:10]:
            amt = h.get('amount', '?')
            merchant = h.get('merchant', '?')
            lines.append(f"{EMOJI['charged']} <code>{merchant}</code> • {amt}")
        text = header + "\n".join(lines)
    else:
        text = header + "\n<i>No hits yet.</i>"

    kb = _kb([("⬅ Back", "home_main")])

    if edit:
        await target.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await target.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "home_settings")
async def cb_home_settings(query: CallbackQuery):
    await _show_settings(query)


async def _show_settings(query: CallbackQuery):
    uid = query.from_user.id
    proxy_mode = await db.get_user_proxy_mode(uid)
    user_proxies = await db.get_proxies(uid)
    sys_proxy = await db.get_setting("system_proxy", None)

    if proxy_mode == "own":
        mode_text = "🟢 Own Proxy"
        toggle_btn = ("Switch to System Proxy", "settings_proxy_system")
    else:
        mode_text = "🔵 System Proxy"
        toggle_btn = ("Switch to Own Proxy", "settings_proxy_own")

    sys_status = f"<code>{sys_proxy[:25]}...</code>" if sys_proxy else "Hosting IP"
    proxy_list = "\n".join(f"<code>{p}</code>" for p in user_proxies[:3]) if user_proxies else "<i>None</i>"

    text = (
        f"╭━━━ ⚙ <b>SETTINGS</b>\n\n"
        f"Proxy Mode → {mode_text}\n"
        f"System → {sys_status}\n\n"
        f"<b>Your Proxies</b>\n{proxy_list}\n\n"
        f"<code>/proxy add host:port:user:pass</code>\n"
        f"<code>/proxy test</code>\n"
        f"╰━━━━━━━━━━━━"
    )

    kb = _kb([toggle_btn], [("⬅ Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "settings_proxy_own")
async def cb_settings_proxy_own(query: CallbackQuery):
    uid = query.from_user.id
    user_proxies = await db.get_proxies(uid)
    if not user_proxies:
        await query.answer("Add a proxy first with /proxy add", show_alert=True)
        return
    await db.set_user_proxy_mode(uid, "own")
    await _show_settings(query)


@router.callback_query(F.data == "settings_proxy_system")
async def cb_settings_proxy_system(query: CallbackQuery):
    await db.set_user_proxy_mode(query.from_user.id, "system")
    await _show_settings(query)


@router.callback_query(F.data == "home_contact")
async def cb_home_contact(query: CallbackQuery):
    text = f"📞 <b>Support</b>\n\nOwner → {OWNER_USERNAME}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Message Owner", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="⬅ Back", callback_data="home_main")]
    ])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()
