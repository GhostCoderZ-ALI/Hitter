import time
from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode

import database.db as db
from functions.card_utils import parse_gen_input, generate_cards
from functions.bin_lookup import lookup_bin
from functions.force_join import check_force_join, force_join_keyboard, FORCE_JOIN_MSG
from functions.emojis import EMOJI, EMOJI_PLAIN

router = Router()


def _build_gen_text(cards, prefix, count, bin_info, elapsed_ms, display_prefix):
    """Build gen result matching reference format exactly"""
    brand = bin_info.get("brand", "")
    btype = bin_info.get("type", "")
    level = bin_info.get("category", "")
    bank = bin_info.get("bank", "")
    flag = bin_info.get("flag", "")
    country = bin_info.get("country_name", "")
    iso = bin_info.get("country_code", "")

    cards_text = "\n".join(f"<code>{c}</code>" for c in cards)

    bin_line = f"<code>{prefix[:6]}</code> — <code>{brand}</code> — <code>{btype}</code>"

    text = (
        f"「 CC GENERATOR 」\n\n"
        f"Bin → <code>{display_prefix}</code>\n"
        f"Generated → <code>{len(cards)}/{count}</code>\n\n"
        f"<b>Cards</b>\n"
        f"{cards_text}\n\n"
        f"BIN ❝ {bin_line}\n"
    )
    if level and level != "UNKNOWN":
        text += f"Product ❝ <code>{level}</code>\n"
    text += (
        f"Bank ❝ <code>{bank or '─'}</code>\n"
        f"Country ❝ {flag} <code>{country}</code> (<code>{iso}</code>)\n\n"
        f"Time ❝ <code>{elapsed_ms}ms</code>"
    )
    return text


def _regen_keyboard(prefix, mm, yy, cvv_pattern, count):
    """Regenerate + link buttons"""
    cb_data = f"regen:{prefix}:{mm}:{yy}:{cvv_pattern}:{count}"
    if len(cb_data) > 64:
        cb_data = cb_data[:64]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI_PLAIN['regenerate']} Regenerate", callback_data=cb_data)],
    ])


@router.message(Command("gen", prefix="/."))
async def cmd_gen(msg: Message, command: CommandObject, bot: Bot):
    uid = msg.from_user.id
    await db.upsert_user(uid, msg.from_user.username, msg.from_user.first_name)

    if await db.is_banned(uid):
        return

    if not await check_force_join(bot, uid):
        kb = await force_join_keyboard()
        await msg.answer(FORCE_JOIN_MSG, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    args = (command.args or "").strip()
    if not args:
        await msg.answer(
            "「 CC GENERATOR 」\n\n"
            "Usage: <code>/gen &lt;bin&gt;[|mm|yy|cvv] [count]</code>\n\n"
            "Examples:\n"
            "<code>/gen 415920</code>\n"
            "<code>/gen 415920|xx|26|xxx 20</code>\n"
            "<code>/gen 374155|12|xx|xxxx 5</code>\n\n"
            "<i>x = random. Max 50 cards.</i>",
            parse_mode=ParseMode.HTML
        )
        return

    parsed = parse_gen_input(args)
    if not parsed:
        await msg.answer(
            f"{EMOJI['declined']} Invalid format.\nUsage: <code>/gen &lt;bin6+&gt;[|mm|yy|cvv] [count]</code>",
            parse_mode=ParseMode.HTML
        )
        return

    prefix, mm, yy, cvv_pattern, count = parsed
    t0 = time.perf_counter()
    cards = generate_cards(prefix, mm, yy, cvv_pattern, count)
    bin_info = await lookup_bin(prefix)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    if not cards:
        await msg.answer(f"{EMOJI['declined']} Failed to generate cards.", parse_mode=ParseMode.HTML)
        return

    is_amex = prefix.startswith("34") or prefix.startswith("37")
    card_len = 15 if is_amex else 16
    display_prefix = prefix + "x" * (card_len - len(prefix))

    text = _build_gen_text(cards, prefix, count, bin_info, elapsed_ms, display_prefix)
    kb = _regen_keyboard(prefix, mm, yy, cvv_pattern, count)
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)


@router.callback_query(lambda c: c.data and c.data.startswith("regen:"))
async def on_regen(callback: CallbackQuery, bot: Bot):
    """Regenerate fresh cards in same message"""
    try:
        parts = callback.data.split(":")
        if len(parts) < 6:
            await callback.answer("❌ Invalid data", show_alert=True)
            return

        prefix, mm, yy, cvv_pattern = parts[1], parts[2], parts[3], parts[4]
        count = int(parts[5])

        t0 = time.perf_counter()
        cards = generate_cards(prefix, mm, yy, cvv_pattern, count)
        bin_info = await lookup_bin(prefix)
        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        if not cards:
            await callback.answer("❌ Failed", show_alert=True)
            return

        is_amex = prefix.startswith("34") or prefix.startswith("37")
        card_len = 15 if is_amex else 16
        display_prefix = prefix + "x" * (card_len - len(prefix))

        text = _build_gen_text(cards, prefix, count, bin_info, elapsed_ms, display_prefix)
        kb = _regen_keyboard(prefix, mm, yy, cvv_pattern, count)

        await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        await callback.answer("🔄 Regenerated!")
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:40]}", show_alert=True)


@router.message(Command("bin", prefix="/."))
async def cmd_bin(msg: Message, command: CommandObject, bot: Bot):
    uid = msg.from_user.id
    await db.upsert_user(uid, msg.from_user.username, msg.from_user.first_name)

    if await db.is_banned(uid):
        return

    if not await check_force_join(bot, uid):
        kb = await force_join_keyboard()
        await msg.answer(FORCE_JOIN_MSG, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    args = (command.args or "").strip()
    if not args or not args.replace(" ", "").isdigit() or len(args.replace(" ", "")) < 6:
        await msg.answer(
            "「 BIN LOOKUP 」\n\n"
            "Usage: <code>/bin &lt;6+ digit BIN&gt;</code>\n"
            "Example: <code>/bin 415920</code>",
            parse_mode=ParseMode.HTML
        )
        return

    t0 = time.perf_counter()
    bin_info = await lookup_bin(args)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    brand = bin_info.get("brand", "")
    btype = bin_info.get("type", "")
    level = bin_info.get("category", "")
    bank = bin_info.get("bank", "")
    flag = bin_info.get("flag", "")
    country = bin_info.get("country_name", "")
    iso = bin_info.get("country_code", "")

    bin_line = f"<code>{args[:6]}</code> — <code>{brand}</code> — <code>{btype}</code>"

    text = (
        f"「 BIN LOOKUP 」\n\n"
        f"BIN ❝ {bin_line}\n"
    )
    if level and level != "UNKNOWN":
        text += f"Product ❝ <code>{level}</code>\n"
    text += (
        f"Bank ❝ <code>{bank or '─'}</code>\n"
        f"Country ❝ {flag} <code>{country}</code> (<code>{iso}</code>)\n\n"
        f"Time ❝ <code>{elapsed_ms}ms</code>"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)
