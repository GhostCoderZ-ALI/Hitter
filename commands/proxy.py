import asyncio
import time
import html
import aiohttp
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.enums import ParseMode

import database.db as db
from functions.force_join import check_force_join, force_join_keyboard, FORCE_JOIN_MSG
from functions.emojis import EMOJI

router = Router()


def get_proxy_url(proxy_str: str) -> str:
    proxy_str = proxy_str.strip()
    try:
        if "@" in proxy_str:
            auth, hostport = proxy_str.rsplit("@", 1)
            user, password = auth.split(":", 1)
            host, port = hostport.rsplit(":", 1)
            return f"http://{user}:{password}@{host}:{port}"
        else:
            parts = proxy_str.split(":")
            if len(parts) == 4:
                host, port, user, password = parts
                return f"http://{user}:{password}@{host}:{port}"
            elif len(parts) == 2:
                return f"http://{parts[0]}:{parts[1]}"
    except Exception:
        pass
    return None


async def test_proxy(proxy_str: str, timeout: int = 10) -> dict:
    """Full proxy test — IP, country, speed, type, fraud score, and Stripe connectivity"""
    result = {
        "proxy": proxy_str, "alive": False, "ms": None, "ip": None,
        "country": None, "country_code": None, "isp": None, "type": None,
        "stripe": False, "stripe_ms": None,
        "fraud_score": None, "is_proxy": None, "is_vpn": None,
        "error": None,
    }
    proxy_url = get_proxy_url(proxy_str)
    if not proxy_url:
        result["error"] = "Invalid format"
        return result
    
    # Detect proxy type from URL
    if proxy_url.startswith("socks5"):
        result["type"] = "SOCKS5"
    elif proxy_url.startswith("socks4"):
        result["type"] = "SOCKS4"
    else:
        result["type"] = "HTTP"
    
    try:
        # Step 1: Basic connectivity + IP info
        t0 = time.perf_counter()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
            async with s.get("http://ip-api.com/json?fields=query,country,countryCode,isp,org,as,hosting", proxy=proxy_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["alive"] = True
                    result["ms"] = round((time.perf_counter() - t0) * 1000)
                    result["ip"] = data.get("query", "?")
                    result["country"] = data.get("country", "?")
                    result["country_code"] = data.get("countryCode", "?")
                    result["isp"] = data.get("isp") or data.get("org") or "?"
                    if data.get("hosting"):
                        result["type"] += " (DC)"
                    else:
                        result["type"] += " (Resi)"
                else:
                    result["error"] = f"HTTP {resp.status}"
                    return result
    except asyncio.TimeoutError:
        result["error"] = "Timeout"
        return result
    except Exception as e:
        result["error"] = str(e)[:40]
        return result
    
    # Step 2: Fraud score check via proxycheck.io (free, no key)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as s:
            check_url = f"http://proxycheck.io/v2/{result['ip']}?vpn=1&risk=1&asn=1"
            async with s.get(check_url) as resp:
                if resp.status == 200:
                    fdata = await resp.json()
                    ip_data = fdata.get(result["ip"], {})
                    result["fraud_score"] = ip_data.get("risk", None)
                    result["is_proxy"] = ip_data.get("proxy", "?")
                    result["is_vpn"] = ip_data.get("vpn", "?")
    except Exception:
        pass  # Non-critical, continue without fraud score
    
    # Step 3: Stripe connectivity test
    try:
        t1 = time.perf_counter()
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8),
            connector=aiohttp.TCPConnector(ssl=False)
        ) as s:
            async with s.post(
                "https://api.stripe.com/v1/tokens",
                proxy=proxy_url,
                headers={"content-type": "application/x-www-form-urlencoded"},
                data="key=pk_test_check"
            ) as resp:
                result["stripe_ms"] = round((time.perf_counter() - t1) * 1000)
                if resp.status in (200, 400, 401, 402, 403, 404):
                    result["stripe"] = True
    except Exception:
        result["stripe"] = False
        result["stripe_ms"] = None
    
    return result


async def test_proxies_batch(proxies: list, concurrency: int = 10) -> list:
    sem = asyncio.Semaphore(concurrency)
    async def _run(p):
        async with sem:
            return await test_proxy(p)
    return await asyncio.gather(*[_run(p) for p in proxies])


@router.message(Command("proxy", prefix="/."))
async def cmd_proxy(msg: Message, command: CommandObject, bot: Bot):
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
        await _show_proxy_list(msg, uid)
        return

    sub, _, rest = args.partition(" ")
    sub = sub.lower()

    if sub == "add":
        await _add_proxies(msg, uid, rest.strip())
    elif sub in ("del", "rm", "remove"):
        await _del_proxy(msg, uid, rest.strip())
    elif sub == "clear":
        await _clear_proxies(msg, uid)
    elif sub in ("test", "check"):
        await _test_proxies(msg, uid)
    elif sub == "list":
        await _show_proxy_list(msg, uid)
    else:
        # Check the proxy without adding, show "Save?" button
        await _check_proxy_only(msg, uid, args)


async def _show_proxy_list(msg: Message, uid: int):
    proxies = await db.get_proxies(uid)
    if proxies:
        lines = "\n".join(f"<code>{p}</code>" for p in proxies[:15])
        if len(proxies) > 15:
            lines += f"\n<i>... and {len(proxies) - 15} more</i>"
    else:
        lines = "<i>None added</i>"

    text = (
        f"「 PROXY MANAGER 」\n\n"
        f"Your proxies ({len(proxies)}):\n{lines}\n\n"
        f"<b>Commands</b>\n"
        f"<code>/proxy add host:port:user:pass</code>\n"
        f"<code>/proxy del &lt;proxy&gt;</code>\n"
        f"<code>/proxy clear</code>\n"
        f"<code>/proxy test</code> ─ Full check (IP, country, speed, Stripe)\n\n"
        f"<i>Formats: host:port | host:port:user:pass | user:pass@host:port</i>"
    )
    await msg.answer(text, parse_mode=ParseMode.HTML)


async def _add_proxies(msg: Message, uid: int, text: str):
    if not text:
        await msg.answer(
            "Usage: <code>/proxy add host:port:user:pass</code>",
            parse_mode=ParseMode.HTML
        )
        return

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        await msg.answer(f"{EMOJI['declined']} No proxies provided.", parse_mode=ParseMode.HTML)
        return

    status_msg = await msg.answer(
        f"{EMOJI['hitting']} Testing {len(lines)} proxy(s)...\n"
        f"Checking IP, country, speed, and Stripe...",
        parse_mode=ParseMode.HTML
    )

    results = await test_proxies_batch(lines, concurrency=10)
    alive, dead = [], []
    for r in results:
        if r["alive"]:
            await db.add_proxy(uid, r["proxy"])
            alive.append(r)
        else:
            dead.append(r)

    alive_blocks = []
    for r in alive[:5]:
        stripe_s = EMOJI["charged"] if r["stripe"] else EMOJI["declined"]
        alive_blocks.append(
            f"{EMOJI['charged']} <code>{r['proxy']}</code>\n"
            f"   IP ~ <code>{r['ip']}</code> | {r['country']} | <code>{r['ms']}ms</code>\n"
            f"   Stripe ~ {stripe_s}"
        )
    dead_lines = "\n".join(f"{EMOJI['declined']} <code>{r['proxy']}</code> — {r['error']}" for r in dead[:3])
    if len(alive) > 5:
        alive_blocks.append(f"<i>... and {len(alive)-5} more added</i>")

    output = (
        f"「 PROXY ADD 」\n\n"
        f"Alive ~ {len(alive)}/{len(lines)}\n"
        f"Dead ~ {len(dead)}/{len(lines)}\n\n"
    )
    if alive_blocks:
        output += "<b>Added:</b>\n" + "\n\n".join(alive_blocks) + "\n"
    if dead_lines:
        output += f"\n<b>Failed:</b>\n{dead_lines}"

    # Safely truncate without breaking HTML tags
    if len(output) > 4096:
        output = output[:4090] + "\n<i>...</i>"
    await status_msg.edit_text(output, parse_mode=ParseMode.HTML)


async def _del_proxy(msg: Message, uid: int, proxy: str):
    if not proxy:
        await msg.answer("Usage: <code>/proxy del host:port:user:pass</code>", parse_mode=ParseMode.HTML)
        return
    await db.remove_proxy(uid, proxy)
    await msg.answer(f"{EMOJI['trash']} Removed: <code>{proxy}</code>", parse_mode=ParseMode.HTML)


async def _clear_proxies(msg: Message, uid: int):
    proxies = await db.get_proxies(uid)
    count   = len(proxies)
    await db.remove_proxy(uid, "all")
    await msg.answer(f"{EMOJI['trash']} Cleared {count} proxy(s).", parse_mode=ParseMode.HTML)


async def _test_proxies(msg: Message, uid: int):
    proxies = await db.get_proxies(uid)
    if not proxies:
        await msg.answer(f"{EMOJI['declined']} No proxies to test. Add one with <code>/proxy add</code>.", parse_mode=ParseMode.HTML)
        return

    status_msg = await msg.answer(
        f"{EMOJI['hitting']} Testing {len(proxies)} proxy(s)...\n"
        f"Checking IP, country, speed, fraud score, and Stripe...",
        parse_mode=ParseMode.HTML
    )

    results = await test_proxies_batch(proxies, concurrency=10)
    alive = [r for r in results if r["alive"]]
    dead  = [r for r in results if not r["alive"]]
    stripe_ok = [r for r in alive if r["stripe"]]

    blocks = []
    for r in results[:10]:
        if r["alive"]:
            stripe_status = f"{EMOJI['charged']} YES" if r["stripe"] else f"{EMOJI['declined']} NO"
            stripe_lat = f" ({r['stripe_ms']}ms)" if r["stripe_ms"] else ""
            
            # Fraud score indicator
            fs = r.get("fraud_score")
            if fs is not None:
                if fs <= 20:
                    fraud_line = f"{EMOJI['charged']} <code>{fs}/100</code> (Clean)"
                elif fs <= 50:
                    fraud_line = f"{EMOJI['error']} <code>{fs}/100</code> (Medium)"
                elif fs <= 75:
                    fraud_line = f"{EMOJI['risky']} <code>{fs}/100</code> (Risky)"
                else:
                    fraud_line = f"{EMOJI['danger']} <code>{fs}/100</code> (High Risk)"
            else:
                fraud_line = "─"
            
            proxy_flag = ""
            if r.get("is_proxy") == "yes":
                proxy_flag += " [Proxy]"
            if r.get("is_vpn") == "yes":
                proxy_flag += " [VPN]"
            
            blocks.append(
                f"{EMOJI['charged']} <code>{r['proxy']}</code>\n"
                f"   IP ~ <code>{r['ip']}</code>\n"
                f"   Country ~ <code>{r['country']}</code> (<code>{r['country_code']}</code>)\n"
                f"   ISP ~ <code>{r['isp']}</code>\n"
                f"   Type ~ <code>{r['type']}</code>{proxy_flag}\n"
                f"   Latency ~ <code>{r['ms']}ms</code>\n"
                f"   Fraud ~ {fraud_line}\n"
                f"   Stripe ~ {stripe_status}{stripe_lat}"
            )
        else:
            blocks.append(
                f"{EMOJI['declined']} <code>{r['proxy']}</code>\n"
                f"   Error ~ {r['error']}"
            )

    text = (
        f"「 PROXY CHECK 」\n\n"
        f"Total ~ {len(proxies)}\n"
        f"Alive ~ {len(alive)}\n"
        f"Dead ~ {len(dead)}\n"
        f"Stripe OK ~ {len(stripe_ok)}/{len(alive)}\n\n"
        + "\n\n".join(blocks)
    )
    if len(proxies) > 10:
        text += f"\n\n<i>... and {len(proxies)-10} more</i>"
    text += "\n\n<i>Fraud data by proxycheck.io</i>"

    await status_msg.edit_text(text[:4096], parse_mode=ParseMode.HTML)


@router.message(Command("ipcheck", prefix="/."))
async def cmd_ipcheck(msg: Message, command: CommandObject):
    """Check fraud score for any IP, user's proxy IP, or bot's hosting IP"""
    uid = msg.from_user.id
    ip_to_check = (command.args or "").strip()

    # If no IP given, check user's proxy IP first, else bot's hosting IP
    proxy_mode = await db.get_user_proxy_mode(uid)
    user_proxy = None
    label = "Bot Hosting IP"

    if not ip_to_check:
        if proxy_mode == "own":
            user_proxies = await db.get_proxies(uid)
            if user_proxies:
                user_proxy = user_proxies[0]
                label = f"Your Proxy IP"
        if not user_proxy:
            sys_proxy = await db.get_setting("system_proxy", "")
            if sys_proxy and proxy_mode == "system":
                user_proxy = sys_proxy
                label = "System Proxy IP"
    else:
        label = f"IP <code>{ip_to_check}</code>"

    status_msg = await msg.answer(
        f"{EMOJI['hitting']} Checking {label}...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        proxy_url = get_proxy_url(user_proxy) if user_proxy else None
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            # Get IP — through proxy if set
            if not ip_to_check:
                if proxy_url:
                    async with s.get("https://api.ipify.org", proxy=proxy_url) as resp:
                        ip_to_check = (await resp.text()).strip()
                else:
                    async with s.get("https://api.ipify.org") as resp:
                        ip_to_check = (await resp.text()).strip()
            
            # Step 1: IP geolocation
            async with s.get(f"http://ip-api.com/json/{ip_to_check}?fields=query,country,countryCode,isp,org,as,hosting") as resp:
                geo = await resp.json() if resp.status == 200 else {}
            
            # Step 2: Fraud score from proxycheck.io
            async with s.get(f"http://proxycheck.io/v2/{ip_to_check}?vpn=1&risk=1&asn=1") as resp:
                fraud_data = {}
                if resp.status == 200:
                    fj = await resp.json()
                    fraud_data = fj.get(ip_to_check, {})
            
            # Step 3: Stripe connectivity (direct, no proxy)
            stripe_ok = False
            stripe_ms = None
            t0 = time.perf_counter()
            try:
                async with s.post(
                    "https://api.stripe.com/v1/tokens",
                    headers={"content-type": "application/x-www-form-urlencoded"},
                    data="key=pk_test_check"
                ) as resp:
                    stripe_ms = round((time.perf_counter() - t0) * 1000)
                    if resp.status in (200, 400, 401, 402, 403, 404):
                        stripe_ok = True
            except Exception:
                pass
        
        # Build output
        country = geo.get("country", "?")
        cc = geo.get("countryCode", "?")
        isp = geo.get("isp") or geo.get("org") or "?"
        is_dc = geo.get("hosting", False)
        ip_type = "Datacenter" if is_dc else "Residential"
        
        fs = fraud_data.get("risk")
        is_proxy = fraud_data.get("proxy", "?")
        is_vpn = fraud_data.get("vpn", "?")
        
        if fs is not None:
            if fs <= 20:
                fraud_line = f"{EMOJI['charged']} <code>{fs}/100</code> (Clean)"
            elif fs <= 50:
                fraud_line = f"{EMOJI['error']} <code>{fs}/100</code> (Medium)"
            elif fs <= 75:
                fraud_line = f"{EMOJI['risky']} <code>{fs}/100</code> (Risky)"
            else:
                fraud_line = f"{EMOJI['danger']} <code>{fs}/100</code> (High Risk)"
        else:
            fraud_line = "─ (unavailable)"
        
        flags = []
        if is_proxy == "yes":
            flags.append("Proxy")
        if is_vpn == "yes":
            flags.append("VPN")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        
        stripe_line = f"{EMOJI['charged']} YES ({stripe_ms}ms)" if stripe_ok else f"{EMOJI['declined']} NO"
        
        text = (
            f"「 IP CHECK 」\n\n"
            f"IP ~ <code>{ip_to_check}</code>\n"
            f"Country ~ <code>{country}</code> (<code>{cc}</code>)\n"
            f"ISP ~ <code>{isp}</code>\n"
            f"Type ~ <code>{ip_type}</code>{flag_str}\n"
            f"Fraud Score ~ {fraud_line}\n"
            f"Stripe ~ {stripe_line}\n"
        )
        
        # Verdict
        if stripe_ok and (fs is None or fs <= 50):
            text += f"\n{EMOJI['charged']} <b>GOOD for hitting</b>"
        elif stripe_ok and fs and fs <= 75:
            text += f"\n{EMOJI['error']} <b>Usable but risky</b>"
        elif not stripe_ok:
            text += f"\n{EMOJI['declined']} <b>Cannot reach Stripe</b>"
        else:
            text += f"\n{EMOJI['danger']} <b>High fraud score — likely blocked</b>"
        
        text += "\n\n<i>Fraud data by proxycheck.io</i>"
        
        await status_msg.edit_text(text, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        await status_msg.edit_text(f"{EMOJI['declined']} Error: {str(e)[:60]}", parse_mode=ParseMode.HTML)


# ─── Check proxy only (no auto-add), show Save button ───

_checked_proxies: dict = {}  # uid -> proxy_str

async def _check_proxy_only(msg: Message, uid: int, proxy_str: str):
    """Check a proxy without adding. Show Save? button if alive."""
    if not proxy_str:
        await msg.answer(
            f"「 PROXY CHECK 」\n\n"
            f"<code>/proxy &lt;host:port:user:pass&gt;</code> — Check only\n"
            f"<code>/proxy add &lt;proxy&gt;</code> — Check + save\n",
            parse_mode=ParseMode.HTML,
        )
        return

    status_msg = await msg.answer(
        f"{EMOJI['hitting']} Checking proxy...", parse_mode=ParseMode.HTML
    )

    r = await test_proxy(proxy_str)

    if not r["alive"]:
        await status_msg.edit_text(
            f"「 PROXY CHECK 」\n\n"
            f"{EMOJI['declined']} <code>{html.escape(proxy_str)}</code>\n"
            f"Error ❝ <code>{html.escape(str(r['error']))}</code>\n\n"
            f"<i>Proxy is dead. Not saved.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    stripe_s = f"{EMOJI['charged']} YES ({r['stripe_ms']}ms)" if r["stripe"] else f"{EMOJI['declined']} NO"
    fs = r.get("fraud_score")
    if fs is not None:
        if fs <= 20:
            fraud_line = f"{EMOJI['charged']} <code>{fs}/100</code> (Clean)"
        elif fs <= 50:
            fraud_line = f"{EMOJI['error']} <code>{fs}/100</code> (Medium)"
        else:
            fraud_line = f"{EMOJI['danger']} <code>{fs}/100</code> (Risky)"
    else:
        fraud_line = "─"

    _checked_proxies[uid] = proxy_str
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{EMOJI['charged']} Save Proxy", callback_data=f"saveproxy_{uid}"),
            InlineKeyboardButton(text=f"{EMOJI['declined']} Discard", callback_data=f"discardproxy_{uid}"),
        ]
    ])
    text = (
        f"「 PROXY CHECK 」\n\n"
        f"{EMOJI['charged']} <code>{html.escape(proxy_str)}</code>\n"
        f"IP ❝ <code>{html.escape(str(r['ip']))}</code>\n"
        f"Country ❝ <code>{html.escape(str(r['country']))}</code> (<code>{html.escape(str(r['country_code']))}</code>)\n"
        f"ISP ❝ <code>{html.escape(str(r['isp']))}</code>\n"
        f"Type ❝ <code>{html.escape(str(r['type']))}</code>\n"
        f"Latency ❝ <code>{r['ms']}ms</code>\n"
        f"Fraud ❝ {fraud_line}\n"
        f"Stripe ❝ {stripe_s}\n\n"
        f"<b>Save this proxy to your account?</b>"
    )
    await status_msg.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("saveproxy_"))
async def cb_save_proxy(query: CallbackQuery):
    uid = int(query.data.split("_")[1])
    if query.from_user.id != uid:
        return await query.answer("Not your session.", show_alert=True)
    proxy_str = _checked_proxies.pop(uid, None)
    if not proxy_str:
        return await query.answer("Session expired.", show_alert=True)
    await db.add_proxy(uid, proxy_str)
    await query.answer(f"Proxy saved!")
    await query.message.edit_text(
        f"{EMOJI['charged']} Proxy <code>{proxy_str}</code> saved to your account.",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("discardproxy_"))
async def cb_discard_proxy(query: CallbackQuery):
    uid = int(query.data.split("_")[1])
    if query.from_user.id != uid:
        return await query.answer("Not your session.", show_alert=True)
    _checked_proxies.pop(uid, None)
    await query.answer("Discarded.")
    await query.message.edit_text(
        f"{EMOJI['declined']} Proxy discarded. Not saved.",
        parse_mode=ParseMode.HTML,
    )
