"""Home screen, settings, help, credits, redeem, myhits, ping"""
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
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows])


async def _home_screen(target, user, edit=False):
    uid = user.id
    plan = await db.get_user_plan(uid)

    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited"
        plan_line = f"{EMOJI['charged']} <b>{plan['label']}</b> - {hpd_str} - Exp {plan['expiry']}"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        plan_line = f"{EMOJI['free']} <b>Free Plan</b> - {hits}/{FREE_DAILY_LIMIT} hits ({remaining} left)"

    fname = user.first_name or "User"
    text = (
        f"「 {EMOJI['welcome']} Welcome - {BOT_NAME} 」\n\n"
        f"Hey, <b>{fname}</b>!\n"
        f"{plan_line}\n\n"
        f"<i>Use /hit to start checking cards.</i>"
    )

    rows = [
        [(f"{EMOJI_PLAIN['bolt']} Hit", "home_help"), (f"{EMOJI_PLAIN['card']} Credits", "home_credits")],
        [(f"{EMOJI_PLAIN['stats']} My Hits", "home_myhits"), (f"{EMOJI_PLAIN['plug']} Settings", "home_settings")],
        [(f"{EMOJI_PLAIN['crown']} Ranking", "home_ranking"), (f"{EMOJI_PLAIN['card']} Saved BINs", "home_bins")],
        [(f"{EMOJI_PLAIN['link']} Contact", "home_contact")],
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows
    ])

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
        f"「 {EMOJI['bolt']} HIT COMMANDS 」\n\n"
        f"<b>Single card:</b>\n<code>/hit &lt;url&gt; cc|mm|yy|cvv</code>\n\n"
        f"<b>Multiple cards:</b>\n<code>/hit &lt;url&gt;</code>\n<code>cc1|mm|yy|cvv</code>\n<code>cc2|mm|yy|cvv</code>\n\n"
        f"<b>Auto-generate from BIN:</b>\n<code>/hit &lt;url&gt; bin6+</code>\n\n"
        f"<b>From file:</b>\nReply to a .txt file with <code>/hit &lt;url&gt;</code>\n\n"
        f"「 {EMOJI['search']} TOOLS 」\n\n"
        f"<code>/gen &lt;bin&gt; [count]</code> - Generate cards\n"
        f"<code>/bin &lt;bin6&gt;</code> - BIN lookup\n"
        f"<code>/myhits</code> - Your hit history\n"
        f"<code>/redeem &lt;code&gt;</code> - Redeem access code\n"
    )
    kb = _kb([(f"{EMOJI_PLAIN['back']} Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_credits")
async def cb_home_credits(query: CallbackQuery):
    uid = query.from_user.id
    plan = await db.get_user_plan(uid)
    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else f"Unlimited {EMOJI['infinity']}"
        text = f"「 {EMOJI['card']} CREDITS 」\n\nPlan -> <b>{plan['label']}</b>\nHits -> {hpd_str}\nExpires -> {plan['expiry']}"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        text = (
            f"「 {EMOJI['card']} CREDITS 」\n\n"
            f"Plan -> {EMOJI['free']} Free\nHits -> {hits}/{FREE_DAILY_LIMIT} ({remaining} left)\n\n"
            f"<i>Contact {OWNER_USERNAME} for premium access.</i>"
        )
    kb = _kb([(f"{EMOJI_PLAIN['back']} Back", "home_main")])
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
        f"「 {EMOJI['stats']} MY HITS 」\n\n"
        f"Total: <code>{stats['total']}</code> | Charged: <code>{stats['charged']}</code>\n"
    )
    if logs:
        lines = []
        for h in logs[:10]:
            amt = h.get('amount', '?')
            merchant = h.get('merchant', '?')
            lines.append(f"{EMOJI['charged']} <code>{merchant}</code> - {amt}")
        text = header + "\n" + "\n".join(lines)
    else:
        text = header + "\n<i>No hits yet.</i>"
    if len(text) > 4000:
        text = text[:3990] + "\n..."
    kb = _kb([(f"{EMOJI_PLAIN['back']} Back", "home_main")])
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
        mode_text = f"{EMOJI['charged']} <b>Own Proxy</b>"
        toggle_btn = (f"{EMOJI_PLAIN['plug']} Switch to System Proxy", "settings_proxy_system")
    else:
        mode_text = f"{EMOJI['plug']} <b>System Proxy</b>"
        toggle_btn = (f"{EMOJI_PLAIN['charged']} Switch to Own Proxy", "settings_proxy_own")

    sys_status = f"<code>{sys_proxy[:25]}...</code>" if sys_proxy else "Hosting IP"
    proxy_list = "\n".join(f"<code>{p}</code>" for p in user_proxies[:3]) if user_proxies else "<i>None</i>"

    text = (
        f"「 {EMOJI['plug']} SETTINGS 」\n\n"
        f"Proxy Mode: {mode_text}\nSystem: {sys_status}\n\n"
        f"Your Proxies:\n{proxy_list}\n\n"
        f"<code>/proxy add host:port:user:pass</code>\n"
        f"<code>/proxy test</code> - Test proxies"
    )
    kb = _kb([toggle_btn], [(f"{EMOJI_PLAIN['back']} Back", "home_main")])
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
    text = f"「 {EMOJI['link']} CONTACT 」\n\nOwner: {OWNER_USERNAME}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_PLAIN['link']} Message Owner", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text=f"{EMOJI_PLAIN['back']} Back", callback_data="home_main")],
    ])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


# ==================== UPDATED HELP COMMAND ====================
@router.message(Command("help", prefix="/."))
async def cmd_help(msg: Message):
    text = (
        f"「 ⚡️ WORKING COMMANDS 」\n\n"
        f"<code>/auth CC|MM|YY|CVV</code> - Stripe auth checker\n"
        f"<code>/sh CC|MM|YY|CVV [proxy]</code> - Shopify API checker\n\n"
        f"Contact: @hqdeven"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("redeem", prefix="/."))
async def cmd_redeem(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    code = (command.args or "").strip()
    if not code:
        await msg.answer(f"Usage: <code>/redeem YOUR-CODE-HERE</code>", parse_mode=ParseMode.HTML)
        return
    result = await db.use_redeem_code(uid, code)
    if result["success"]:
        hpd = result.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else "Unlimited"
        await msg.answer(
            f"{EMOJI['charged']} <b>Code Redeemed!</b>\nPlan: <b>{result['plan_type']}</b>\nHits: {hpd_str}\nDuration: {result['days']} days",
            parse_mode=ParseMode.HTML
        )
    else:
        await msg.answer(f"{EMOJI['declined']} {result['error']}", parse_mode=ParseMode.HTML)

@router.message(Command("credits", prefix="/."))
async def cmd_credits(msg: Message):
    uid = msg.from_user.id
    plan = await db.get_user_plan(uid)
    if plan["unlimited"]:
        hpd = plan.get("hits_per_day", 0)
        hpd_str = f"{hpd}/day" if hpd > 0 else f"Unlimited"
        text = f"Plan: <b>{plan['label']}</b> | Hits: {hpd_str} | Exp: {plan['expiry']}"
    else:
        hits = await db.get_daily_hits(uid)
        remaining = max(0, FREE_DAILY_LIMIT - hits)
        text = f"Plan: Free | Hits: {hits}/{FREE_DAILY_LIMIT} ({remaining} left)"
    await msg.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command("ping", prefix="/."))
async def cmd_ping(msg: Message):
    start = time.time()
    sent = await msg.answer(f"{EMOJI['bolt']} Pinging...", parse_mode=ParseMode.HTML)
    latency_ms = round((time.time() - start) * 1000)
    uptime_sec = int(time.time() - _bot_start_time)
    hours, rem = divmod(uptime_sec, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s"
    await sent.edit_text(f"{EMOJI['bolt']} Pong! Latency: {latency_ms}ms | Uptime: {uptime_str}", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "home_ranking")
async def cb_home_ranking(query: CallbackQuery):
    ranking = await db.get_charged_ranking(10)
    if not ranking:
        text = f"「 {EMOJI['crown']} RANKING 」\n\n<i>No charged hits yet.</i>"
    else:
        lines = []
        medals = ["1st", "2nd", "3rd"]
        for idx, r in enumerate(ranking):
            name = r.get("first_name") or r.get("username") or "?"
            count = r["charged_count"]
            pos = medals[idx] if idx < 3 else f"{idx+1}th"
            lines.append(f"<b>{pos}</b> - {name}: <code>{count}</code> charged")
        text = f"「 {EMOJI['crown']} TOP HITTERS 」\n\n" + "\n".join(lines)
    kb = _kb([(f"{EMOJI_PLAIN['back']} Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()


@router.callback_query(F.data == "home_bins")
async def cb_home_bins(query: CallbackQuery):
    uid = query.from_user.id
    bins = await db.get_saved_bins(uid)
    if not bins:
        text = f"「 {EMOJI['card']} SAVED BINS 」\n\n<i>No saved BINs.</i>\n\n<code>/savebin &lt;name&gt; &lt;bin&gt;</code>"
    else:
        lines = [f"<code>{b['name']}</code> -> <code>{b['bin_value']}</code>" for b in bins]
        text = f"「 {EMOJI['card']} SAVED BINS ({len(bins)}) 」\n\n" + "\n".join(lines) + f"\n\n<code>/delbin &lt;name&gt;</code> to remove"
    kb = _kb([(f"{EMOJI_PLAIN['back']} Back", "home_main")])
    await query.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await query.answer()

@router.message(Command("savebin", prefix="/."))
async def cmd_savebin(msg: Message, command: CommandObject):
    uid = msg.from_user.id
    args = (command.args or "").strip().split(None, 1)
    if len(args) < 2:
        await msg.answer(f"Usage: <code>/savebin &lt;name&gt; &lt;bin&gt;</code>", parse_mode=ParseMode.HTML)
        return
    ok = await db.save_bin(uid, args[0], args[1])
    if ok:
        await msg.answer(f"{EMOJI['charged']} BIN saved as <b>{args[0]}</b>.", parse_mode=ParseMode.HTML)
    else:
        await msg.answer(f"{EMOJI['declined']} Failed.", parse_mode=ParseMode.HTML)

@router.message(Command("mybins", prefix="/."))
async def cmd_mybins(msg: Message):
    uid = msg.from_user.id
    bins = await db.get_saved_bins(uid)
    if not bins:
        await msg.answer(f"<i>No saved BINs. Use /savebin.</i>", parse_mode=ParseMode.HTML)
        return
    lines = [f"<code>{b['name']}</code> -> <code>{b['bin_value']}</code>" for b in bins]
    await msg.answer(f"「 SAVED BINS 」\n\n" + "\n".join(lines), parse_mode=ParseMode.HTML)

@router.message(Command("delbin", prefix="/."))
async def cmd_delbin(msg: Message, command: CommandObject):
    name = (command.args or "").strip()
    if not name:
        await msg.answer(f"Usage: <code>/delbin &lt;name&gt;</code>", parse_mode=ParseMode.HTML)
        return
    await db.delete_saved_bin(msg.from_user.id, name)
    await msg.answer(f"{EMOJI['charged']} BIN <b>{name}</b> removed.", parse_mode=ParseMode.HTML)
